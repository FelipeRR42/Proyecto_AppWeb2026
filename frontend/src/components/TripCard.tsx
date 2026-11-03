import { Clock3, MapPin, Ticket } from 'lucide-react'
import type { Trip } from '../types/trip'

type TripCardProps = {
  trip: Trip
}

const dateFormatter = new Intl.DateTimeFormat('es-CL', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  timeZone: 'America/Santiago',
})

const timeFormatter = new Intl.DateTimeFormat('es-CL', {
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

function formatTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '--:--' : timeFormatter.format(date)
}

export default function TripCard({ trip }: TripCardProps) {
  const seats = trip.asientos
  const availableSeats = seats?.filter((seat) => seat.estado === 'disponible').length
  const occupiedSeats = seats && availableSeats !== undefined
    ? seats.length - availableSeats
    : undefined
  const isFull = trip.estado === 'lleno' || availableSeats === 0
  const isAlmostFull =
    !isFull &&
    availableSeats !== undefined &&
    seats !== undefined &&
    seats.length > 0 &&
    availableSeats / seats.length <= 0.25
  const badgeLabel = isFull
    ? 'Agotado'
    : isAlmostFull
      ? 'Casi lleno'
      : 'Disponible'

  return (
    <article className="trip-card">
      <div className="trip-main">
        <div className="trip-copy">
          <div className="trip-meta">
            <span className="trip-type"><Ticket size={12} aria-hidden="true" /> Viaje</span>
            <span className="trip-date">{formatDate(trip.fecha_evento)}</span>
          </div>
          <h2 className="trip-title">{trip.artista}</h2>
          <p className="trip-subtitle">{trip.titulo}</p>
          <div className="trip-details">
            <p><MapPin size={13} aria-hidden="true" /><span>{trip.recinto}</span></p>
            <p><MapPin size={13} aria-hidden="true" /><span>{trip.origen}</span></p>
          </div>
        </div>

        <div className="trip-schedule">
          <p><Clock3 size={13} aria-hidden="true" /><span>Salida {formatTime(trip.fecha_salida)}</span></p>
          <p><Clock3 size={13} aria-hidden="true" /><span>Regreso {formatTime(trip.fecha_retorno)}</span></p>
        </div>
      </div>

      <div className="trip-purchase">
        <span className={`availability-badge${isFull ? ' availability-full' : isAlmostFull ? ' availability-low' : ''}`}>
          <span className="availability-dot" aria-hidden="true" />
          {badgeLabel}
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
          className={`select-trip${isFull ? ' select-trip-full' : ''}`}
          type="button"
          disabled
          title={isFull ? 'Este viaje está agotado' : 'La selección aún no está disponible'}
        >
          {isFull ? 'Agotado' : 'Seleccionar'}
          {!isFull && <span aria-hidden="true">→</span>}
        </button>
      </div>
    </article>
  )
}
