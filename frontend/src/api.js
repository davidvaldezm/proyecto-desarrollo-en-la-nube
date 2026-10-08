// Cliente de la API de PaseQR. La URL viene de VITE_API_URL (ver .env.example).
const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.error || `Error ${status}`)
    this.status = status
    this.detalles = body?.detalles || {}
  }
}

async function request(method, path, body) {
  if (!API_URL) throw new ApiError(0, { error: 'Falta configurar VITE_API_URL' })
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

export const api = {
  listarEventos: () => request('GET', '/eventos'),
  obtenerEvento: (id) => request('GET', `/eventos/${encodeURIComponent(id)}`),
  crearEvento: (evento) => request('POST', '/eventos', evento),
  comprar: (compra) => request('POST', '/compras', compra), // Flujo 1
  checkin: (datos) => request('POST', '/checkin', datos), // Flujo 2
}
