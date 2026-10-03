import { useRef, useState } from 'react'
import Assistant from '../components/Assistant'
import CarImage from '../components/CarImage'
import Icon from '../components/Icon'
import { money } from '../api'
import { CITIES, COLORS, MODELS, SELLER, splitModel } from '../constants'

// Resize a photo to ≤1568px JPEG in the browser before sending it to the AI.
async function shrink(file) {
  const img = await createImageBitmap(file)
  const scale = Math.min(1, 1568 / Math.max(img.width, img.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(img.width * scale)
  canvas.height = Math.round(img.height * scale)
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
  const url = canvas.toDataURL('image/jpeg', 0.85)
  return { b64: url.split(',')[1], media_type: 'image/jpeg', preview: url }
}

export default function SellMode({ demoSafe, agent }) {
  const { run, start, resume } = agent
  const [form, setForm] = useState({ year: 2019, mileage: 61000, model: 'Toyota Camry', color: 'Silver', city: 'Buffalo' })
  const [photos, setPhotos] = useState([])
  const fileRef = useRef(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const v = run?.values || {}
  const pending = run?.pending

  const onFiles = async (files) => {
    try {
      setPhotos(await Promise.all([...files].slice(0, 4).map(shrink)))
    } catch {
      alert('That photo format is not supported. Please use JPG or PNG.')
    }
  }
  const analyze = () => {
    const [make, model] = splitModel(form.model)
    start({
      vehicle: { year: +form.year, make, model, trim: '', mileage: +form.mileage, city: form.city, title_status: 'clean', seller_name: SELLER, lot_fit: false },
      photos: photos.map(({ b64, media_type }) => ({ b64, media_type })),
      demo_safe: demoSafe,
    }, `Sell my ${form.year} ${form.model}, ${(+form.mileage).toLocaleString()} mi, in ${form.city}${photos.length ? ` (${photos.length} photo${photos.length > 1 ? 's' : ''})` : ''}`)
  }
  const actions = pending && ('best' in pending
    ? [{ label: 'List now', value: { list: true }, primary: true }, { label: 'Save draft', value: { list: false } }]
    : [{ label: 'Sold', value: { sold: true }, primary: true }, { label: 'No sale', value: { sold: false } }])
  const done = v.auction?.sold === false ? 'No car left unsold: re-offered to Copart\'s global buyers.'
    : v.auction?.sold ? 'Sold. Transport and title paperwork started.' : null
  const [, model] = splitModel(form.model)
  const cond = v.condition

  return (
    <>
      <Assistant title="Selling assistant" run={run} actions={actions} onAction={resume} doneText={done}
        intro="Add a few photos. I'll write the condition report, show where you keep the most money, and find buyers already waiting.">
        <div className="fields">
          <label className="field">Year<input type="number" value={form.year} onChange={set('year')} /></label>
          <label className="field">Mileage<input type="number" step="1000" value={form.mileage} onChange={set('mileage')} /></label>
          <label className="field full">Make & model<select value={form.model} onChange={set('model')}>{MODELS.map((m) => <option key={m}>{m}</option>)}</select></label>
          <label className="field">Color<select value={form.color} onChange={set('color')}>{COLORS.map((c) => <option key={c}>{c}</option>)}</select></label>
          <label className="field">Location<select value={form.city} onChange={set('city')}>{CITIES.map((c) => <option key={c}>{c}</option>)}</select></label>
        </div>
        <div className="dropzone" onClick={() => fileRef.current.click()} onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); onFiles(e.dataTransfer.files) }}>
          <Icon name="upload" size={18} />
          {photos.length ? <div className="thumbs">{photos.map((p, i) => <img key={i} src={p.preview} alt="" />)}</div> : <span>Add car photos (JPG or PNG)</span>}
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => onFiles(e.target.files)} />
        </div>
        <button className="btn btn-primary btn-block" onClick={analyze} disabled={run?.busy}><Icon name="camera" size={15} />Analyze & find buyers</button>
      </Assistant>

      <section>
        <div className="results-head">
          <div><h2>Your listing</h2><div className="sub">{form.year} {form.model} · {(+form.mileage).toLocaleString()} mi · {form.city}</div></div>
          {v.listing && <span className="pill"><Icon name="clock" size={12} />Auction {v.listing.auction_starts}</span>}
        </div>
        <div className="card panel">
          <div className="hero-car">
            <div className="vimg">{photos[0] ? <img src={photos[0].preview} alt="Your car" /> : <CarImage model={model} color={form.color} />}</div>
            {cond ? (
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--gray)', display: 'flex', alignItems: 'center', gap: 6 }}>AI CONDITION REPORT <span className="ai-chip"><Icon name="zap" size={9} stroke={3} />AI</span></div>
                <div className="grade-big">{cond.condition_grade.toFixed(1)}<small> / 5</small></div>
                <div style={{ fontSize: 14, lineHeight: 1.45 }}>{cond.summary}</div>
                {cond.visible_damage?.length > 0 && <div className="tags">{cond.visible_damage.map((d) => <span key={d} className="tag">{d}</span>)}</div>}
              </div>
            ) : (
              <div style={{ color: 'var(--gray)' }}>{run?.busy ? 'Reading your photos…' : 'Run the assistant to get an AI condition report, the best way to sell, and waiting buyers.'}</div>
            )}
          </div>
        </div>
        {v.paths && (
          <div className="card panel">
            <h3><Icon name="dollar" size={17} />Where you keep the most money</h3>
            <table className="tbl">
              <thead><tr><th>Option</th><th>Sale</th><th>Costs</th><th>Wait</th><th>You keep</th></tr></thead>
              <tbody>{v.paths.rows.map((r) => (
                <tr key={r.channel} className={r.best ? 'best' : ''}>
                  <td>{r.best && '★ '}{r.channel}</td><td>{money(r.gross)}</td><td>−{money(r.fees + r.transport + r.holding)}</td><td>{r.days} days</td><td>{money(r.net)}</td>
                </tr>))}
              </tbody>
            </table>
          </div>
        )}
        {v.waiting_buyers?.length > 0 && (
          <div className="card panel">
            <h3><Icon name="bell" size={17} />{v.waiting_buyers.length} buyers already waiting for this car</h3>
            <div className="buyers">{v.waiting_buyers.map((w) => (
              <div key={w.wish_id} className="buyer">
                <div className="avatar">{w.buyer.split(' ').map((p) => p[0]).slice(0, 2).join('')}</div>
                <div style={{ flex: 1 }}>{w.buyer}<small>{w.channel === 'ACV' ? 'ACV dealer' : 'Copart global buyer'}{w.max_price ? ` · up to ${money(w.max_price)}` : ''}</small></div>
                {v.listing && w.channel === 'ACV' && <span className="pill" style={{ color: 'var(--green)' }}><Icon name="check" size={12} stroke={3} />Notified</span>}
              </div>))}
            </div>
          </div>
        )}
      </section>
    </>
  )
}
