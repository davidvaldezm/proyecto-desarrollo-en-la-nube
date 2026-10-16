import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'
import { api } from '../api.js'

const COLORES = { VALIDO: 'ok', YA_USADO: 'error', INVALIDO: 'error', OTRO_EVENTO: 'error', NO_EMITIDO: 'error' }

// Flujo 2: el staff elige el evento, ingresa su PIN y escanea el QR con la cámara.
// Si no hay cámara (o el sitio no es HTTPS), puede pegar el contenido del QR a mano.
export default function CheckIn() {
  const [eventos, setEventos] = useState([])
  const [eventoId, setEventoId] = useState('')
  const [pin, setPin] = useState('')
  const [manual, setManual] = useState('')
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState('')
  const [camara, setCamara] = useState(false)
  const scanner = useRef(null)
  const ultimo = useRef({ qr: '', t: 0 })
  const datos = useRef({})
  datos.current = { eventoId, pin }

  useEffect(() => { api.listarEventos().then((d) => setEventos(d.eventos)).catch(() => {}) }, [])
  useEffect(() => () => { scanner.current?.stop().catch(() => {}) }, [])

  async function validar(qr) {
    const ahora = Date.now()
    if (qr === ultimo.current.qr && ahora - ultimo.current.t < 3000) return // la cámara lee varias veces
    ultimo.current = { qr, t: ahora }
    setError('')
    try {
      setResultado(await api.checkin({ evento_id: datos.current.eventoId, pin_staff: datos.current.pin, qr }))
    } catch (err) {
      setResultado(null)
      setError(err.message)
    }
  }

  async function iniciarCamara() {
    setError('')
    try {
      scanner.current = new Html5Qrcode('lector-qr')
      await scanner.current.start({ facingMode: 'environment' }, { fps: 10, qrbox: 240 }, (texto) => validar(texto))
      setCamara(true)
    } catch (err) {
      setError(`No se pudo abrir la cámara (${err?.message || err}). Usa la captura manual.`)
    }
  }

  async function detenerCamara() {
    await scanner.current?.stop().catch(() => {})
    setCamara(false)
  }

  const listo = eventoId && /^\d{4,8}$/.test(pin)

  return (
    <section className="angosto">
      <h1>Check-in</h1>
      <div className="form">
        <label>Evento
          <select value={eventoId} onChange={(e) => setEventoId(e.target.value)}>
            <option value="">Selecciona…</option>
            {eventos.map((ev) => <option key={ev.evento_id} value={ev.evento_id}>{ev.nombre}</option>)}
          </select>
        </label>
        <label>PIN del staff<input inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value)} /></label>
      </div>

      {resultado && (
        <div className={`resultado ${COLORES[resultado.resultado]}`}>
          <strong>{resultado.mensaje}</strong>
          {resultado.nombre && <span>{resultado.nombre}</span>}
          {resultado.resultado === 'YA_USADO' && resultado.usado_en &&
            <span>Primer uso: {new Date(resultado.usado_en).toLocaleTimeString('es-MX')}</span>}
          <span className="contador">Asistentes: {resultado.asistentes}</span>
        </div>
      )}
      {error && <p className="alerta error">{error}</p>}

      <div id="lector-qr" className={camara ? 'lector activo' : 'lector'} />
      {listo && (camara
        ? <button className="secundario" onClick={detenerCamara}>Detener cámara</button>
        : <button onClick={iniciarCamara}>Escanear con la cámara</button>)}

      <form className="form manual" onSubmit={(e) => { e.preventDefault(); validar(manual.trim()) }}>
        <label>Captura manual del código
          <input value={manual} onChange={(e) => setManual(e.target.value)} placeholder="v1.…" />
        </label>
        <button disabled={!listo || !manual}>Validar</button>
      </form>
    </section>
  )
}
