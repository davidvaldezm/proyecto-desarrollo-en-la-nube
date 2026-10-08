import { useEffect, useState } from 'react'
import { api } from '../api.js'

const fmtFecha = (iso) =>
  new Date(iso).toLocaleString('es-MX', { dateStyle: 'full', timeStyle: 'short' })
const fmtPrecio = (p) => (Number(p) === 0 ? 'Gratis' : `$${Number(p).toFixed(2)} MXN`)

export default function Eventos() {
  const [eventos, setEventos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listarEventos()
      .then((data) => setEventos(data.eventos))
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <p className="alerta error">No se pudieron cargar los eventos: {error}</p>
  if (!eventos) return <p className="muted">Cargando eventos…</p>

  return (
    <section>
      <h1>Próximos eventos</h1>
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
            {/* Flujo 1 (David): formulario de compra que llama a api.comprar */}
            <button disabled title="Disponible cuando se implemente el Flujo 1">Comprar boleto</button>
          </article>
        ))}
      </div>
    </section>
  )
}
