import { useState, type FormEvent } from 'react'
import { BusFront } from 'lucide-react'
import { login } from '../services/auth'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    const normalizedEmail = email.trim()
    if (!normalizedEmail || !password) {
      setError('Ingresa tu correo electrónico y contraseña.')
      return
    }
    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError('Ingresa un correo electrónico válido.')
      return
    }

    setLoading(true)
    try {
      const session = await login(normalizedEmail, password)
      sessionStorage.setItem('access_token', session.access)
      sessionStorage.setItem('user_role', session.role)
      window.location.assign(session.role === 'administrador' ? '/admin/' : '/')
    } catch (loginError) {
      setError(
        loginError instanceof Error
          ? loginError.message
          : 'Ocurrió un error inesperado. Inténtalo nuevamente.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <div className="login-content">
        <a className="login-brand" href="/" aria-label="MiTransporte, inicio">
          <span className="login-brand-icon">
            <BusFront size={21} strokeWidth={2.2} aria-hidden="true" />
          </span>
          <span>MiTransporte</span>
        </a>

        <section className="login-card" aria-labelledby="login-title">
          <h1 id="login-title">Bienvenido</h1>
          <p className="login-intro">Ingresa a tu cuenta para reservar</p>
          {new URLSearchParams(window.location.search).get('registered') === '1' && (
            <p className="login-success" role="status">
              Tu cuenta fue creada. Ya puedes iniciar sesión.
            </p>
          )}

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <label htmlFor="login-email">Correo electrónico</label>
            <input
              autoComplete="email"
              id="login-email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="tu@correo.com"
              type="email"
              value={email}
            />

            <label htmlFor="login-password">Contraseña</label>
            <input
              autoComplete="current-password"
              id="login-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              type="password"
              value={password}
            />

            {error && (
              <p className="login-error" role="alert">
                {error}
              </p>
            )}

            <button className="login-submit" disabled={loading} type="submit">
              {loading ? 'Iniciando sesión…' : 'Iniciar sesión'}
            </button>
          </form>

          <p className="login-register">
            ¿No tienes cuenta? <a href="/registro">Regístrate</a>
          </p>

          <div className="login-admin-note">
            Los administradores ingresan desde este mismo formulario.
          </div>
        </section>
      </div>
    </main>
  )
}
