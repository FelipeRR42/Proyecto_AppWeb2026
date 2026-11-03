import { useEffect, useState } from 'react'
import { AlertCircle, CalendarDays, RotateCw } from 'lucide-react'
import TripCard from './TripCard'
import { getUpcomingTrips } from '../services/trips'
import type { Trip, TripFilters } from '../types/trip'

const EMPTY_FILTERS: TripFilters = {
  fecha: '',
  origen: '',
  artista: '',
  precioMinimo: '',
  precioMaximo: '',
  cuposMinimos: '',
  orden: 'fecha',
}

type HomeTripsSectionProps = {
  onChooseSeat: (tripId: string) => void
  reloadKey: number
}

export default function HomeTripsSection({
  onChooseSeat,
  reloadKey,
}: HomeTripsSectionProps) {
  const [trips, setTrips] = useState<Trip[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [requestKey, setRequestKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadTrips() {
      setLoading(true)
      setError(null)

      try {
        setTrips(await getUpcomingTrips(EMPTY_FILTERS, controller.signal))
      } catch (reason) {
        if (controller.signal.aborted) return
        setError(
          reason instanceof Error
            ? reason.message
            : 'Ocurrió un error inesperado al consultar la API.',
        )
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    void loadTrips()
    return () => controller.abort()
  }, [reloadKey, requestKey])

  return (
    <section className="trips-section" id="viajes">
      <div className="section-heading">
        <div>
          <p className="section-kicker">La próxima aventura empieza aquí</p>
          <h2>Próximos viajes</h2>
        </div>
        <a className="all-trips-link" href="/viajes">
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
            <p>{error} Comprueba tu conexión e inténtalo otra vez.</p>
          </div>
          <button
            className="retry-button"
            onClick={() => setRequestKey((key) => key + 1)}
            type="button"
          >
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
