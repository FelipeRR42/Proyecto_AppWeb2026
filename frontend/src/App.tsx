import { useCallback, useEffect, useState } from 'react'
import { BusFront } from 'lucide-react'
import HowItWorks from './components/HowItWorks'
import HeroSection from './components/HeroSection'
import SiteHeader from './components/SiteHeader'
import TripsSection from './components/TripsSection'
import { getUpcomingTrips } from './services/trips'
import type { Trip } from './types/trip'

export default function App() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const retry = useCallback(() => setReloadKey((key) => key + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    async function loadTrips() {
      setLoading(true)
      setError(null)

      try {
        setTrips(await getUpcomingTrips(controller.signal))
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
  }, [reloadKey])

  return (
    <>
      <SiteHeader />
      <main>
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
        <TripsSection
          trips={trips}
          loading={loading}
          error={error}
          onRetry={retry}
        />
        <HowItWorks />
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
