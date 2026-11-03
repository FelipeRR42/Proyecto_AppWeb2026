import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { RotateCw, SlidersHorizontal, X } from 'lucide-react'
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

export default function TripsSection() {
  const [draftFilters, setDraftFilters] = useState<TripFilters>(EMPTY_FILTERS)
  const [filters, setFilters] = useState<TripFilters>(EMPTY_FILTERS)
  const [trips, setTrips] = useState<Trip[]>([])
  const [origins, setOrigins] = useState<string[]>([])
  const [artists, setArtists] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterError, setFilterError] = useState<string | null>(null)
  const [requestKey, setRequestKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadTrips() {
      setLoading(true)
      setError(null)

      try {
        const [results, availableTrips] = await Promise.all([
          getUpcomingTrips(filters, controller.signal),
          getUpcomingTrips(EMPTY_FILTERS, controller.signal),
        ])
        setTrips(results)
        const selectableTrips = availableTrips.filter(
          (trip) =>
            trip.estado === 'programado' &&
            (trip.asientos === undefined ||
              trip.asientos.some((seat) => seat.estado === 'disponible')),
        )
        const availableOrigins = [...new Set(selectableTrips.map((trip) => trip.origen))]
          .sort((first, second) => first.localeCompare(second, 'es-CL'))
        const availableArtists = [...new Set(selectableTrips.map((trip) => trip.artista))]
          .sort((first, second) => first.localeCompare(second, 'es-CL'))
        setOrigins(availableOrigins)
        setArtists(availableArtists)

        if (filters.origen && !availableOrigins.includes(filters.origen)) {
          setFilters((current) => ({ ...current, origen: '' }))
          setDraftFilters((current) => ({ ...current, origen: '' }))
        }
        if (filters.artista && !availableArtists.includes(filters.artista)) {
          setFilters((current) => ({ ...current, artista: '' }))
          setDraftFilters((current) => ({ ...current, artista: '' }))
        }
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
  }, [filters, requestKey])

  const activeFilterCount = useMemo(
    () =>
      Number(Boolean(filters.fecha)) +
      Number(Boolean(filters.origen)) +
      Number(Boolean(filters.artista)) +
      Number(Boolean(filters.precioMinimo)) +
      Number(Boolean(filters.precioMaximo)) +
      Number(Boolean(filters.cuposMinimos)),
    [filters],
  )

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const minimumPrice = Number(draftFilters.precioMinimo)
    const maximumPrice = Number(draftFilters.precioMaximo)
    if (
      draftFilters.precioMinimo &&
      draftFilters.precioMaximo &&
      maximumPrice < minimumPrice
    ) {
      setFilterError('El precio máximo debe ser mayor o igual al mínimo.')
      return
    }

    setFilterError(null)
    setFilters({ ...draftFilters })
    setRequestKey((key) => key + 1)
  }

  function clearFilters() {
    setDraftFilters(EMPTY_FILTERS)
    setFilters(EMPTY_FILTERS)
    setFilterError(null)
    setRequestKey((key) => key + 1)
  }

  function updateFilter<Key extends keyof TripFilters>(
    key: Key,
    value: TripFilters[Key],
  ) {
    setDraftFilters((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="search-layout" aria-label="Búsqueda de viajes">
      <aside className="filter-panel">
        <div className="panel-title">
          <SlidersHorizontal size={15} aria-hidden="true" />
          <h2>Filtros</h2>
        </div>

        <form className="filter-form" onSubmit={applyFilters}>
          <label className="filter-field">
            <span>Fecha de viaje</span>
            <input
              type="date"
              value={draftFilters.fecha}
              onChange={(event) => updateFilter('fecha', event.target.value)}
            />
          </label>

          <label className="filter-field">
            <span>Ubicación de salida</span>
            <select
              value={draftFilters.origen}
              onChange={(event) => updateFilter('origen', event.target.value)}
            >
              <option value="">Todas las ciudades</option>
              {origins.map((origin) => (
                <option key={origin} value={origin}>{origin}</option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Evento musical</span>
            <select
              value={draftFilters.artista}
              onChange={(event) => updateFilter('artista', event.target.value)}
            >
              <option value="">Todos los artistas</option>
              {artists.map((artist) => (
                <option key={artist} value={artist}>{artist}</option>
              ))}
            </select>
          </label>

          <fieldset className="filter-field price-filter">
            <legend>Precio por asiento (CLP)</legend>
            <div className="price-inputs">
              <label>
                <span className="visually-hidden">Precio mínimo</span>
                <input
                  type="number"
                  min="0"
                  inputMode="numeric"
                  placeholder="Mín."
                  value={draftFilters.precioMinimo}
                  onChange={(event) => {
                    updateFilter('precioMinimo', event.target.value)
                    setFilterError(null)
                  }}
                />
              </label>
              <span aria-hidden="true">—</span>
              <label>
                <span className="visually-hidden">Precio máximo</span>
                <input
                  type="number"
                  min="0"
                  inputMode="numeric"
                  placeholder="Máx."
                  value={draftFilters.precioMaximo}
                  onChange={(event) => {
                    updateFilter('precioMaximo', event.target.value)
                    setFilterError(null)
                  }}
                />
              </label>
            </div>
          </fieldset>

          <label className="filter-field">
            <span>Cupos mínimos</span>
            <input
              type="number"
              min="0"
              inputMode="numeric"
              placeholder="Sin mínimo"
              value={draftFilters.cuposMinimos}
              onChange={(event) => updateFilter('cuposMinimos', event.target.value)}
            />
          </label>

          <label className="filter-field">
            <span>Ordenar viajes</span>
            <select
              value={draftFilters.orden}
              onChange={(event) =>
                updateFilter('orden', event.target.value as TripFilters['orden'])
              }
            >
              <option value="fecha">Fecha más próxima</option>
              <option value="precio_asc">Menor precio</option>
              <option value="precio_desc">Mayor precio</option>
            </select>
          </label>

          {filterError && <p className="filter-error" role="alert">{filterError}</p>}

          <button className="apply-filters" type="submit" disabled={loading}>
            Aplicar filtros
          </button>
          <button
            className="clear-filters"
            type="button"
            onClick={clearFilters}
            disabled={loading && activeFilterCount === 0}
          >
            <X size={13} aria-hidden="true" />
            Limpiar filtros
          </button>
        </form>
      </aside>

      <div className="results-panel">
        <div className="results-heading">
          <p aria-live="polite">
            {loading ? 'Buscando viajes…' : `${trips.length} ${trips.length === 1 ? 'viaje encontrado' : 'viajes encontrados'}`}
          </p>
        </div>

        {loading && (
          <div className="results-list" aria-label="Cargando viajes" aria-busy="true">
            {[0, 1, 2].map((item) => (
              <div className="trip-skeleton" key={item}>
                <span className="skeleton-line skeleton-short" />
                <span className="skeleton-line skeleton-title" />
                <span className="skeleton-line" />
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="notice notice-error" role="alert">
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
          <div className="results-list">
            {trips.map((trip) => (
              <TripCard
                key={trip.id}
                trip={trip}
              />
            ))}
          </div>
        )}

        {!loading && !error && trips.length === 0 && (
          <div className="notice notice-empty">
            <div className="notice-copy">
              <strong>No encontramos viajes con esos filtros</strong>
              <p>Prueba cambiar los criterios de búsqueda o limpiar los filtros.</p>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
