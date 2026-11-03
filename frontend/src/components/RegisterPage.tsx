import { useState, type FormEvent } from 'react'
import { BusFront } from 'lucide-react'
import BackButton from './BackButton'
import { registerPassenger } from '../services/auth'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
type RegistrationField = 'name' | 'email' | 'phone' | 'address' | 'password'

export default function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Partial<Record<RegistrationField, string>>>({})
  const [formError, setFormError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrors({})
    setFormError('')

    const normalizedName = name.trim()
    const normalizedEmail = email.trim()
    const normalizedPhone = phone.trim()
    const normalizedAddress = address.trim()
    const validationErrors: Partial<Record<RegistrationField, string>> = {}

    if (!normalizedName) validationErrors.name = 'Ingresa tu nombre completo.'
    if (!normalizedEmail) {
      validationErrors.email = 'Ingresa tu correo electrónico.'
    } else if (!EMAIL_PATTERN.test(normalizedEmail)) {
      validationErrors.email = 'El correo debe tener un formato válido, por ejemplo nombre@dominio.cl.'
    }
    if (!normalizedPhone) validationErrors.phone = 'Ingresa tu teléfono de contacto.'
    if (!normalizedAddress) {
      validationErrors.address = 'Ingresa la dirección a la que normalmente regresarás.'
    } else if (normalizedAddress.length > 200) {
      validationErrors.address = 'La dirección no puede superar los 200 caracteres.'
    }
    if (!password) {
      validationErrors.password = 'Ingresa una contraseña.'
    } else if (password.length < 8) {
      validationErrors.password = 'La contraseña debe tener al menos 8 caracteres.'
    }

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setLoading(true)
    try {
      await registerPassenger({
        name: normalizedName,
        email: normalizedEmail,
        phone: normalizedPhone,
        address: normalizedAddress,
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
              aria-describedby={errors.name ? 'register-name-error' : undefined}
              aria-invalid={Boolean(errors.name)}
              id="register-name"
              name="name"
              onChange={(event) => {
                setName(event.target.value)
                setErrors((current) => ({ ...current, name: '' }))
              }}
              placeholder="Juan Pérez González"
              required
              type="text"
              value={name}
            />
            {errors.name && <p className="login-error field-error" id="register-name-error">{errors.name}</p>}

            <label htmlFor="register-email">Correo electrónico</label>
            <input
              autoComplete="email"
              aria-describedby={errors.email ? 'register-email-error' : undefined}
              aria-invalid={Boolean(errors.email)}
              id="register-email"
              name="email"
              onChange={(event) => {
                setEmail(event.target.value)
                setErrors((current) => ({ ...current, email: '' }))
              }}
              placeholder="juan@correo.com"
              required
              type="email"
              value={email}
            />
            {errors.email && <p className="login-error field-error" id="register-email-error">{errors.email}</p>}

            <label htmlFor="register-phone">Teléfono</label>
            <input
              autoComplete="tel"
              aria-describedby={errors.phone ? 'register-phone-error' : undefined}
              aria-invalid={Boolean(errors.phone)}
              id="register-phone"
              name="phone"
              onChange={(event) => {
                setPhone(event.target.value)
                setErrors((current) => ({ ...current, phone: '' }))
              }}
              placeholder="+56 9 1234 5678"
              required
              type="tel"
              value={phone}
            />
            {errors.phone && <p className="login-error field-error" id="register-phone-error">{errors.phone}</p>}

            <label htmlFor="register-address">Dirección de retorno predeterminada</label>
            <input
              autoComplete="street-address"
              aria-describedby={errors.address ? 'register-address-error' : undefined}
              aria-invalid={Boolean(errors.address)}
              id="register-address"
              maxLength={200}
              name="address"
              onChange={(event) => {
                setAddress(event.target.value)
                setErrors((current) => ({ ...current, address: '' }))
              }}
              placeholder="Av. Principal 123, Ovalle"
              required
              type="text"
              value={address}
            />
            {errors.address && <p className="login-error field-error" id="register-address-error">{errors.address}</p>}

            <label htmlFor="register-password">Contraseña</label>
            <input
              autoComplete="new-password"
              aria-describedby={errors.password ? 'register-password-error' : undefined}
              aria-invalid={Boolean(errors.password)}
              id="register-password"
              minLength={8}
              name="password"
              onChange={(event) => {
                setPassword(event.target.value)
                setErrors((current) => ({ ...current, password: '' }))
              }}
              placeholder="Mínimo 8 caracteres"
              required
              type="password"
              value={password}
            />
            {errors.password && <p className="login-error field-error" id="register-password-error">{errors.password}</p>}

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
