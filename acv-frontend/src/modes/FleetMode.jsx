import { useState } from 'react'
import Assistant from '../components/Assistant'
import { MarketBars } from '../components/Charts'
import Icon from '../components/Icon'
import { money } from '../api'
import { CITIES, FLEET_MODELS } from '../constants'

export default function FleetMode({ demoSafe, agent }) {
  const { run, start, resume } = agent
  const [count, setCount] = useState(120)
  const [lots, setLots] = useState(['Buffalo', 'Rochester', 'Albany'])
  const [weeks, setWeeks] = useState(2)
  const v = run?.values || {}
  const plan = v.plan, base = v.baselines
  const toggle = (c) => setLots(lots.includes(c) ? lots.filter((x) => x !== c) : [...lots, c])

  const go = () => start({ fleet_name: 'Rental fleet', count, lots, models: FLEET_MODELS, weeks, demo_safe: demoSafe },
    `Sell ${count} similar rental cars from ${lots.join(', ')} over ${weeks} week${weeks > 1 ? 's' : ''}.`)

  return (
    <>
      <Assistant title="Fleet assistant" run={run} onAction={resume}
        intro="Selling a big batch of similar cars? I'll spread them across markets in full truckloads so prices hold and shipping stays cheap."
        actions={run?.pending && [{ label: 'Approve plan', value: { approved: true }, primary: true }, { label: 'Not now', value: { approved: false } }]}
        doneText={v.schedule ? 'Approved: auctions staggered, car haulers booked, buyers alerted.' : null}>
        <label className="field">Cars to sell: <b style={{ color: 'var(--ink)' }}>{count}</b>
          <input type="range" min="30" max="240" step="10" value={count} onChange={(e) => setCount(+e.target.value)} />
        </label>
        <div className="field">Fleet lots
          <div className="chips">{CITIES.slice(0, 10).map((c) => <button key={c} className={`chip ${lots.includes(c) ? 'on' : ''}`} onClick={() => toggle(c)}>{c}</button>)}</div>
        </div>
        <label className="field">Sell over: <b style={{ color: 'var(--ink)' }}>{weeks} week{weeks > 1 ? 's' : ''}</b>
          <input type="range" min="1" max="4" value={weeks} onChange={(e) => setWeeks(+e.target.value)} />
        </label>
        <button className="btn btn-primary btn-block" onClick={go} disabled={run?.busy || !lots.length}><Icon name="truck" size={15} />Plan distribution</button>
      </Assistant>

      <section>
        <div className="results-head">
          <div><h2>Fleet distribution plan</h2><div className="sub">{count} cars · 2023 Altima, Corolla, Malibu · {lots.join(', ')}</div></div>
          {plan && <span className="pill">{plan.markets} markets · {weeks} week{weeks > 1 ? 's' : ''}</span>}
        </div>
        {plan && base ? (
          <>
            <div className="stats three">
              <div className="card stat accent"><div className="label">Extra vs dumping locally</div><div className="value">+{money(plan.net - base.dump.net)}</div><div className="delta">+{Math.round((plan.net / base.dump.net - 1) * 100)}% net</div></div>
              <div className="card stat"><div className="label">Transport per car</div><div className="value">{money(plan.transport_per_car)}</div><div className="delta">vs {money(base.single.transport_per_car)} one by one</div></div>
              <div className="card stat"><div className="label">Full truckloads</div><div className="value">{plan.loads.filter((l) => l.truck).length}</div><div className="delta" style={{ color: 'var(--gray)' }}>vs {base.single.trucks} single trips</div></div>
            </div>
            <div className="card panel">
              <h3><Icon name="globe" size={17} />Where the cars go</h3>
              <div className="legend" style={{ marginBottom: 6 }}>{Array.from({ length: weeks }, (_, i) => <span key={i}><i style={{ background: ['#f26522', '#323536', '#ff9e1b', '#8a8d91'][i] }} />Week {i + 1}</span>)}</div>
              <MarketBars loads={plan.loads} />
            </div>
            <div className="card panel">
              <h3><Icon name="trending" size={17} />Compared with the usual ways</h3>
              <table className="tbl">
                <thead><tr><th>Plan</th><th>Avg sale</th><th>Transport / car</th><th>Net to fleet</th></tr></thead>
                <tbody>{[base.dump, base.single, plan].map((p) => (
                  <tr key={p.name} className={p === plan ? 'best' : ''}><td>{p === plan ? '★ ' : ''}{p.name}</td><td>{money(p.avg_price)}</td><td>{money(p.transport_per_car)}</td><td>{money(p.net)}</td></tr>))}
                </tbody>
              </table>
              <div className="disclaimer">Illustrative demo data.</div>
            </div>
          </>
        ) : (
          <div className="card empty"><Icon name="truck" size={44} stroke={1.5} /><h3>{run?.busy ? 'Planning…' : 'Plan a fleet sale'}</h3><div>See where every truckload goes, week by week.</div></div>
        )}
      </section>
    </>
  )
}
