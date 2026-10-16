import { useEffect, useState } from 'react'
import { api, correoGuardado, nuevoId } from '../api.js'

export const fmtFecha = (iso) =>
  new Date(iso).toLocaleString('es-MX', { dateStyle: 'full', timeStyle: 'short' })
const fmtPrecio = (p) => (Number(p) === 0 ? 'Gratis' : `$${Number(p).toFixed(2)} MXN`)

// Flujo 1: formulario de compra. El compra_id se genera al abrir el formulario y se
// reutiliza en reintentos, así el backend no duplica boletos (idempotencia).
function FormCompra({ evento, onComprado, onCancelar }) {
  const [compraId] = useState(nuevoId)
  const [form, setForm] = useState({ nombre: '', email: correoGuardado.leer(), cantidad: 1 })
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const set = (c) => (e) => setForm({ ...form, [c]: e.target.value })

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true)
    setError('')
    setErrores({})
    try {
      const r = await api.comprar({
        compra_id: compraId, evento_id: evento.evento_id, nombre: form.nombre,
        email: form.email, cantidad: Number.parseInt(form.cantidad, 10),
      })
      correoGuardado.guardar(form.email)
      onComprado(r, form.email)
    } catch (err) {
      setErrores(err.detalles || {})
      setError(err.status === 409 ? `${err.message}. Disponibles: ${err.detalles?.disponibles ?? 0}` : err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form compra" onSubmit={enviar}>
      {error && <p className="alerta error">{error}</p>}
      <label>Nombre<input value={form.nombre} onChange={set('nombre')} required />
        {errores.nombre && <small className="error">{errores.nombre}</small>}</label>
      <label>Correo<input type="email" value={form.email} onChange={set('email')} required />
        {errores.email && <small className="error">{errores.email}</small>}</label>
      <label>Boletos
        <select value={form.cantidad} onChange={set('cantidad')}>
          {[1, 2, 3, 4].filter((n) => n <= evento.disponibles).map((n) => <option key={n}>{n}</option>)}
        </select>
      </label>
      <div className="fila">
        <button type="button" className="secundario" onClick={onCancelar}>Cancelar</button>
        <button disabled={enviando}>{enviando ? 'Comprando…' : 'Confirmar compra'}</button>
      </div>
    </form>
  )
}

export default function Eventos() {
  const [eventos, setEventos] = useState(null)
  const [error, setError] = useState('')
  const [comprando, setComprando] = useState(null)
  const [aviso, setAviso] = useState(null)

  const cargar = () => api.listarEventos().then((d) => setEventos(d.eventos)).catch((e) => setError(e.message))
  useEffect(() => { cargar() }, [])

  if (error) return <p className="alerta error">No se pudieron cargar los eventos: {error}</p>
  if (!eventos) return <p className="muted">Cargando eventos…</p>

  return (
    <section>
      <h1>Próximos eventos</h1>
      {aviso && (
        <p className="alerta ok">
          ¡Listo! Compraste {aviso.n} boleto(s). Estamos generando tus PDF con código QR:
          {' '}<a href="#/mis-boletos">ve a Mis boletos</a>. Si es tu primera compra, revisa tu correo y
          confirma la suscripción de AWS para recibir avisos.
        </p>
      )}
      {eventos.length === 0 && (
        <p className="muted">No hay eventos a la venta. <a href="#/organizar">Crea el primero</a>.</p>
      )}
      <div className="grid">
        {eventos.map((ev) => (
          <article key={ev.evento_id} className="card">
            <h2>{ev.nombre}</h2>
            <p className="muted">{fmtFecha(ev.fecha_inicio)}</p>
            <p>{ev.lugar}</p>
            {ev.descripcion && <p className="desc">{ev.descripcion}</p>}
            <div className="card-pie">
              <strong>{fmtPrecio(ev.precio)}</strong>
              <span className={ev.disponibles > 0 ? 'ok' : 'agotado'}>
                {ev.disponibles > 0 ? `${ev.disponibles} disponibles` : 'Agotado'}
              </span>
            </div>
            {comprando === ev.evento_id ? (
              <FormCompra
                evento={ev}
                onCancelar={() => setComprando(null)}
                onComprado={(r) => { setComprando(null); setAviso({ n: r.boletos.length }); cargar() }}
              />
            ) : (
              <button disabled={ev.disponibles <= 0} onClick={() => { setAviso(null); setComprando(ev.evento_id) }}>
                {ev.disponibles > 0 ? 'Comprar boleto' : 'Agotado'}
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
