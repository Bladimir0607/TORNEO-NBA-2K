"""
Suite de automatizacion con Playwright (Python + pytest)
Proyecto: Herramientas del Torneo NBA 2K (servicio propio + externo)

Cubre:
  - Servicio propio: Reparto de premio (POST /api/reparto-premio)
  - Servicio externo consumido: Ruta entre sedes via OSRM (GET /api/ruta-sedes)
  - 10 casos de prueba, cada uno usando una forma distinta de "wait".

Antes de correr:
  1. Backend corriendo en http://localhost:8001  (uvicorn main:app --reload --port 8001)
  2. Frontend corriendo en http://localhost:5174 (npm run dev)

Ejecutar:
  pytest test_herramientas.py --browser chromium --headed
"""

import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:5174"


# ---------------------------------------------------------------
# Caso 1: carga de la pagina
# Wait usado: page.wait_for_load_state() -> espera explicita de
# ciclo de vida de la pagina.
# ---------------------------------------------------------------
def test_01_carga_pagina(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("load")
    expect(page.locator(".scoreboard__title")).to_have_text("TORNEO NBA 2K")


# ---------------------------------------------------------------
# Caso 2: campos del reparto de premio visibles
# Wait usado: page.wait_for_selector() -> espera explicita a que
# un selector aparezca en el DOM con un estado dado.
# ---------------------------------------------------------------
def test_02_campos_reparto_visibles(page: Page):
    page.goto(BASE_URL)
    page.wait_for_selector("#pozo", state="visible")
    page.wait_for_selector("#lugares", state="visible")
    assert page.is_visible("#pozo")
    assert page.is_visible("#lugares")


# ---------------------------------------------------------------
# Caso 3: llenar el pozo (control: number input)
# Wait usado: auto-wait incorporado de Playwright en locator.fill()
# (espera implicitamente a que el elemento este listo).
# ---------------------------------------------------------------
def test_03_llenar_pozo(page: Page):
    page.goto(BASE_URL)
    page.fill("#pozo", "50000")
    assert page.input_value("#pozo") == "50000"


# ---------------------------------------------------------------
# Caso 4: seleccionar cantidad de lugares (control: select)
# Wait usado: locator.wait_for(state="attached") -> espera a que
# el elemento este presente en el DOM.
# ---------------------------------------------------------------
def test_04_seleccionar_lugares(page: Page):
    page.goto(BASE_URL)
    select_lugares = page.locator("#lugares")
    select_lugares.wait_for(state="attached")
    select_lugares.select_option("4")
    assert page.input_value("#lugares") == "4"


# ---------------------------------------------------------------
# Caso 5: calcular reparto de premio (servicio PROPIO)
# Wait usado: expect().to_have_count() -> asercion con auto-espera
# que reintenta hasta que la tabla tenga la cantidad de filas
# esperada (una fila por lugar premiado).
# ---------------------------------------------------------------
def test_05_calcular_reparto_tabla(page: Page):
    page.goto(BASE_URL)
    page.fill("#pozo", "50000")
    page.locator("#lugares").select_option("3")
    page.get_by_role("button", name="Calcular reparto").click()
    filas = page.locator(".tabla-resultado tbody tr")
    expect(filas).to_have_count(3)


# ---------------------------------------------------------------
# Caso 6: verificar montos calculados por el servicio propio
# Wait usado: page.wait_for_function() -> espera explicita a que
# una condicion de JavaScript en la pagina se cumpla (a que la
# primera celda de monto ya no este vacia).
# ---------------------------------------------------------------
def test_06_montos_reparto_correctos(page: Page):
    page.goto(BASE_URL)
    page.fill("#pozo", "10000")
    page.locator("#lugares").select_option("2")
    page.get_by_role("button", name="Calcular reparto").click()
    page.wait_for_function(
        "document.querySelector('.tabla-resultado tbody tr td:nth-child(3)') !== null"
    )
    primera_fila = page.locator(".tabla-resultado tbody tr").first
    # con 2 lugares el reparto es 70/30, entonces el primer lugar
    # debe llevarse RD$ 7,000.00 de un pozo de 10,000
    expect(primera_fila).to_contain_text("7,000.00")


# ---------------------------------------------------------------
# Caso 7: sedes cargadas desde el backend (control: select)
# Wait usado: expect().to_have_count() -> espera a que el select de
# sedes tenga las 6 opciones que devuelve el endpoint /api/sedes.
# ---------------------------------------------------------------
def test_07_sedes_cargadas(page: Page):
    page.goto(BASE_URL)
    opciones = page.locator("#origen option")
    expect(opciones).to_have_count(6)


# ---------------------------------------------------------------
# Caso 8: calcular ruta entre sedes (SERVICIO EXTERNO consumido)
# Wait usado: page.wait_for_response() -> espera explicita a la
# respuesta HTTP real del backend, que a su vez consulta OSRM.
# ---------------------------------------------------------------
def test_08_calcular_ruta_externa(page: Page):
    page.goto(BASE_URL)
    page.locator("#origen").select_option("santo_domingo")
    page.locator("#destino").select_option("pedernales")

    with page.expect_response(
        lambda r: "/api/ruta-sedes" in r.url and r.status == 200
    ) as resp_info:
        page.get_by_role("button", name="Calcular ruta").click()

    response = resp_info.value
    datos = response.json()
    assert datos["origen"] == "Santo Domingo"
    assert datos["destino"] == "Pedernales"
    assert datos["distancia_km"] > 0
    expect(page.locator(".resultado-ruta")).to_be_visible()


# ---------------------------------------------------------------
# Caso 9: error al elegir la misma sede de origen y destino
# Wait usado: page.wait_for_selector() esperando a que aparezca el
# mensaje de error devuelto por el backend.
# ---------------------------------------------------------------
def test_09_misma_sede_error(page: Page):
    page.goto(BASE_URL)
    page.locator("#origen").select_option("santo_domingo")
    page.locator("#destino").select_option("santo_domingo")
    page.get_by_role("button", name="Calcular ruta").click()
    page.wait_for_selector(".alerta--error", state="visible")
    expect(page.locator(".alerta--error")).to_contain_text("misma sede")


# ---------------------------------------------------------------
# Caso 10: verificacion de la URL del frontend
# Wait usado: page.wait_for_url() -> espera explicita a que la URL
# de la pagina cumpla un patron.
# ---------------------------------------------------------------
def test_10_url_pagina(page: Page):
    page.goto(BASE_URL)
    page.wait_for_url(re.compile(r"localhost:5174"))
    assert "localhost:5174" in page.url