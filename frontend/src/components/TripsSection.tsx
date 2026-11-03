import { AlertCircle, CalendarDays, RotateCw } from 'lucide-react'
import TripCard from './TripCard'
import type { Trip } from '../types/trip'

type TripsSectionProps = {
  trips: Trip[]
  loading: boolean
  error: string | null
  onRetry: () => void
  onChooseSeat: (tripId: string) => void
}

export default function TripsSection({
  trips,
  loading,
  error,
  onRetry,
  onChooseSeat,
}: TripsSectionProps) {
  return (
    <section className="trips-section" id="viajes">
      <div className="section-heading">
        <div>
          <p className="section-kicker">La próxima aventura empieza aquí</p>
          <h2>Próximos viajes</h2>
        </div>
        <a className="all-trips-link" href="#viajes">
          Explorar viajes <span aria-hidden="true">→</span>
        </a>
      </div>

      {loading && (
        <div className="trip-grid" aria-label="Cargando viajes" aria-busy="true">
          {[0, 1, 2].map((item) => (
            <div className="trip-skeleton" key={item}>
              <span className="skeleton-line skeleton-short" />
              <span className="skeleton-line skeleton-title" />
              <span className="skeleton-line" />
              <span className="skeleton-line skeleton-price" />
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="notice notice-error" role="alert">
          <span className="notice-icon"><AlertCircle size={20} aria-hidden="true" /></span>
          <div className="notice-copy">
            <strong>No pudimos cargar los viajes.</strong>
            <p>{error} Comprueba la conexión de Django con MongoDB e inténtalo otra vez.</p>
          </div>
          <button className="retry-button" onClick={onRetry} type="button">
            <RotateCw size={13} aria-hidden="true" />
            Reintentar
          </button>
        </div>
      )}

      {!loading && !error && trips.length > 0 && (
        <div className="trip-grid">
          {trips.slice(0, 3).map((trip) => (
            <TripCard key={trip.id} trip={trip} onChooseSeat={onChooseSeat} />
          ))}
        </div>
      )}

      {!loading && !error && trips.length === 0 && (
        <div className="notice notice-empty">
          <span className="notice-icon"><CalendarDays size={20} aria-hidden="true" /></span>
          <div className="notice-copy">
            <strong>Aún no hay viajes próximos</strong>
            <p>Cuando se publiquen nuevos viajes, aparecerán aquí.</p>
          </div>
        </div>
      )}
    </section>
  )
}
