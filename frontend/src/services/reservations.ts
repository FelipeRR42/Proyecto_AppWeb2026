import { API_URL } from './trips'

export type PassengerDetails = {
  nombre_completo: string
  correo_electronico: string
  contrasenia: string
  direccion_retorno_predeterminada: string
  telefono: string
}

export type Reservation = {
  id_reserva: string
  estado: string
  bloqueado_hasta: string
}

async function getErrorMessage(response: Response): Promise<string> {
  const body = await response.text()

  if (body) {
    try {
      const data: unknown = JSON.parse(body)
      if (typeof data === 'object' && data !== null) {
        const values = Object.values(data as Record<string, unknown>)
          .flatMap((value) => Array.isArray(value) ? value : [value])
          .filter((value): value is string => typeof value === 'string')
        if (values.length > 0) return values.join(' ')
      }
    } catch {
      return body
    }
  }

  return `No se pudo completar la solicitud (HTTP ${response.status}).`
}

async function postJson(path: string, payload: unknown): Promise<unknown> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json() as Promise<unknown>
}

export async function createPassenger(details: PassengerDetails): Promise<string> {
  const response = await postJson('/pasajeros/', details)
  if (
    typeof response !== 'object' ||
    response === null ||
    !('id' in response) ||
    typeof response.id !== 'string' ||
    response.id.length === 0
  ) {
    throw new Error('La API no devolvió el identificador del pasajero.')
  }
  return response.id
}

export async function createReservation(payload: {
  id_pasajero: string
  id_viaje: string
  tipo_viaje: 'ida' | 'ida_vuelta'
  asientos: number[]
  direccion_retorno: string | null
}): Promise<Reservation> {
  const response = await postJson('/reservas/', payload)
  if (
    typeof response !== 'object' ||
    response === null ||
    !('id_reserva' in response) ||
    typeof response.id_reserva !== 'string' ||
    !('estado' in response) ||
    typeof response.estado !== 'string' ||
    !('bloqueado_hasta' in response) ||
    typeof response.bloqueado_hasta !== 'string'
  ) {
    throw new Error('La API devolvió una respuesta de reserva con un formato inesperado.')
  }
  if (Number.isNaN(Date.parse(response.bloqueado_hasta))) {
    throw new Error('La API devolvió un vencimiento de bloqueo inválido.')
  }
  return {
    id_reserva: response.id_reserva,
    estado: response.estado,
    bloqueado_hasta: response.bloqueado_hasta,
  }
}

export async function cancelReservation(reservationId: string): Promise<void> {
  const response = await fetch(
    `${API_URL}/reservas/${encodeURIComponent(reservationId)}/cancelar/`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
    },
  )

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }
}
