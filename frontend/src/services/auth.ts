const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

export type UserRole = 'pasajero' | 'administrador'

export interface SessionUser {
  role: UserRole
  nombre_completo: string
}

export interface LoginResponse {
  role: UserRole
  nombre_completo: string
}

export interface PassengerProfile {
  nombre_completo: string
  correo_electronico: string
  telefono: string
  direccion_retorno_predeterminada: string
}

let csrfTokenCache: string | null = null

function clearLegacyTokens(): void {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem('refresh_token')
  sessionStorage.removeItem('session_user')
}

clearLegacyTokens()

export function saveSession(session: LoginResponse): void {
  clearLegacyTokens()
  sessionStorage.setItem('user_role', session.role)
  sessionStorage.setItem('user_name', session.nombre_completo)
}

export function clearSession(): void {
  clearLegacyTokens()
  sessionStorage.removeItem('user_role')
  sessionStorage.removeItem('user_name')
  sessionStorage.removeItem('session_user')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function getErrorMessage(data: unknown, fallback: string): string {
  if (!isRecord(data)) return fallback

  for (const key of ['detail', 'message', 'error', 'non_field_errors']) {
    const value = data[key]
    if (typeof value === 'string') return value
    if (Array.isArray(value) && value.every((item) => typeof item === 'string')) {
      return value.join(' ')
    }
  }

  const fieldErrors = Object.values(data).flatMap((value) =>
    typeof value === 'string'
      ? [value]
      : Array.isArray(value) && value.every((item) => typeof item === 'string')
        ? value
        : [],
  )
  if (fieldErrors.length > 0) return fieldErrors.join(' ')

  return fallback
}

export async function getCsrfToken(): Promise<string> {
  if (csrfTokenCache) return csrfTokenCache

  let response: Response
  try {
    response = await fetch(`${API_URL}/auth/csrf/`, {
      headers: { Accept: 'application/json' },
      credentials: 'include',
    })
  } catch {
    throw new Error('No pudimos conectar con el servidor. Inténtalo nuevamente.')
  }

  let data: unknown
  try {
    data = await response.json()
  } catch {
    data = null
  }
  if (!response.ok || !isRecord(data) || typeof data.csrfToken !== 'string') {
    throw new Error('No se pudo iniciar una solicitud segura. Recarga la página e inténtalo nuevamente.')
  }

  csrfTokenCache = data.csrfToken
  return csrfTokenCache
}

async function postAuthRequest(path: string, body: Record<string, string>) {
  let response: Response

  try {
    const csrfToken = await getCsrfToken()
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'include',
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error('No pudimos conectar con el servidor. Inténtalo nuevamente.')
  }

  let data: unknown
  try {
    data = await response.json()
  } catch {
    data = null
  }

  return { response, data }
}

export async function refreshAccessToken(): Promise<boolean> {
  const { response } = await postAuthRequest('/auth/refresh/', {})
  if (!response.ok) {
    clearSession()
    return false
  }

  return true
}

export async function logoutSession(): Promise<void> {
  const { response } = await postAuthRequest('/auth/logout/', {})
  if (!response.ok) {
    throw new Error('No se pudo cerrar la sesión en el servidor.')
  }
  clearSession()
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const { response, data } = await postAuthRequest('/auth/login/', {
    correo_electronico: email,
    contrasenia: password,
  })

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        response.status === 401
          ? 'El correo electrónico o la contraseña son incorrectos.'
          : 'No se pudo iniciar sesión. Inténtalo nuevamente.',
      ),
    )
  }

  if (!isRecord(data)) {
    throw new Error('El servidor devolvió una respuesta de inicio de sesión inválida.')
  }

  const role = data.role
  const nombreCompleto = data.nombre_completo

  if (
    (role !== 'pasajero' && role !== 'administrador') ||
    typeof nombreCompleto !== 'string'
  ) {
    throw new Error('El servidor devolvió datos de sesión incompletos o inválidos.')
  }

  return { role, nombre_completo: nombreCompleto }
}

export async function getCurrentPassengerProfile(): Promise<PassengerProfile> {
  const sendRequest = async () => {
    try {
      return await fetch(`${API_URL}/auth/profile/`, {
        headers: { Accept: 'application/json' },
        credentials: 'include',
      })
    } catch {
      throw new Error('No pudimos conectar con el servidor. Inténtalo nuevamente.')
    }
  }

  let response = await sendRequest()
  if (response.status === 401) {
    if (!(await refreshAccessToken())) {
      throw new Error('Tu sesión venció o ya no es válida. Inicia sesión nuevamente.')
    }
    response = await sendRequest()
  }

  let data: unknown
  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    if (response.status === 401) clearSession()
    throw new Error(getErrorMessage(data, 'No se pudieron cargar los datos del perfil.'))
  }

  if (
    !isRecord(data) ||
    typeof data.nombre_completo !== 'string' ||
    typeof data.correo_electronico !== 'string' ||
    typeof data.telefono !== 'string' ||
    typeof data.direccion_retorno_predeterminada !== 'string'
  ) {
    throw new Error('El servidor devolvió datos de perfil incompletos o inválidos.')
  }

  return {
    nombre_completo: data.nombre_completo,
    correo_electronico: data.correo_electronico,
    telefono: data.telefono,
    direccion_retorno_predeterminada: data.direccion_retorno_predeterminada,
  }
}

export function getSessionUser(): SessionUser | null {
  const role = sessionStorage.getItem('user_role')
  if (role === 'pasajero' || role === 'administrador') {
    return {
      role,
      nombre_completo: sessionStorage.getItem('user_name') ?? '',
    }
  }
  sessionStorage.removeItem('user_role')
  sessionStorage.removeItem('user_name')
  return null
}

export async function registerPassenger({
  name,
  email,
  phone,
  address,
  password,
}: {
  name: string
  email: string
  phone: string
  address: string
  password: string
}): Promise<void> {
  const { response, data } = await postAuthRequest('/auth/register/', {
    nombre_completo: name,
    correo_electronico: email,
    contrasenia: password,
    direccion_retorno_predeterminada: address,
    telefono: phone,
  })

  if (!response.ok) {
    const fallback =
      response.status === 409
        ? 'Este correo electrónico ya está registrado.'
        : 'No se pudo crear la cuenta. Inténtalo nuevamente.'
    throw new Error(getErrorMessage(data, fallback))
  }
}

export async function registerAndLoginPassenger({
  name,
  email,
  phone,
  address,
  password,
}: {
  name: string
  email: string
  phone: string
  address: string
  password: string
}): Promise<LoginResponse> {
  const { response, data } = await postAuthRequest('/auth/register/', {
    nombre_completo: name,
    correo_electronico: email,
    contrasenia: password,
    direccion_retorno_predeterminada: address,
    telefono: phone,
  })

  if (!response.ok && response.status !== 409) {
    throw new Error(
      getErrorMessage(data, 'No se pudo crear la cuenta. Inténtalo nuevamente.'),
    )
  }

  const session = await login(email, password)
  saveSession(session)
  return session
}
