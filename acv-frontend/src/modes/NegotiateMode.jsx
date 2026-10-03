import { useState } from 'react'
import Assistant from '../components/Assistant'
import CarImage from '../components/CarImage'
import { OffersChart } from '../components/Charts'
import Icon from '../components/Icon'
import { money } from '../api'
import { BUYER, SELLER } from '../constants'

const WHO = { mediator: ['AI', 'Mediator'], seller: ['S', "Seller's agent"], buyer: ['B', "Buyer's agent"] }

export default function NegotiateMode({ demoSafe, agent }) {
  const { run, start, resume } = agent
  const [f, setF] = useState({ ask: 15000, min: 12800, lien: 5000, bid: 12000, max: 13400 })
  const set = (k) => (e) => setF({ ...f, [k]: +e.target.value })
  const v = run?.values || {}
  const pending = run?.pending
  const c = v.closing

  const go = () => start({
    car: { year: 2020, make: 'Toyota', model: 'Camry', trim: '', mileage: 52000, grade: 4.0, city: 'Buffalo' },
    seller: SELLER, buyer: BUYER, buyer_city: 'Rochester', ask: f.ask, seller_min: f.min, high_bid: f.bid,
    buyer_max: f.max, lien: f.lien, demo_safe: demoSafe,
  }, `Seller asks ${money(f.ask)}, top bid is ${money(f.bid)}. Close the gap.`)

  return (
    <>
      <Assistant title="Deal assistant" run={run} onAction={resume}
        intro="When the ask is above the top bid, I negotiate for both sides without revealing their limits, then close the deal."
        actions={pending && [
          { label: `Both accept ${money(pending.price)}`, value: { accepted: true }, primary: true },
          { label: 'Walk away', value: { accepted: false } },
        ]}
        doneText={c ? 'Deal closed: payment, insurance, loan payoff, title and truck handled.' : (v.round && !v.deal ? 'No deal. Nobody was pushed past their limit.' : null)}>
        <div className="fields">
          <div className="group-label"><Icon name="dollar" size={13} />Seller</div>
          <label className="field">Asking price<input type="number" step="250" value={f.ask} onChange={set('ask')} /></label>
          <label className="field"><span className="field-label">Lowest OK <span className="hint">private</span></span><input type="number" step="250" value={f.min} onChange={set('min')} /></label>
          <label className="field full">Loan still owed<input type="number" step="500" value={f.lien} onChange={set('lien')} /></label>
          <div className="group-label"><Icon name="cart" size={13} />Buyer</div>
          <label className="field">Top bid<input type="number" step="250" value={f.bid} onChange={set('bid')} /></label>
          <label className="field"><span className="field-label">Highest OK <span className="hint">private</span></span><input type="number" step="250" value={f.max} onChange={set('max')} /></label>
        </div>
        <button className="btn btn-primary btn-block" onClick={go} disabled={run?.busy}><Icon name="users" size={15} />Start AI negotiation</button>
      </Assistant>

      <section>
        <div className="results-head">
          <div><h2>Deal room</h2><div className="sub">2020 Toyota Camry · 52,000 mi · Buffalo → Rochester</div></div>
          {v.deal && <span className="pill" style={{ color: 'var(--orange-dark)' }}>Deal at {money(v.deal.price)}</span>}
        </div>
        {c && (
          <div className="stats">
            <div className="card stat accent"><div className="label">Deal price</div><div className="value">{money(c.price)}</div><div className="delta">+{money(c.price - v.high_bid)} vs top bid</div></div>
            <div className="card stat"><div className="label">Seller gets</div><div className="value">{money(c.seller_payout)}</div></div>
            <div className="card stat"><div className="label">Buyer pays (all-in)</div><div className="value">{money(c.buyer_pays)}</div></div>
            <div className="card stat"><div className="label">ACV earns</div><div className="value">{money(c.acv.total)}</div><div className="delta">only because it sold</div></div>
          </div>
        )}
        <div className="card panel">
          <div className="hero-car">
            <div className="vimg"><CarImage model="Camry" color="Gray" /></div>
            <div>
              {v.rounds?.length > 1 ? (
                <>
                  <div className="legend"><span><i style={{ background: '#323536' }} />Seller</span><span><i style={{ background: '#f26522' }} />Buyer</span></div>
                  <OffersChart rounds={v.rounds} />
                </>
              ) : <div style={{ color: 'var(--gray)' }}>{run?.busy ? 'Negotiating…' : 'Start the negotiation to watch the gap close, round by round.'}</div>}
            </div>
          </div>
        </div>
        {v.messages?.length > 0 && (
          <div className="card panel">
            <h3><Icon name="users" size={17} />Negotiation</h3>
            <div className="msgs">{v.messages.map((m, i) => (
              <div key={i} className="msg"><div className={`who ${m.who}`}>{WHO[m.who][0]}</div><div className="text">{m.text}</div></div>))}
            </div>
          </div>
        )}
        {c && (
          <div className="card panel">
            <h3><Icon name="check" size={17} stroke={3} />Closed automatically</h3>
            <div className="checklist">
              {[['dollar', `Payment held in escrow: ${money(c.buyer_pays)}`], ['shield', `Transit insurance bound (${money(c.insurance_premium)})`],
                ['dollar', c.lien_payoff ? `Loan of ${money(c.lien_payoff)} paid to the lender` : 'No loan to pay off'], ['check', 'E-title transfer started'],
                ['truck', `Truck booked: ${money(c.transport)}`], ['dollar', `Seller payout: ${money(c.seller_payout)}`]].map(([ic, t]) => (
                <div key={t} className="check-item"><div className="step-icon"><Icon name={ic} size={12} stroke={2.6} /></div>{t}</div>))}
            </div>
          </div>
        )}
      </section>
    </>
  )
}
