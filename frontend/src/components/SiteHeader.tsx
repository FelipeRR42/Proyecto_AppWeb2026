import { BusFront, LogOut } from 'lucide-react'
import BackButton from './BackButton'
import { clearSession, getSessionUser } from '../services/auth'

export default function SiteHeader() {
  const isSearchPage = window.location.pathname.replace(/\/+$/, '') === '/viajes'
  const user = getSessionUser()

  function logout() {
    clearSession()
    window.location.assign('/')
  }

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
        {isSearchPage && <BackButton />}
        {user ? (
          <>
            <div className="account-profile">
              <strong>{user.nombre_completo}</strong>
              <span>{user.direccion_retorno_predeterminada || user.correo_electronico}</span>
            </div>
            <button
              className="account-button account-logout"
              type="button"
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
              onClick={logout}
            >
              <LogOut size={14} aria-hidden="true" />
            </button>
          </>
        ) : (
          <>
            <a className="account-button" href="/login">
              Ingresar
            </a>
            <a className="account-button account-button-primary" href="/registro">
              Registrarse
            </a>
          </>
        )}
      </nav>
    </header>
  )
}
