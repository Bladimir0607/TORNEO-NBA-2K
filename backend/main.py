"""
Backend - Herramientas del Torneo NBA 2K
==========================================
Este proyecto NO usa base de datos. Todo el trabajo ocurre en memoria,
en el momento de cada peticion. Tiene dos partes, tal como pidio el
profesor:

  1) SERVICIO PROPIO (nuestro): /api/reparto-premio
     Logica propia: reparte un pozo de premio entre los lugares que
     pagan (1ro, 2do, 3ro...) usando porcentajes predefinidos.
     No llama a ningun servicio externo, es matematica pura.

  2) SERVICIO EXTERNO CONSUMIDO: /api/ruta-sedes
     Consume una API publica y gratuita (OSRM - Open Source Routing
     Machine, servidor demo publico, no requiere API key) para
     calcular la distancia y el tiempo estimado en carro entre dos
     sedes del torneo. Es el mismo caso que el ejemplo del profesor
     (Santo Domingo -> Pedernales).

Para correrlo:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8001
"""

from typing import Dict, List

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Herramientas del Torneo NBA 2K")

# CORS: permite que el frontend (puerto 5174) llame a este backend
# (puerto 8001) sin ser bloqueado por el navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# 1) SERVICIO PROPIO: Repartidor de premio
# =========================================================================

# Tabla de porcentajes de reparto segun cuantos lugares pagan.
# Son reglas propias del torneo (no vienen de ninguna API externa).
# Cada lista suma 100.
TABLA_REPARTO: Dict[int, List[float]] = {
    2: [70, 30],
    3: [50, 30, 20],
    4: [45, 25, 18, 12],
    5: [40, 22, 16, 12, 10],
}


class ReparteoInput(BaseModel):
    pozo_total: float = Field(..., gt=0, description="Monto total del premio a repartir")
    lugares_pagados: int = Field(..., ge=2, le=5, description="Cuantos lugares reciben premio (2 a 5)")


class ReparteoLugar(BaseModel):
    posicion: int
    porcentaje: float
    monto: float


class ReparteoOutput(BaseModel):
    pozo_total: float
    lugares_pagados: int
    reparto: List[ReparteoLugar]


@app.post("/api/reparto-premio", response_model=ReparteoOutput)
def reparto_premio(datos: ReparteoInput):
    """Servicio propio: calcula cuanto dinero le toca a cada posicion
    (1er, 2do, 3er lugar, etc.) segun el pozo total y la cantidad de
    lugares que pagan. No hay conexion a ninguna base de datos ni a
    ningun servicio externo; es una regla de negocio propia."""

    porcentajes = TABLA_REPARTO.get(datos.lugares_pagados)
    if porcentajes is None:
        raise HTTPException(
            status_code=400,
            detail="Solo se admite repartir entre 2 y 5 lugares",
        )

    reparto = [
        ReparteoLugar(
            posicion=i + 1,
            porcentaje=pct,
            monto=round(datos.pozo_total * pct / 100, 2),
        )
        for i, pct in enumerate(porcentajes)
    ]

    return ReparteoOutput(
        pozo_total=datos.pozo_total,
        lugares_pagados=datos.lugares_pagados,
        reparto=reparto,
    )


# =========================================================================
# 2) SERVICIO EXTERNO CONSUMIDO: Ruta y tiempo entre sedes (OSRM)
# =========================================================================

# Coordenadas (latitud, longitud) de posibles sedes del torneo.
# Esto es solo una lista fija en el codigo (no es base de datos).
SEDES: Dict[str, Dict[str, float]] = {
    "santo_domingo": {"nombre": "Santo Domingo", "lat": 18.4861, "lon": -69.9312},
    "santiago": {"nombre": "Santiago de los Caballeros", "lat": 19.4517, "lon": -70.6970},
    "punta_cana": {"nombre": "Punta Cana", "lat": 18.5601, "lon": -68.3725},
    "la_romana": {"nombre": "La Romana", "lat": 18.4273, "lon": -68.9728},
    "puerto_plata": {"nombre": "Puerto Plata", "lat": 19.7934, "lon": -70.6884},
    "pedernales": {"nombre": "Pedernales", "lat": 18.0384, "lon": -71.7434},
}

OSRM_URL = "http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"


@app.get("/api/sedes")
def listar_sedes():
    """Devuelve la lista de sedes disponibles, para llenar los
    selectores (dropdowns) del frontend."""
    return [{"clave": clave, "nombre": info["nombre"]} for clave, info in SEDES.items()]


@app.get("/api/ruta-sedes")
async def ruta_entre_sedes(
    origen: str = Query(..., description="Clave de la sede de origen"),
    destino: str = Query(..., description="Clave de la sede de destino"),
):
    """Consume el servicio externo OSRM (Open Source Routing Machine)
    para calcular la distancia y el tiempo estimado en auto entre dos
    sedes del torneo. OSRM es un servicio publico y gratuito, no
    requiere API key. Este es el 'servicio ajeno' que pide el
    profesor (equivalente al ejemplo de Google Geocode)."""

    if origen not in SEDES or destino not in SEDES:
        raise HTTPException(status_code=400, detail="Sede de origen o destino no valida")
    if origen == destino:
        raise HTTPException(status_code=400, detail="Origen y destino no pueden ser la misma sede")

    o = SEDES[origen]
    d = SEDES[destino]
    url = OSRM_URL.format(lon1=o["lon"], lat1=o["lat"], lon2=d["lon"], lat2=d["lat"])

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params={"overview": "false"})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error consultando el servicio de rutas: {e}")

    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=502, detail="El servicio de rutas no devolvio una ruta valida")

    ruta = data["routes"][0]
    distancia_km = round(ruta["distance"] / 1000, 1)
    duracion_min = round(ruta["duration"] / 60, 0)

    return {
        "origen": o["nombre"],
        "destino": d["nombre"],
        "distancia_km": distancia_km,
        "duracion_min": duracion_min,
        "duracion_texto": f"{int(duracion_min // 60)}h {int(duracion_min % 60)}min",
        "fuente": "OSRM (Open Source Routing Machine) - router.project-osrm.org",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
