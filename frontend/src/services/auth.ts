const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

export type UserRole = 'pasajero' | 'administrador'

export interface SessionUser {
  id: string
  role: UserRole
  nombre_completo: string
  correo_electronico: string
  telefono: string
  direccion_retorno_predeterminada: string
}

interface LoginResponse {
  access: string
  role: UserRole
  user: SessionUser
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

async function postAuthRequest(path: string, body: Record<string, string>) {
  let response: Response

  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
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

  const user = isRecord(data.user) ? data.user : data
  const access =
    typeof data.access === 'string'
      ? data.access
      : typeof data.access_token === 'string'
        ? data.access_token
        : typeof data.token === 'string'
          ? data.token
          : ''
  const role = user.rol ?? user.role ?? data.rol ?? data.role

  if (
    !access ||
    (role !== 'pasajero' && role !== 'administrador')
  ) {
    throw new Error('El servidor devolvió datos de sesión incompletos o inválidos.')
  }

  if (
    typeof user.id !== 'string' ||
    typeof user.nombre_completo !== 'string' ||
    typeof user.correo_electronico !== 'string'
  ) {
    throw new Error('El servidor no devolvió los datos del perfil de usuario.')
  }

  return {
    access,
    role,
    user: {
      id: user.id,
      role,
      nombre_completo: user.nombre_completo,
      correo_electronico: user.correo_electronico,
      telefono: typeof user.telefono === 'string' ? user.telefono : '',
      direccion_retorno_predeterminada:
        typeof user.direccion_retorno_predeterminada === 'string'
          ? user.direccion_retorno_predeterminada
          : '',
    },
  }
}

export function getSessionUser(): SessionUser | null {
  const storedUser = sessionStorage.getItem('session_user')
  if (!storedUser) return null

  try {
    const user: unknown = JSON.parse(storedUser)
    if (
      isRecord(user) &&
      typeof user.id === 'string' &&
      (user.role === 'pasajero' || user.role === 'administrador') &&
      typeof user.nombre_completo === 'string' &&
      typeof user.correo_electronico === 'string' &&
      typeof user.telefono === 'string' &&
      typeof user.direccion_retorno_predeterminada === 'string'
    ) {
      return {
        id: user.id,
        role: user.role,
        nombre_completo: user.nombre_completo,
        correo_electronico: user.correo_electronico,
        telefono: user.telefono,
        direccion_retorno_predeterminada: user.direccion_retorno_predeterminada,
      }
    }
  } catch {
    sessionStorage.removeItem('session_user')
  }

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
  const { response, data } = await postAuthRequest('/pasajeros/', {
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
