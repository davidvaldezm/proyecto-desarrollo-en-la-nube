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
  misBoletos: (email) => request('GET', `/boletos?email=${encodeURIComponent(email)}`), // Flujo 1
  checkin: (datos) => request('POST', '/checkin', datos), // Flujo 2
}

// UUID v4 para la llave de idempotencia de la compra. crypto.randomUUID solo existe en HTTPS,
// así que hay respaldo con getRandomValues (disponible también en HTTP).
export function nuevoId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID()
  const b = window.crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

// Recordar el correo del comprador en este navegador (opcional; puede no estar disponible).
export const correoGuardado = {
  leer: () => { try { return localStorage.getItem('paseqr-email') || '' } catch { return '' } },
  guardar: (e) => { try { localStorage.setItem('paseqr-email', e) } catch { /* sin almacenamiento */ } },
}
