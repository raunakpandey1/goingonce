import { useState } from 'react'
import Assistant from '../components/Assistant'
import CarImage from '../components/CarImage'
import Icon from '../components/Icon'
import VehicleCard from '../components/VehicleCard'
import { money } from '../api'
import { BUYER, PITCH, SUGGESTIONS } from '../constants'

export default function BuyMode({ demoSafe, agent }) {
  const { run, start, resume } = agent
  const [text, setText] = useState(PITCH)
  const v = run?.values || {}
  const cards = [...(v.matches || []), ...(v.flagged || [])]
  const pending = run?.pending
  const send = () => text.trim() && start({ request_text: text, buyer_name: BUYER, demo_safe: demoSafe }, text)

  return (
    <>
      <Assistant
        title="Buying assistant"
        intro="Tell me what you need. I'll search ACV and Copart, check every car's history, and ask before I bid."
        run={run}
        actions={pending && [
          { label: `Approve: bid up to ${money(pending.total)}`, value: { approved: true }, primary: true },
          { label: 'Not now', value: { approved: false } },
        ]}
        onAction={resume}
        doneText={v.result?.bids?.length ? `Bids placed on ${v.result.bids.length} cars. Truck booked, title checks started.` : null}
      >
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. Need 3 Accords under $15K delivered to Buffalo"
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
        <div className="suggestions">
          {SUGGESTIONS.slice(1).map((s) => <button key={s} className="suggestion" onClick={() => setText(s)}>{s}</button>)}
        </div>
        <button className="btn btn-primary btn-block" onClick={send} disabled={run?.busy}><Icon name="send" size={15} />Send to agent</button>
      </Assistant>

      <section>
        <div className="results-head">
          <div>
            <h2>Marketplace results</h2>
            <div className="sub">{v.request ? `${v.request.quantity}× ${[v.request.make, v.request.model].filter(Boolean).join(' ')} · delivered to ${v.request.destination_city}` : 'Live listings across ACV and Copart'}</div>
          </div>
          {v.searches && <div style={{ display: 'flex', gap: 8 }}>{v.searches.map((s) => <span key={s.source} className="pill">{s.source} · {s.live_count} listings</span>)}</div>}
        </div>
        {v.result?.bids?.length > 0 && <div className="banner ok"><Icon name="check" size={18} stroke={3} />Bids placed on {v.result.bids.length} cars · Truck booked · Title checks started</div>}
        {v.result?.remaining > 0 && <div className="banner info"><Icon name="search" size={16} />Watching ACV + Copart for {v.result.remaining} more. Sellers who list a match will see this buyer waiting.</div>}
        {cards.length > 0 ? (
          <div className="grid">{cards.map((car) => <VehicleCard key={car.id} car={car} destination={v.request?.destination_city} />)}</div>
        ) : (
          <div className="card empty">
            <div className="cars-row">
              <div style={{ width: 170 }}><CarImage model="Camry" color="White" /></div>
              <div style={{ width: 170 }}><CarImage model="RAV4" color="Blue" /></div>
              <div style={{ width: 170 }}><CarImage model="F-150" color="Gray" /></div>
            </div>
            <h3>{run?.busy ? 'Searching ACV and Copart…' : 'Ask for the cars you need'}</h3>
            <div>The assistant finds them, checks their full history, and lines up bids for your approval.</div>
          </div>
        )}
      </section>
    </>
  )
}

