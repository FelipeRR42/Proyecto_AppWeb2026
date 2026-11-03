import { BusFront } from 'lucide-react'

export default function SiteHeader() {
  const isSearchPage = window.location.pathname.replace(/\/+$/, '') === '/viajes'

  return (
    <header className="site-header">
      <a className="brand" href="/" aria-label="MiTransporte, inicio">
        <span className="brand-icon">
          <BusFront size={16} strokeWidth={2.2} aria-hidden="true" />
        </span>
        <span>MiTransporte</span>
      </a>

      <nav className="header-actions" aria-label="Cuenta">
        <span className="header-route">Ovalle <span aria-hidden="true">→</span> Santiago</span>
        <a className="account-button" href={isSearchPage ? '/' : '/viajes'}>
          {isSearchPage ? 'Inicio' : 'Explorar'}
        </a>
        <a className="account-button" href="/login">
          Ingresar
        </a>
        <a className="account-button account-button-primary" href="/registro">
          Registrarse
        </a>
      </nav>
    </header>
  )
}
