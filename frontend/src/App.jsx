// App.jsx
// ============================================================
// Herramientas del Torneo NBA 2K - sin base de datos.
//
// Dos secciones, cada una habla con un endpoint distinto del backend:
//
//  1) Reparto de premio -> POST /api/reparto-premio
//     SERVICIO PROPIO: logica nuestra, no depende de nada externo.
//
//  2) Ruta entre sedes -> GET /api/ruta-sedes
//     SERVICIO EXTERNO CONSUMIDO: el backend llama a OSRM
//     (Open Source Routing Machine) para calcular distancia y tiempo.
// ============================================================

import { useEffect, useState } from 'react'

const API_URL = 'http://localhost:8001'

export default function App() {
  return (
    <div className="court">
      <header className="scoreboard">
        <span className="scoreboard__badge">HERRAMIENTAS</span>
        <h1 className="scoreboard__title">TORNEO NBA 2K</h1>
        <p className="scoreboard__subtitle">Reparto de premios y logística entre sedes</p>
      </header>

      <RepartoPremio />
      <RutaSedes />
    </div>
  )
}

// ------------------------------------------------------------
// SECCION 1: Reparto de premio (servicio propio)
// ------------------------------------------------------------
function RepartoPremio() {
  const [pozo, setPozo] = useState('')
  const [lugares, setLugares] = useState(3)
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)

  async function calcular(e) {
    e.preventDefault()
    setError(null)
    setResultado(null)
    setCargando(true)
    try {
      const res = await fetch(`${API_URL}/api/reparto-premio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pozo_total: Number(pozo),
          lugares_pagados: Number(lugares),
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Error al calcular el reparto')
      }
      setResultado(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  return (
    <section className="card">
      <h2 className="card__title">🏆 Reparto de premio</h2>
      <p className="card__desc">
        Servicio propio: calcula cuánto le toca a cada posición según el pozo total.
      </p>

      <form className="form-inline" onSubmit={calcular}>
        <div className="field">
          <label htmlFor="pozo">Pozo total (RD$)</label>
          <input
            id="pozo"
            type="number"
            min="1"
            step="0.01"
            placeholder="Ej. 50000"
            value={pozo}
            onChange={(e) => setPozo(e.target.value)}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="lugares">Lugares premiados</label>
          <select id="lugares" value={lugares} onChange={(e) => setLugares(e.target.value)}>
            <option value={2}>2 lugares</option>
            <option value={3}>3 lugares</option>
            <option value={4}>4 lugares</option>
            <option value={5}>5 lugares</option>
          </select>
        </div>

        <button type="submit" className="btn" disabled={cargando}>
          {cargando ? 'Calculando...' : 'Calcular reparto'}
        </button>
      </form>

      {error && <p className="alerta alerta--error">{error}</p>}

      {resultado && (
        <table className="tabla-resultado">
          <thead>
            <tr>
              <th>Posición</th>
              <th>Porcentaje</th>
              <th>Monto</th>
            </tr>
          </thead>
          <tbody>
            {resultado.reparto.map((r) => (
              <tr key={r.posicion}>
                <td>{r.posicion}°</td>
                <td>{r.porcentaje}%</td>
                <td>RD$ {r.monto.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

// ------------------------------------------------------------
// SECCION 2: Ruta entre sedes (consume servicio externo OSRM)
// ------------------------------------------------------------
function RutaSedes() {
  const [sedes, setSedes] = useState([])
  const [origen, setOrigen] = useState('')
  const [destino, setDestino] = useState('')
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)

  // Al montar el componente, pide la lista de sedes al backend.
  useEffect(() => {
    fetch(`${API_URL}/api/sedes`)
      .then((r) => r.json())
      .then((data) => {
        setSedes(data)
        if (data.length >= 2) {
          setOrigen(data[0].clave)
          setDestino(data[data.length - 1].clave)
        }
      })
      .catch(() => setError('No se pudo cargar la lista de sedes'))
  }, [])

  async function calcularRuta(e) {
    e.preventDefault()
    setError(null)
    setResultado(null)
    setCargando(true)
    try {
      const params = new URLSearchParams({ origen, destino })
      const res = await fetch(`${API_URL}/api/ruta-sedes?${params}`)
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Error al calcular la ruta')
      }
      setResultado(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  return (
    <section className="card">
      <h2 className="card__title">🗺️ Ruta entre sedes</h2>
      <p className="card__desc">
        Consume un servicio externo (OSRM) para calcular distancia y tiempo estimado en auto.
      </p>

      <form className="form-inline" onSubmit={calcularRuta}>
        <div className="field">
          <label htmlFor="origen">Sede de origen</label>
          <select id="origen" value={origen} onChange={(e) => setOrigen(e.target.value)}>
            {sedes.map((s) => (
              <option key={s.clave} value={s.clave}>{s.nombre}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="destino">Sede de destino</label>
          <select id="destino" value={destino} onChange={(e) => setDestino(e.target.value)}>
            {sedes.map((s) => (
              <option key={s.clave} value={s.clave}>{s.nombre}</option>
            ))}
          </select>
        </div>

        <button type="submit" className="btn" disabled={cargando || !sedes.length}>
          {cargando ? 'Consultando...' : 'Calcular ruta'}
        </button>
      </form>

      {error && <p className="alerta alerta--error">{error}</p>}

      {resultado && (
        <div className="resultado-ruta">
          <p>
            <strong>{resultado.origen}</strong> → <strong>{resultado.destino}</strong>
          </p>
          <p className="resultado-ruta__dato">
            📏 Distancia: <strong>{resultado.distancia_km} km</strong>
          </p>
          <p className="resultado-ruta__dato">
            ⏱️ Tiempo estimado: <strong>{resultado.duracion_texto}</strong>
          </p>
          <p className="resultado-ruta__fuente">Fuente: {resultado.fuente}</p>
        </div>
      )}
    </section>
  )
}
