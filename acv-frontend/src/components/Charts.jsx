import { money } from '../api'

// Seller vs. buyer offers by negotiation round.
export function OffersChart({ rounds }) {
  const W = 640, H = 240, P = { l: 70, r: 24, t: 16, b: 34 }
  const vals = rounds.flatMap((r) => [r.seller, r.buyer])
  const lo = Math.min(...vals) - 300, hi = Math.max(...vals) + 300
  const x = (i) => P.l + (i * (W - P.l - P.r)) / Math.max(rounds.length - 1, 1)
  const y = (v) => P.t + ((hi - v) * (H - P.t - P.b)) / (hi - lo)
  const ticks = [0, 1, 2, 3].map((k) => lo + ((hi - lo) * k) / 3)
  const line = (key) => rounds.map((r, i) => `${i ? 'L' : 'M'}${x(i)},${y(r[key])}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Offers by round">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={P.l} x2={W - P.r} y1={y(t)} y2={y(t)} stroke="#e3e4e6" />
          <text x={P.l - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="#8a8d91">{money(Math.round(t / 100) * 100)}</text>
        </g>
      ))}
      {rounds.map((r, i) => <text key={i} x={x(i)} y={H - 12} textAnchor="middle" fontSize="11" fill="#8a8d91">{i === 0 ? 'Start' : `Round ${r.round}`}</text>)}
      <path d={line('seller')} fill="none" stroke="#323536" strokeWidth="3" />
      <path d={line('buyer')} fill="none" stroke="#f26522" strokeWidth="3" />
      {rounds.map((r, i) => (
        <g key={`p${i}`}>
          <circle cx={x(i)} cy={y(r.seller)} r="4.5" fill="#323536" />
          <circle cx={x(i)} cy={y(r.buyer)} r="4.5" fill="#f26522" />
        </g>
      ))}
    </svg>
  )
}

// Cars sent to each market, stacked by week.
export function MarketBars({ loads }) {
  const byMarket = {}
  loads.forEach((l) => {
    byMarket[l.to] = byMarket[l.to] || {}
    byMarket[l.to][l.week] = (byMarket[l.to][l.week] || 0) + l.cars
  })
  const rows = Object.entries(byMarket).map(([m, w]) => ({ m, w, total: Object.values(w).reduce((a, b) => a + b, 0) }))
    .sort((a, b) => b.total - a.total)
  const max = Math.max(...rows.map((r) => r.total))
  const colors = { 1: '#f26522', 2: '#323536', 3: '#ff9e1b', 4: '#8a8d91' }
  const W = 820, rowH = 30, L = 110, H = rows.length * rowH + 8
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Cars per market">
      {rows.map((r, i) => {
        let cx = L
        return (
          <g key={r.m} transform={`translate(0,${i * rowH + 4})`}>
            <text x={L - 10} y="15" textAnchor="end" fontSize="12" fill="#323536">{r.m}</text>
            {Object.entries(r.w).sort().map(([wk, n]) => {
              const w = (n / max) * (W - L - 50)
              const el = <rect key={wk} x={cx} y="3" width={w} height="16" rx="3" fill={colors[wk]} />
              cx += w + 2
              return el
            })}
            <text x={cx + 6} y="15" fontSize="12" fontWeight="700" fill="#121212">{r.total}</text>
          </g>
        )
      })}
    </svg>
  )
}
