const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

export type UserRole = 'pasajero' | 'administrador'

interface LoginResponse {
  access: string
  role: UserRole
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

  return { access, role }
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
