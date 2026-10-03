import { useState } from 'react'
import CarImage from './CarImage'
import Icon from './Icon'
import { miles, money } from '../api'

// Marketplace listing card, in the style of an auction marketplace grid.
export default function VehicleCard({ car, destination }) {
  const [open, setOpen] = useState(false)
  const flagged = car.passport?.status === 'flagged'
  const t = car.transport
  return (
    <article className={`card vcard ${flagged ? 'flagged' : ''}`}>
      <div className="vimg">
        <CarImage model={car.model} color={car.color} />
        <span className={`badge ${car.source}`}>{car.source}</span>
        <span className="timer"><Icon name="clock" size={11} stroke={2.6} />Ends {car.auction_ends.replace('Today ', '')}</span>
        {flagged && <div className="ribbon"><Icon name="alert" size={13} stroke={2.6} />HIDDEN HISTORY CAUGHT</div>}
      </div>
      <div className="vbody">
        <div className="vtitle">{car.year} {car.make} {car.model} {car.trim}</div>
        <div className="vmeta">
          <span>{miles(car.mileage)}</span>·
          <span className="grade"><Icon name="star" size={12} /> {car.condition_grade.toFixed(1)}</span>·
          <span><Icon name="pin" size={12} /> {car.city}, {car.state}</span>
        </div>
        <div className="vprice"><b>{money(car.price)}</b><span>market {money(car.market_value)}</span></div>
        {flagged ? (
          <>
            <div className="vstatus bad"><Icon name="alert" size={14} stroke={2.6} />{car.risk?.headline}</div>
            {car.risk?.recommendation && <div className="risk">{car.risk.recommendation}</div>}
          </>
        ) : (
          <>
            <div className="vmeta"><Icon name="truck" size={13} /> {money(t.cost)} to {destination} · {t.days} day{t.days === 1 ? '' : 's'}</div>
            <div className="vstatus ok"><Icon name="shield" size={14} stroke={2.4} />History clean · ACV + Copart</div>
          </>
        )}
        {open && (
          <ul className="timeline">
            {car.passport.timeline.map((e, i) => <li key={i}><b>{e.date}</b> · {e.source} · {e.event}</li>)}
          </ul>
        )}
        <div className="vfoot">
          <button className="linkish" onClick={() => setOpen(!open)}>{open ? 'Hide history' : 'View history'}</button>
          {flagged ? <span style={{ color: 'var(--red)', fontWeight: 700 }}>Excluded</span> : <span>Bid up to <b>{money(car.recommended_bid)}</b></span>}
        </div>
      </div>
    </article>
  )
}
