import { useEffect, useState } from 'react'
import Icon from './components/Icon'
import { useAgent } from './api'
import BuyMode from './modes/BuyMode'
import SellMode from './modes/SellMode'
import NegotiateMode from './modes/NegotiateMode'
import FleetMode from './modes/FleetMode'

const MODES = [
  { key: 'buy', label: 'Buy', icon: 'cart', Comp: BuyMode },
  { key: 'sell', label: 'Sell', icon: 'camera', Comp: SellMode },
  { key: 'deal', label: 'Negotiate', icon: 'users', Comp: NegotiateMode },
  { key: 'fleet', label: 'Fleet', icon: 'truck', Comp: FleetMode },
]

export default function App() {
  const [mode, setMode] = useState('buy')
  const [demoSafe, setDemoSafe] = useState(false)
  // One agent per mode, kept here so switching tabs never loses a run.
  const agents = { buy: useAgent('buyer'), sell: useAgent('seller'), deal: useAgent('deal'), fleet: useAgent('fleet') }

  useEffect(() => {
    fetch('/api/health').then((r) => r.json()).then((h) => setDemoSafe(!h.live_ai)).catch(() => setDemoSafe(true))
  }, [])

  const reset = async () => {
    await fetch('/api/reset', { method: 'POST' })
    Object.values(agents).forEach((a) => a.clear())
  }
  const active = MODES.find((m) => m.key === mode)

  return (
    <>
      <nav className="nav">
        <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
          <span className="brand-acv">ACV</span>
          <span className="brand-divider" />
          <span className="brand-go"><Icon name="gavel" size={18} stroke={2.4} />GoingOnce</span>
        </a>
        <div className="nav-links">
          {MODES.map((m) => (
            <a key={m.key} href="#" className={mode === m.key ? 'active' : ''} onClick={(e) => { e.preventDefault(); setMode(m.key) }}>{m.label}</a>
          ))}
        </div>
        <div className="nav-right">
          <span className={`toggle ${demoSafe ? 'on' : ''}`} onClick={() => setDemoSafe(!demoSafe)} title="Uses saved AI results. Turn on if the Wi-Fi is bad.">
            <span className="track" />Demo-safe
          </span>
          <button className="btn btn-ghost btn-sm" onClick={reset}><Icon name="refresh" size={13} />Reset</button>
          <span className="user-chip"><span className="avatar">MM</span>Mike's Motors</span>
        </div>
      </nav>

      <header className="hero">
        <div className="hero-inner">
          <div className="hero-eyebrow">AI auction assistant</div>
          <h1>Every car finds its best buyer, <span>across ACV and Copart.</span></h1>
          <p>Four AI agents that search, check history, match buyers, negotiate and ship. You approve every money step.</p>
          <div className="mode-tabs">
            {MODES.map((m) => (
              <button key={m.key} className={`mode-tab ${mode === m.key ? 'active' : ''}`} onClick={() => setMode(m.key)}>
                <span className="tab-dot"><Icon name={m.icon} size={14} stroke={2.4} /></span>{m.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="main">
        <active.Comp demoSafe={demoSafe} agent={agents[mode]} />
      </main>
      <footer className="footer">GoingOnce · concept prototype built at the UB AI for Good Hackathon 2026 · not an official ACV product · demo data</footer>
    </>
  )
}
