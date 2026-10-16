import { useEffect, useRef, useState } from 'react'
import { api, correoGuardado } from '../api.js'
import { fmtFecha } from './Eventos.jsx'

const ETIQUETAS = { PENDIENTE: 'Generando…', EMITIDO: 'Listo', USADO: 'Usado' }

// Flujo 1: consulta de boletos por correo y descarga del PDF (URL prefirmada de S3).
export default function MisBoletos() {
  const [email, setEmail] = useState(correoGuardado.leer())
  const [boletos, setBoletos] = useState(null)
  const [error, setError] = useState('')
  const timer = useRef(null)

  async function buscar(e) {
    e?.preventDefault()
    setError('')
    try {
      const r = await api.misBoletos(email)
      correoGuardado.guardar(email)
      setBoletos(r.boletos)
    } catch (err) {
      setError(err.message)
    }
  }

  // Mientras haya boletos en generación, refresca cada 3 s (la emisión es asíncrona vía SQS).
  useEffect(() => {
    clearTimeout(timer.current)
    if (boletos?.some((b) => b.estado === 'PENDIENTE')) timer.current = setTimeout(buscar, 3000)
    return () => clearTimeout(timer.current)
  }, [boletos])

  useEffect(() => { if (email) buscar() }, [])

  return (
    <section className="angosto">
      <h1>Mis boletos</h1>
      <form className="form fila" onSubmit={buscar}>
        <label>Correo con el que compraste
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <button className="boton-bajo">Buscar</button>
      </form>
      {error && <p className="alerta error">{error}</p>}
      {boletos && boletos.length === 0 && <p className="muted">No hay boletos con ese correo.</p>}
      <ul className="lista">
        {boletos?.map((b) => (
          <li key={b.boleto_id} className="card">
            <div className="card-pie">
              <strong>{b.evento_nombre}</strong>
              <span className={`estado ${b.estado}`}>{ETIQUETAS[b.estado] || b.estado}</span>
            </div>
            <p className="muted">{fmtFecha(b.fecha_evento)} · {b.lugar}</p>
            <p>Boleto {b.numero} · {b.nombre}</p>
            {b.pdf_url && <a className="boton" href={b.pdf_url} target="_blank" rel="noreferrer">Descargar PDF</a>}
            {b.estado === 'USADO' && <p className="muted">Entrada registrada: {fmtFecha(b.usado_en)}</p>}
          </li>
        ))}
      </ul>
    </section>
  )
}
