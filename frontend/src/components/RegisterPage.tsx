import { useState, type FormEvent } from 'react'
import { BusFront } from 'lucide-react'
import BackButton from './BackButton'
import { registerPassenger } from '../services/auth'

export default function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [formError, setFormError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')

    setLoading(true)
    try {
      await registerPassenger({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        address: address.trim(),
        password,
      })
      window.location.assign('/login?registered=1')
    } catch (registrationError) {
      setFormError(
        registrationError instanceof Error
          ? registrationError.message
          : 'Ocurrió un error inesperado. Inténtalo nuevamente.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <div className="login-content">
        <BackButton />
        <a className="login-brand" href="/" aria-label="MiTransporte, inicio">
          <span className="login-brand-icon">
            <BusFront size={21} strokeWidth={2.2} aria-hidden="true" />
          </span>
          <span>MiTransporte</span>
        </a>

        <section className="login-card" aria-labelledby="register-title">
          <h1 id="register-title">Crear cuenta</h1>
          <p className="login-intro">Regístrate para reservar tu viaje</p>

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <label htmlFor="register-name">Nombre completo</label>
            <input
              autoComplete="name"
              id="register-name"
              name="name"
              onChange={(event) => setName(event.target.value)}
              placeholder="Juan Pérez González"
              type="text"
              value={name}
            />

            <label htmlFor="register-email">Correo electrónico</label>
            <input
              autoComplete="email"
              id="register-email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="juan@correo.com"
              type="email"
              value={email}
            />

            <label htmlFor="register-phone">Teléfono</label>
            <input
              autoComplete="tel"
              id="register-phone"
              name="phone"
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+56 9 1234 5678"
              type="tel"
              value={phone}
            />

            <label htmlFor="register-address">Dirección de retorno predeterminada</label>
            <input
              autoComplete="street-address"
              id="register-address"
              name="address"
              onChange={(event) => setAddress(event.target.value)}
              placeholder="Av. Principal 123, Ovalle"
              type="text"
              value={address}
            />

            <label htmlFor="register-password">Contraseña</label>
            <input
              autoComplete="new-password"
              id="register-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Contraseña"
              type="password"
              value={password}
            />

            {formError && (
              <p className="login-error" role="alert">
                {formError}
              </p>
            )}

            <button
              className="login-submit register-submit"
              disabled={loading}
              type="submit"
            >
              {loading ? 'Creando cuenta…' : 'Crear cuenta →'}
            </button>
          </form>

          <p className="login-register register-login">
            ¿Ya tienes cuenta? <a href="/login">Iniciar sesión</a>
          </p>
        </section>
      </div>
    </main>
  )
}
