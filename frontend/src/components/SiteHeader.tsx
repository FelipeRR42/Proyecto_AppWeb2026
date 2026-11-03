import { BusFront } from 'lucide-react'

export default function SiteHeader() {
  return (
    <header className="site-header">
      <a className="brand" href="#inicio" aria-label="MiTransporte, inicio">
        <span className="brand-icon">
          <BusFront size={16} strokeWidth={2.2} aria-hidden="true" />
        </span>
        <span>MiTransporte</span>
      </a>

      <nav className="header-actions" aria-label="Cuenta">
        <span className="header-route">Ovalle <span aria-hidden="true">→</span> Santiago</span>
        <button className="account-button" type="button" disabled aria-label="Inicio de sesión próximamente">
          Ingresar
        </button>
        <button className="account-button account-button-primary" type="button" disabled aria-label="Registro próximamente">
          Registrarse
        </button>
      </nav>
    </header>
  )
}
