# Herramientas del Torneo NBA 2K — Servicio propio + Servicio externo

Este proyecto **no usa base de datos**. Tiene dos partes:

1. **Servicio PROPIO** (`POST /api/reparto-premio`): reparte un pozo de
   premio entre los lugares que pagan, usando porcentajes definidos por
   nosotros mismos. Es lógica de negocio pura.

2. **Servicio EXTERNO consumido** (`GET /api/ruta-sedes`): el backend le
   pregunta a **OSRM** (Open Source Routing Machine, servidor demo
   público — https://router.project-osrm.org, **gratis y sin API key**)
   la distancia y el tiempo estimado en carro entre dos sedes del
   torneo. Es el mismo caso del ejemplo del profesor (Santo Domingo →
   Pedernales), pero con un servicio que no requiere registrarte ni
   pedir una llave de API, así no perdemos tiempo con eso.

---

## 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Nota: usamos el puerto **8001** (no el 8000) para poder tener este
proyecto corriendo al mismo tiempo que el del formulario, sin que
choquen.

Prueba en el navegador: http://localhost:8001/api/health → debe decir
`{"status":"ok"}`.

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre: http://localhost:5174 (puerto 5174, distinto al del formulario).

## 3. Cómo probarlo

**Reparto de premio:**
1. Escribe un monto en "Pozo total", ej. `50000`.
2. Elige cuántos lugares pagan (2 a 5).
3. Dale "Calcular reparto" — verás una tabla con el monto exacto de
   cada posición.

**Ruta entre sedes:**
1. Elige una sede de origen y una de destino (ej. Santo Domingo →
   Pedernales, el mismo ejemplo del profesor).
2. Dale "Calcular ruta" — el backend consulta OSRM y te devuelve la
   distancia en km y el tiempo estimado en carro.

## En Resumen:

- El servicio **propio** (`/api/reparto-premio`) no depende de internet
  ni de terceros: toda la lógica (porcentajes por posición) está en
  `backend/main.py`, en el diccionario `TABLA_REPARTO`.
- El servicio **externo** (`/api/ruta-sedes`) sí depende de internet:
  el backend hace una petición HTTP a `router.project-osrm.org` usando
  la librería `httpx`, y traduce la respuesta a un formato más simple
  para el frontend.
- Las "sedes" (Santo Domingo, Pedernales, etc.) son solo una lista fija
  en el código (diccionario `SEDES`), **no es una base de datos** — es
  solo para tener coordenadas de ejemplo que enviarle a OSRM.
