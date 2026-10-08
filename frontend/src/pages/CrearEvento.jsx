import { useState } from 'react'
import { api } from '../api.js'

const INICIAL = {
  nombre: '', descripcion: '', lugar: '', fecha: '', cupo: 100, precio: 0,
  organizador_email: '', pin_staff: '',
}

export default function CrearEvento() {
  const [form, setForm] = useState(INICIAL)
  const [errores, setErrores] = useState({})
  const [estado, setEstado] = useState({ tipo: '', msg: '' })
  const [enviando, setEnviando] = useState(false)

  const set = (campo) => (e) => setForm({ ...form, [campo]: e.target.value })

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true)
    setErrores({})
    setEstado({ tipo: '', msg: '' })
    try {
      const evento = await api.crearEvento({
        nombre: form.nombre,
        descripcion: form.descripcion,
        lugar: form.lugar,
        // datetime-local no trae zona horaria: se convierte a ISO con la del navegador
        fecha_inicio: form.fecha ? new Date(form.fecha).toISOString() : '',
        cupo: Number.parseInt(form.cupo, 10),
        precio: Number(form.precio),
        organizador_email: form.organizador_email,
        pin_staff: form.pin_staff,
      })
      setEstado({ tipo: 'ok', msg: `Evento creado: ${evento.nombre}. Guarda el PIN para el check-in.` })
      setForm(INICIAL)
    } catch (err) {
      setErrores(err.detalles)
      setEstado({ tipo: 'error', msg: err.message })
    } finally {
      setEnviando(false)
    }
  }

  const campo = (nombre, label, props = {}) => (
    <label>
      {label}
      <input value={form[nombre]} onChange={set(nombre)} {...props} />
      {errores[nombre] && <small className="error">{errores[nombre]}</small>}
    </label>
  )

  return (
    <section className="angosto">
      <h1>Crear evento</h1>
      {estado.msg && <p className={`alerta ${estado.tipo}`}>{estado.msg}</p>}
      <form onSubmit={enviar} className="form">
        {campo('nombre', 'Nombre del evento', { required: true })}
        <label>
          Descripción
          <textarea value={form.descripcion} onChange={set('descripcion')} rows={3} />
        </label>
        {campo('lugar', 'Lugar', { required: true })}
        <label>
          Fecha y hora
          <input type="datetime-local" value={form.fecha} onChange={set('fecha')} required />
          {errores.fecha_inicio && <small className="error">{errores.fecha_inicio}</small>}
        </label>
        <div className="fila">
          {campo('cupo', 'Cupo', { type: 'number', min: 1, max: 5000, required: true })}
          {campo('precio', 'Precio (MXN)', { type: 'number', min: 0, step: '0.01', required: true })}
        </div>
        {campo('organizador_email', 'Tu correo (recibes el reporte)', { type: 'email', required: true })}
        {campo('pin_staff', 'PIN para el staff (4 a 8 dígitos)', { inputMode: 'numeric', required: true })}
        <button disabled={enviando}>{enviando ? 'Creando…' : 'Crear evento'}</button>
      </form>
    </section>
  )
}
