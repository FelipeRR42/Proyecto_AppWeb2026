import { useCallback, useEffect, useState } from 'react'
import { BusFront } from 'lucide-react'
import HeroSection from './components/HeroSection'
import HomeTripsSection from './components/HomeTripsSection'
import HowItWorks from './components/HowItWorks'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import ReservationView from './components/ReservationView'
import SiteHeader from './components/SiteHeader'
import TripsSection from './components/TripsSection'
import { getTripById } from './services/trips'
import type { Trip } from './types/trip'

export default function App() {
  const [reloadKey, setReloadKey] = useState(0)
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null)
  const [selectedTrip, setSelectedTrip] = useState<Trip | null>(null)
  const [selectedTripLoading, setSelectedTripLoading] = useState(false)
  const [selectedTripError, setSelectedTripError] = useState<string | null>(null)
  const [selectedTripReloadKey, setSelectedTripReloadKey] = useState(0)

  const retryTrips = useCallback(() => setReloadKey((key) => key + 1), [])
  const retrySelectedTrip = useCallback(() => {
    setSelectedTripReloadKey((key) => key + 1)
    retryTrips()
  }, [retryTrips])
  const openTripReservation = useCallback((tripId: string) => {
    setSelectedTrip(null)
    setSelectedTripLoading(true)
    setSelectedTripId(tripId)
  }, [])

  useEffect(() => {
    if (!selectedTripId) {
      setSelectedTrip(null)
      setSelectedTripError(null)
      return
    }

    const tripId = selectedTripId
    const controller = new AbortController()

    async function loadSelectedTrip() {
      setSelectedTripLoading(true)
      setSelectedTripError(null)

      try {
        setSelectedTrip(await getTripById(tripId, controller.signal))
      } catch (reason) {
        if (controller.signal.aborted) return
        setSelectedTripError(
          reason instanceof Error
            ? reason.message
            : 'Ocurrió un error inesperado al consultar la API.',
        )
      } finally {
        if (!controller.signal.aborted) setSelectedTripLoading(false)
      }
    }

    void loadSelectedTrip()
    return () => controller.abort()
  }, [selectedTripId, selectedTripReloadKey])

  const pathname = window.location.pathname.replace(/\/+$/, '') || '/'
  if (pathname === '/login') return <LoginPage />
  if (pathname === '/registro') return <RegisterPage />

  return (
    <>
      <SiteHeader />
      <main>
        {selectedTripId ? (
          <ReservationView
            trip={selectedTrip}
            loading={selectedTripLoading}
            error={selectedTripError}
            onBack={() => setSelectedTripId(null)}
            onRetry={retrySelectedTrip}
          />
        ) : pathname === '/viajes' ? (
          <section className="search-page">
            <p className="section-kicker">Encuentra tu próximo viaje</p>
            <h1 className="page-title">Buscar viajes</h1>
            <TripsSection
              onChooseSeat={openTripReservation}
              reloadKey={reloadKey}
            />
          </section>
        ) : (
          <>
            <HeroSection />
            <section className="feature-strip" aria-label="Ventajas de MiTransporte">
              <div className="feature-item">
                <span className="feature-icon"><BusFront size={17} aria-hidden="true" /></span>
                <span><strong>Viajes a conciertos</strong> en un solo lugar</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon feature-icon-green">02</span>
                <span><strong>Tu asiento asegurado</strong> para disfrutar tranquilo</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon feature-icon-blue">03</span>
                <span><strong>Ida y vuelta</strong> para volver sin preocupaciones</span>
              </div>
            </section>
            <HomeTripsSection
              onChooseSeat={openTripReservation}
              reloadKey={reloadKey}
            />
            <HowItWorks />
          </>
        )}
      </main>
      <footer className="site-footer">
        <a className="brand footer-brand" href="#inicio">
          <span className="brand-icon"><BusFront size={15} aria-hidden="true" /></span>
          <span>MiTransporte</span>
        </a>
        <p>Tu viaje al concierto, sin complicaciones.</p>
      </footer>
    </>
  )
}
