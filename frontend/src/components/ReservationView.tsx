import { useEffect, useState, type FormEvent } from 'react'
import {
  AlertCircle,
  Armchair,
  ArrowLeft,
  BusFront,
  CalendarDays,
  Check,
  Clock3,
  MapPin,
  RotateCw,
} from 'lucide-react'
import {
  cancelReservation,
  createPassenger,
  createReservation,
  type PassengerDetails,
  type Reservation,
} from '../services/reservations'
import { getSessionUser } from '../services/auth'
import type { Trip, TripSeat } from '../types/trip'

type ReservationViewProps = {
  trip: Trip | null
  loading: boolean
  error: string | null
  onBack: () => void
  onRetry: () => void
}

type TripType = 'ida' | 'ida_vuelta'

const dateTimeFormatter = new Intl.DateTimeFormat('es-CL', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Santiago',
})

const currencyFormatter = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
})

function formatDateTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Fecha por confirmar' : dateTimeFormatter.format(date)
}

function seatState(seat: TripSeat): 'available' | 'occupied' | 'blocked' {
  if (seat.estado === 'disponible') return 'available'
  if (seat.estado === 'bloqueado') return 'blocked'
  return 'occupied'
}

function SeatMap({
  seats,
  selectedSeats,
  heldSeats,
  disabled,
  onToggle,
}: {
  seats: TripSeat[]
  selectedSeats: number[]
  heldSeats: number[]
  disabled: boolean
  onToggle: (seatNumber: number) => void
}) {
  const orderedSeats = [...seats].sort((first, second) => first.num_asiento - second.num_asiento)

  return (
    <div className="seat-map" aria-label="Mapa de asientos del bus">
      <div className="seat-map-front">
        <BusFront size={18} aria-hidden="true" />
        <span>Frente del bus</span>
      </div>
      <div className="seat-grid">
        {orderedSeats.map((seat, index) => {
          const state = seatState(seat)
          const isSelected = selectedSeats.includes(seat.num_asiento)
          const isHeld = heldSeats.includes(seat.num_asiento)
          const column = (index % 4) + (index % 4 >= 2 ? 1 : 0) + 1
          const row = Math.floor(index / 4) + 1

          return (
            <button
              className={`seat seat-${state}${isSelected || isHeld ? ' seat-selected' : ''}`}
              key={seat.num_asiento}
              type="button"
              style={{ gridColumn: column, gridRow: row }}
              disabled={disabled || isHeld || state !== 'available'}
              aria-pressed={isSelected || isHeld}
              aria-label={`Asiento ${seat.num_asiento}, ${
                isHeld ? 'bloqueado por tu reserva' : isSelected ? 'seleccionado' : state === 'available' ? 'disponible' : state === 'blocked' ? 'bloqueado' : 'ocupado'
              }`}
              onClick={() => onToggle(seat.num_asiento)}
            >
              {isSelected ? <Check size={16} aria-hidden="true" /> : seat.num_asiento}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function ReservationView({
  trip,
  loading,
  error,
  onBack,
  onRetry,
}: ReservationViewProps) {
  const signedInUser = getSessionUser()
  const usesSignedInAccount = signedInUser?.role === 'pasajero'
  const [selectedSeats, setSelectedSeats] = useState<number[]>([])
  const [tripType, setTripType] = useState<TripType>('ida')
  const [passenger, setPassenger] = useState<PassengerDetails>({
    nombre_completo: signedInUser?.nombre_completo ?? '',
    correo_electronico: signedInUser?.correo_electronico ?? '',
    contrasenia: '',
    direccion_retorno_predeterminada: signedInUser?.direccion_retorno_predeterminada ?? '',
    telefono: signedInUser?.telefono ?? '',
  })
  const [passengerId, setPassengerId] = useState<string | null>(
    usesSignedInAccount ? signedInUser.id : null,
  )
  const [reservation, setReservation] = useState<Reservation | null>(null)
  const [now, setNow] = useState(Date.now())
  const [submitting, setSubmitting] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const seats = trip?.asientos ?? []
  const selectedSeatCount = selectedSeats.length
  const seatPrice = trip
    ? tripType === 'ida' ? trip.precio_ida : trip.precio_ida_y_vuelta
    : 0
  const total = seatPrice * selectedSeatCount
  const availableCount = seats.filter((seat) => seatState(seat) === 'available').length
  const sortedSelection = [...selectedSeats].sort((first, second) => first - second)
  const heldSeats = reservation ? sortedSelection : []
  const expiry = reservation ? new Date(reservation.bloqueado_hasta).getTime() : 0
  const secondsRemaining = reservation
    ? Math.max(0, Math.ceil((expiry - now) / 1000))
    : 0

  useEffect(() => {
    if (!reservation) return
    const interval = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(interval)
  }, [reservation])

  useEffect(() => {
    if (!reservation || secondsRemaining > 0) return
    setReservation(null)
    setSelectedSeats([])
    setActionMessage('El tiempo de bloqueo terminó y los asientos se liberaron.')
    onRetry()
  }, [reservation, secondsRemaining, onRetry])

  function toggleSeat(seatNumber: number) {
    if (reservation || submitting) return
    setSelectedSeats((current) =>
      current.includes(seatNumber)
        ? current.filter((number) => number !== seatNumber)
        : [...current, seatNumber],
    )
  }

  function updatePassenger(field: keyof PassengerDetails, value: string) {
    setPassenger((current) => ({ ...current, [field]: value }))
  }

  async function handleReservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!trip || !selectedSeats.length || reservation) return

    setSubmitting(true)
    setActionError(null)
    setActionMessage(null)
    try {
      const id = passengerId ?? await createPassenger(passenger)
      if (!passengerId) {
        setPassengerId(id)
        setPassenger((current) => ({ ...current, contrasenia: '' }))
      }
      const created = await createReservation({
        id_pasajero: id,
        id_viaje: trip.id,
        tipo_viaje: tripType,
        asientos: sortedSelection,
        direccion_retorno: tripType === 'ida_vuelta'
          ? passenger.direccion_retorno_predeterminada
          : null,
      })
      if (!created.id_reserva || !created.bloqueado_hasta) {
        throw new Error('La API creó una reserva sin informar el vencimiento del bloqueo.')
      }
      setReservation(created)
      setNow(Date.now())
      setActionMessage('Asientos bloqueados. Completa el pago antes de que venza el plazo.')
      onRetry()
    } catch (reason) {
      setActionError(
        reason instanceof Error
          ? reason.message
          : 'No se pudo crear la reserva. Inténtalo nuevamente.',
      )
      if (reason instanceof Error && reason.message.includes('ya no están disponibles')) {
        onRetry()
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCancel(): Promise<boolean> {
    if (!reservation) return false
    setCancelling(true)
    setActionError(null)
    try {
      await cancelReservation(reservation.id_reserva)
      setReservation(null)
      setSelectedSeats([])
      setActionMessage('Reserva cancelada y asientos liberados.')
      onRetry()
      return true
    } catch (reason) {
      setActionError(
        reason instanceof Error
          ? reason.message
          : 'No se pudo cancelar la reserva.',
      )
      return false
    } finally {
      setCancelling(false)
    }
  }

  async function handleBack() {
    if (reservation) {
      if (!(await handleCancel())) return
    }
    onBack()
  }

  return (
    <section className="reservation-page">
      <div className="reservation-container">
        <button
          className="reservation-back"
          type="button"
          disabled={submitting || cancelling}
          onClick={() => void handleBack()}
        >
          <ArrowLeft size={15} aria-hidden="true" />
          Volver a los viajes
        </button>

        <div className="reservation-heading">
          <p className="section-kicker">Tu próximo concierto</p>
          <h1>Elige tu asiento</h1>
          <p>Selecciona tu lugar en el bus y revisa el resumen de tu viaje.</p>
        </div>

        {loading && (
          <div className="notice" role="status" aria-busy="true">
            <span className="notice-icon"><Armchair size={19} aria-hidden="true" /></span>
            <div className="notice-copy">
              <strong>Cargando asientos del viaje</strong>
              <p>Consultando disponibilidad actual en MiTransporte.</p>
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="notice notice-error" role="alert">
            <span className="notice-icon"><AlertCircle size={20} aria-hidden="true" /></span>
            <div className="notice-copy">
              <strong>No pudimos cargar este viaje.</strong>
              <p>{error}</p>
            </div>
            <button className="retry-button" onClick={onRetry} type="button">
              <RotateCw size={13} aria-hidden="true" />
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && trip && (
          <>
            <div className="reservation-trip-summary">
              <div className="reservation-trip-icon"><BusFront size={22} aria-hidden="true" /></div>
              <div className="reservation-trip-copy">
                <span>{trip.artista}</span>
                <h2>{trip.titulo}</h2>
                <div className="reservation-trip-meta">
                  <span><MapPin size={13} aria-hidden="true" />{trip.origen} <span aria-hidden="true">→</span> {trip.destino}</span>
                  <span><CalendarDays size={13} aria-hidden="true" />{formatDateTime(trip.fecha_evento)}</span>
                  <span><Clock3 size={13} aria-hidden="true" />Salida {formatDateTime(trip.fecha_salida)}</span>
                </div>
              </div>
              <span className="reservation-availability">
                {availableCount} {availableCount === 1 ? 'asiento disponible' : 'asientos disponibles'}
              </span>
            </div>

            <div className="reservation-layout">
              <section className="seat-panel" aria-labelledby="seat-panel-title">
                <div className="seat-panel-heading">
                  <div>
                    <p className="section-kicker">Mapa del vehículo</p>
                    <h2 id="seat-panel-title">Selecciona tus asientos</h2>
                  </div>
                  <span className="seat-count">{seats.length} asientos</span>
                </div>

                <fieldset
                  className="trip-type-options"
                  disabled={Boolean(reservation) || submitting}
                >
                  <legend>Tipo de viaje</legend>
                  <label className={tripType === 'ida' ? 'trip-type-option selected' : 'trip-type-option'}>
                    <input
                      type="radio"
                      name="trip-type"
                      value="ida"
                      checked={tripType === 'ida'}
                      onChange={() => setTripType('ida')}
                    />
                    Solo ida
                    <span>{currencyFormatter.format(trip.precio_ida)}</span>
                  </label>
                  <label className={tripType === 'ida_vuelta' ? 'trip-type-option selected' : 'trip-type-option'}>
                    <input
                      type="radio"
                      name="trip-type"
                      value="ida_vuelta"
                      checked={tripType === 'ida_vuelta'}
                      onChange={() => setTripType('ida_vuelta')}
                    />
                    Ida y vuelta
                    <span>{currencyFormatter.format(trip.precio_ida_y_vuelta)}</span>
                  </label>
                </fieldset>

                <div className="seat-legend" aria-label="Estados de los asientos">
                  <span><i className="legend-seat legend-available" />Disponible</span>
                  <span><i className="legend-seat legend-selected" />Seleccionado</span>
                  <span><i className="legend-seat legend-occupied" />Ocupado</span>
                  <span><i className="legend-seat legend-blocked" />Bloqueado</span>
                </div>

                {seats.length > 0 ? (
                  <SeatMap
                    seats={seats}
                    selectedSeats={selectedSeats}
                    heldSeats={heldSeats}
                    disabled={Boolean(reservation) || submitting}
                    onToggle={toggleSeat}
                  />
                ) : (
                  <div className="seat-map-empty">
                    <Armchair size={22} aria-hidden="true" />
                    <p>Este viaje todavía no tiene asientos publicados.</p>
                  </div>
                )}
              </section>

              <aside className="reservation-summary" aria-labelledby="reservation-summary-title">
                <p className="section-kicker">Tu viaje</p>
                <h2 id="reservation-summary-title">Resumen de selección</h2>

                <div className="summary-row">
                  <span>Asientos</span>
                  <strong>{sortedSelection.length ? sortedSelection.join(', ') : 'Sin seleccionar'}</strong>
                </div>
                <div className="summary-row">
                  <span>Tipo</span>
                  <strong>{tripType === 'ida' ? 'Solo ida' : 'Ida y vuelta'}</strong>
                </div>
                <div className="summary-row">
                  <span>Precio por asiento</span>
                  <strong>{currencyFormatter.format(seatPrice)}</strong>
                </div>
                <div className="summary-total">
                  <span>Total</span>
                  <strong>{currencyFormatter.format(total)}</strong>
                </div>

                {reservation ? (
                  <div className="reservation-hold" role="status" aria-live="polite">
                    <strong>Bloqueo activo</strong>
                    <span>
                      Tiempo restante: {Math.floor(secondsRemaining / 60)}:
                      {String(secondsRemaining % 60).padStart(2, '0')}
                    </span>
                    <div className="reservation-passenger-details">
                      <strong>Datos del pasajero</strong>
                      <dl>
                        <div>
                          <dt>Nombre</dt>
                          <dd>{passenger.nombre_completo}</dd>
                        </div>
                        <div>
                          <dt>Correo</dt>
                          <dd>{passenger.correo_electronico}</dd>
                        </div>
                        <div>
                          <dt>Teléfono</dt>
                          <dd>{passenger.telefono}</dd>
                        </div>
                        <div>
                          <dt>Dirección de retorno</dt>
                          <dd>{passenger.direccion_retorno_predeterminada}</dd>
                        </div>
                      </dl>
                    </div>
                    <button
                      className="reservation-cancel"
                      type="button"
                      disabled={cancelling}
                      onClick={() => void handleCancel()}
                    >
                      {cancelling ? 'Liberando…' : 'Cancelar y liberar asientos'}
                    </button>
                  </div>
                ) : (
                  <form className="reservation-form" onSubmit={(event) => void handleReservation(event)}>
                    {usesSignedInAccount ? (
                      <div className="reservation-account-summary">
                        <strong>Datos de tu cuenta</strong>
                        <span>{passenger.nombre_completo}</span>
                        <span>{passenger.correo_electronico}</span>
                        <span>{passenger.telefono || 'Teléfono no informado'}</span>
                        <span>{passenger.direccion_retorno_predeterminada || 'Dirección no informada'}</span>
                      </div>
                    ) : (
                      <fieldset disabled={Boolean(passengerId) || submitting}>
                        <legend>Datos del pasajero</legend>
                        {passengerId && (
                          <p className="reservation-form-note">
                            Datos registrados. Puedes volver a intentar el bloqueo con esta cuenta.
                          </p>
                        )}
                        <label>
                          Nombre completo
                          <input
                            autoComplete="name"
                            required
                            value={passenger.nombre_completo}
                            onChange={(event) => updatePassenger('nombre_completo', event.target.value)}
                          />
                        </label>
                        <label>
                          Correo electrónico
                          <input
                            autoComplete="email"
                            type="email"
                            required
                            value={passenger.correo_electronico}
                            onChange={(event) => updatePassenger('correo_electronico', event.target.value)}
                          />
                        </label>
                        {!passengerId && (
                          <label>
                            Contraseña
                            <input
                              autoComplete="new-password"
                              type="password"
                              minLength={8}
                              required
                              value={passenger.contrasenia}
                              onChange={(event) => updatePassenger('contrasenia', event.target.value)}
                            />
                          </label>
                        )}
                        <label>
                          Teléfono
                          <input
                            autoComplete="tel"
                            type="tel"
                            required
                            value={passenger.telefono}
                            onChange={(event) => updatePassenger('telefono', event.target.value)}
                          />
                        </label>
                        <label>
                          Dirección de retorno
                          <input
                            autoComplete="street-address"
                            required
                            value={passenger.direccion_retorno_predeterminada}
                            onChange={(event) => updatePassenger('direccion_retorno_predeterminada', event.target.value)}
                          />
                        </label>
                      </fieldset>
                    )}
                    {actionError && <p className="reservation-action-error" role="alert">{actionError}</p>}
                    {actionMessage && <p className="reservation-action-message" role="status">{actionMessage}</p>}
                    <button
                      className="reservation-confirm"
                      type="submit"
                      disabled={submitting || selectedSeats.length === 0 || availableCount === 0}
                    >
                      {submitting
                        ? 'Bloqueando asientos…'
                        : usesSignedInAccount
                          ? 'Bloquear asientos'
                          : passengerId
                            ? 'Reintentar bloqueo'
                            : 'Crear cuenta y bloquear'}
                    </button>
                    <p className="reservation-api-note">
                      Al confirmar, tus asientos quedan bloqueados por 5 minutos. No se realizará ningún cobro.
                    </p>
                  </form>
                )}
                {reservation && (
                  <>
                    {actionError && <p className="reservation-action-error" role="alert">{actionError}</p>}
                    {actionMessage && <p className="reservation-action-message" role="status">{actionMessage}</p>}
                  </>
                )}
              </aside>
            </div>
          </>
        )}
      </div>
    </section>
  )
}
