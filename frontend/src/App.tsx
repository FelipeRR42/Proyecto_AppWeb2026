import SiteHeader from './components/SiteHeader'
import TripsSection from './components/TripsSection'

export default function App() {
  return (
    <>
      <SiteHeader />
      <main className="search-page">
        <h1 className="page-title">Buscar viajes</h1>
        <TripsSection />
      </main>
    </>
  )
}
