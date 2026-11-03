import { useState } from 'react'
import { CalendarDays, Clock3, MapPin, Ticket } from 'lucide-react'
import type { Trip } from '../types/trip'

type TripCardProps = {
  trip: Trip
  onChooseSeat: (tripId: string) => void
  layout?: 'grid' | 'horizontal'
}

const dateFormatter = new Intl.DateTimeFormat('es-CL', {
  day: 'numeric',
  month: 'short',
  timeZone: 'America/Santiago',
})

const dateTimeFormatter = new Intl.DateTimeFormat('es-CL', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Santiago',
})

const currencyFormatter = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
})

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Fecha por confirmar' : dateFormatter.format(date)
}

function formatDateTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Por confirmar' : dateTimeFormatter.format(date)
}

export default function TripCard({
  trip,
  onChooseSeat,
  layout = 'grid',
}: TripCardProps) {
  const [expanded, setExpanded] = useState(false)
  const seats = trip.asientos
  const availableSeats = seats?.filter((seat) => seat.estado === 'disponible').length
  const occupiedSeats = seats && availableSeats !== undefined
    ? seats.length - availableSeats
    : undefined
  const fillPercent = seats?.length && occupiedSeats !== undefined
    ? Math.round((occupiedSeats / seats.length) * 100)
    : 0
  const isFull = trip.estado === 'lleno' || availableSeats === 0
  const isAlmostFull =
    availableSeats !== undefined &&
    seats !== undefined &&
    seats.length > 0 &&
    availableSeats / seats.length <= 0.25
  const availability = isFull
    ? 'Agotado'
    : isAlmostFull
      ? 'Casi lleno'
      : 'Disponible'

  if (layout === 'horizontal') {
    return (
      <article className="trip-card trip-card-horizontal">
        <div className="trip-main">
          <div className="trip-copy">
            <div className="trip-meta">
              <span className="trip-category"><Ticket size={12} aria-hidden="true" /> Viaje</span>
              <span className="trip-date">{formatDate(trip.fecha_evento)}</span>
            </div>
            <h2 className="trip-title">{trip.artista}</h2>
            <p className="trip-subtitle">{trip.titulo}</p>
            <div className="trip-details">
              <p><MapPin size={13} aria-hidden="true" /><span>{trip.recinto}</span></p>
              <p><MapPin size={13} aria-hidden="true" /><span>{trip.origen} <span aria-hidden="true">→</span> {trip.destino}</span></p>
            </div>
          </div>
          <div className="trip-schedule">
            <p><Clock3 size={13} aria-hidden="true" /><span>Salida {formatDateTime(trip.fecha_salida)}</span></p>
            <p><Clock3 size={13} aria-hidden="true" /><span>Regreso {formatDateTime(trip.fecha_retorno)}</span></p>
          </div>
        </div>
        <div className="trip-purchase">
          <span className={`availability-badge${isFull ? ' availability-full' : isAlmostFull ? ' availability-low' : ''}`}>
            <span className="availability-dot" aria-hidden="true" />
            {availability}
          </span>
          <div className="trip-price">
            <strong>{currencyFormatter.format(trip.precio_ida)}</strong>
            <span>por asiento</span>
          </div>
          <div className="trip-seat-count" aria-live="polite">
            {availableSeats === undefined
              ? 'Cupos por confirmar'
              : `${availableSeats} ${availableSeats === 1 ? 'libre' : 'libres'} · ${occupiedSeats}/${seats?.length} ocupados`}
          </div>
          <button
            className={`trip-select${isFull ? ' trip-select-full' : ''}`}
            type="button"
            disabled={isFull || !seats?.length}
            onClick={() => onChooseSeat(trip.id)}
            title={isFull ? 'Este viaje está agotado' : undefined}
          >
            {isFull ? 'Agotado' : 'Elegir asiento'}
          </button>
        </div>
      </article>
    )
  }

  return (
    <article className="trip-card">
      <div className="trip-card-heading">
        <span className="trip-category"><Ticket size={12} aria-hidden="true" /> Concierto</span>
        <span className={`availability-badge${isFull ? ' availability-full' : isAlmostFull ? ' availability-low' : ''}`}>
          <span className="availability-dot" aria-hidden="true" />
          {availability}
        </span>
      </div>

      <p className="trip-artist">{trip.artista}</p>
      <h3 className="trip-title">{trip.titulo}</h3>
      <p className="trip-event-date"><CalendarDays size={13} aria-hidden="true" />{formatDate(trip.fecha_evento)}</p>

      <div className="trip-details">
        <p><MapPin size={14} aria-hidden="true" /><span>{trip.recinto}</span></p>
        <p><MapPin size={14} aria-hidden="true" /><span>{trip.origen} <span aria-hidden="true">→</span> {trip.destino}</span></p>
        <p><Clock3 size={14} aria-hidden="true" /><span>Salida {formatDateTime(trip.fecha_salida)}</span></p>
      </div>

      {seats && availableSeats !== undefined ? (
        <div className="trip-availability">
          <div className="availability-caption">
            <span>{availableSeats} {availableSeats === 1 ? 'libre' : 'libres'}</span>
            <span>{occupiedSeats}/{seats.length} ocupados</span>
          </div>
          <div
            className="availability-track"
            role="progressbar"
            aria-label="Asientos ocupados"
            aria-valuemin={0}
            aria-valuemax={seats.length}
            aria-valuenow={occupiedSeats}
          >
            <span style={{ width: `${fillPercent}%` }} />
          </div>
        </div>
      ) : (
        <div className="trip-availability availability-unreported">
          Disponibilidad por confirmar
        </div>
      )}

      {expanded && (
        <div className="trip-extra" aria-live="polite">
          <p><Clock3 size={13} aria-hidden="true" /> Regreso {formatDateTime(trip.fecha_retorno)}</p>
          {trip.descripcion && <p className="trip-description">{trip.descripcion}</p>}
        </div>
      )}

      <div className="trip-card-footer">
        <div className="trip-price">
          <span>Desde</span>
          <strong>{currencyFormatter.format(trip.precio_ida)}</strong>
          <small>{currencyFormatter.format(trip.precio_ida_y_vuelta)} ida y vuelta</small>
        </div>
        <div className="trip-card-actions">
          <button
            className="trip-details-toggle"
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((current) => !current)}
          >
            {expanded ? 'Cerrar' : 'Ver viaje'}
          </button>
          <button
            className="trip-select"
            type="button"
            disabled={isFull || !seats?.length}
            onClick={() => onChooseSeat(trip.id)}
          >
            Elegir asiento
          </button>
        </div>
      </div>
    </article>
  )
}
