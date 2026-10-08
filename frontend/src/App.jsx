import { useEffect, useState } from 'react'
import Eventos from './pages/Eventos.jsx'
import CrearEvento from './pages/CrearEvento.jsx'
import MisBoletos from './pages/MisBoletos.jsx'
import CheckIn from './pages/CheckIn.jsx'

// Router mínimo con hash (#/ruta): funciona en un bucket S3 sin configuración extra.
const RUTAS = {
  '/': { titulo: 'Eventos', Pagina: Eventos },
  '/organizar': { titulo: 'Crear evento', Pagina: CrearEvento },
  '/mis-boletos': { titulo: 'Mis boletos', Pagina: MisBoletos },
  '/checkin': { titulo: 'Check-in', Pagina: CheckIn },
}

function rutaActual() {
  return window.location.hash.replace(/^#/, '') || '/'
}

export default function App() {
  const [ruta, setRuta] = useState(rutaActual())

  useEffect(() => {
    const onHash = () => setRuta(rutaActual())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const base = '/' + (ruta.split('/')[1] || '')
  const { Pagina } = RUTAS[base] || RUTAS['/']

  return (
    <>
      <header className="topbar">
        <a className="logo" href="#/">Pase<span>QR</span></a>
        <nav>
          {Object.entries(RUTAS).map(([path, { titulo }]) => (
            <a key={path} href={`#${path}`} className={base === path ? 'activo' : ''}>{titulo}</a>
          ))}
        </nav>
      </header>
      <main>
        <Pagina ruta={ruta} />
      </main>
    </>
  )
}
