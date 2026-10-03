import { useId } from 'react'

// Studio-style side view of a car, drawn in SVG and colored to match the listing.
// (Demo images: no real photos, no copyright issues, works offline.)

const PAINT = {
  White: ['#f7f8fa', '#d9dde3'], Black: ['#2b2f36', '#121417'], Silver: ['#d4d8de', '#9aa1ab'],
  Gray: ['#8b929b', '#5b6169'], Blue: ['#3c6fc4', '#1f3f7a'], Red: ['#c9302c', '#7f1714'],
}

const SUV = ['RAV4', 'CR-V', 'Rogue', 'Equinox', 'Escape', 'Explorer', 'Highlander', 'Tucson', 'Grand Cherokee', 'Outback', 'Wrangler']
const TRUCK = ['F-150', 'Silverado 1500', '1500', 'Tacoma']

export function bodyType(model = '') {
  if (TRUCK.includes(model)) return 'truck'
  if (SUV.includes(model)) return 'suv'
  return 'sedan'
}

const SHAPES = {
  sedan: {
    body: 'M28,150 Q26,128 50,123 L112,116 Q138,90 176,85 L252,84 Q288,86 314,112 L354,119 Q374,123 374,141 L374,152 Q374,162 362,162 L40,162 Q28,162 28,150 Z',
    windows: ['M130,115 Q152,96 180,93 L214,92 L214,115 Z', 'M220,92 L254,92 Q280,95 300,114 L220,115 Z'],
    wheels: [96, 302], r: 25, door: 217, light: [34, 131], tail: [366, 128],
  },
  suv: {
    body: 'M26,150 Q24,124 46,119 L100,112 Q122,76 152,70 L304,68 Q332,69 346,98 L360,116 Q374,120 374,140 L374,152 Q374,163 362,163 L38,163 Q26,163 26,150 Z',
    windows: ['M118,111 Q136,82 160,78 L208,77 L208,111 Z', 'M214,77 L300,76 Q322,79 336,106 L214,110 Z'],
    wheels: [100, 300], r: 27, door: 211, light: [32, 128], tail: [366, 124],
  },
  truck: {
    body: 'M26,150 Q24,126 46,121 L98,115 Q118,80 142,76 L212,75 L216,116 L374,116 L374,152 Q374,163 362,163 L38,163 Q26,163 26,150 Z',
    windows: ['M112,113 Q130,86 148,82 L204,81 L206,113 Z'],
    wheels: [98, 308], r: 27, door: 160, light: [32, 129], tail: [368, 122], bed: true,
  },
}

export default function CarImage({ model, color = 'Silver', body }) {
  const uid = useId().replace(/:/g, '')
  const kind = body || bodyType(model)
  const s = SHAPES[kind]
  const [paint, shade] = PAINT[color] || PAINT.Silver
  return (
    <svg viewBox="0 0 400 250" role="img" aria-label={`${color} ${model || kind}`}>
      <defs>
        <linearGradient id={`bg${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f4f5f7" /><stop offset="0.72" stopColor="#e9ebee" /><stop offset="1" stopColor="#dfe2e6" />
        </linearGradient>
        <linearGradient id={`paint${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={paint} /><stop offset="0.55" stopColor={paint} /><stop offset="1" stopColor={shade} />
        </linearGradient>
        <linearGradient id={`glass${uid}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5d7184" /><stop offset="1" stopColor="#1f2a36" />
        </linearGradient>
      </defs>
      <rect width="400" height="250" fill={`url(#bg${uid})`} />
      <ellipse cx="200" cy="200" rx="172" ry="11" fill="#000" opacity="0.16" />
      <g transform="translate(0,26)">
        {s.wheels.map((x) => <path key={`arch${x}`} d={`M${x - s.r - 6},162 A${s.r + 6},${s.r + 6} 0 0 1 ${x + s.r + 6},162 Z`} fill="#1b1d21" />)}
        <path d={s.body} fill={`url(#paint${uid})`} stroke="rgba(0,0,0,.18)" strokeWidth="1.2" />
        {s.bed && <rect x="216" y="108" width="158" height="9" rx="2" fill={shade} />}
        {s.windows.map((d, i) => <path key={i} d={d} fill={`url(#glass${uid})`} />)}
        <line x1={s.door} y1="117" x2={s.door} y2="156" stroke="rgba(0,0,0,.2)" strokeWidth="1.5" />
        <path d="M44,128 L360,126" stroke="#fff" strokeOpacity="0.35" strokeWidth="2" />
        <rect x={s.light[0]} y={s.light[1]} width="16" height="7" rx="3" fill="#fff6d6" stroke="rgba(0,0,0,.15)" />
        <rect x={s.tail[0] - 4} y={s.tail[1]} width="10" height="9" rx="2" fill="#d12a2a" />
        {s.wheels.map((x) => (
          <g key={x}>
            <circle cx={x} cy="162" r={s.r} fill="#17191c" />
            <circle cx={x} cy="162" r={s.r * 0.58} fill="#b9bec6" />
            <circle cx={x} cy="162" r={s.r * 0.22} fill="#6b717a" />
            {[0, 72, 144, 216, 288].map((a) => (
              <line key={a} x1={x} y1="162" x2={x + Math.cos((a * Math.PI) / 180) * s.r * 0.52} y2={162 + Math.sin((a * Math.PI) / 180) * s.r * 0.52} stroke="#8d939b" strokeWidth="3" />
            ))}
          </g>
        ))}
      </g>
    </svg>
  )
}
