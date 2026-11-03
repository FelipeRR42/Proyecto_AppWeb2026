import SiteHeader from './components/SiteHeader'
import TripsSection from './components/TripsSection'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'

export default function App() {
  if (window.location.pathname === '/login' || window.location.pathname === '/login/') {
    return <LoginPage />
  }
  if (
    window.location.pathname === '/registro' ||
    window.location.pathname === '/registro/'
  ) {
    return <RegisterPage />
  }

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
