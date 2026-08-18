"""Bilingüe español / inglés.

Hay dos problemas distintos acá, y se resuelven distinto a propósito:

- **Los textos fijos de la app** (títulos, botones, rótulos de ejes) viven en un
  diccionario local, en views/translations.py. Es gratis, instantáneo y no
  depende de ningún servicio: aunque se caiga internet, el tablero sigue
  funcionando en los dos idiomas.

- **Lo que escriben las campañas** (artículos de facturas, notas, pies de foto)
  no se puede anticipar en un diccionario. Se traduce con deep-translator y se
  guarda en la base al momento de crearlo, en columnas `_en`. Así se traduce
  una sola vez por registro y el donante lo ve al instante, sin esperar a
  ningún servicio externo.

El traductor en vivo queda como respaldo para lo que ya estaba cargado antes de
esta función, y ante cualquier falla devuelve el texto original: para un
tablero de transparencia, mostrar un dato en español es mucho mejor que
mostrar un hueco donde debería estar la evidencia de un gasto.
"""

import time

import streamlit as st

from translator import translate_to_english
from views.translations import GLOSARIO, TEXTOS

IDIOMAS = ("es", "en")
IDIOMA_POR_DEFECTO = "es"
NOMBRES_IDIOMA = {"es": "Español", "en": "English"}

# Re-exportado para que las vistas sigan teniendo un único punto de entrada al
# idioma; la implementación vive en translator.py, que no depende de Streamlit.
__all__ = [
    "IDIOMAS",
    "get_language",
    "localize",
    "localize_field",
    "prime_translations",
    "render_language_selector",
    "sync_language_from_url",
    "t",
    "translate_dynamic",
    "translate_to_english",
]


def get_language() -> str:
    """Idioma activo. Vive en session_state bajo 'app_language', que es la misma
    clave que usa el selector de la barra lateral."""
    idioma = st.session_state.get("app_language", IDIOMA_POR_DEFECTO)
    return idioma if idioma in IDIOMAS else IDIOMA_POR_DEFECTO


def sync_language_from_url():
    """Permite compartir un enlace ya en inglés (`?lang=en`).

    Importa para lo que busca este tablero: quien difunde la campaña afuera
    puede mandar el link directo en el idioma de quien lo va a leer, sin
    pedirle que primero cambie un selector."""
    pedido = st.query_params.get("lang")
    if pedido in IDIOMAS and "app_language" not in st.session_state:
        st.session_state["app_language"] = pedido


def render_language_selector():
    """Selector en la barra lateral, visible desde cualquier pantalla."""
    st.sidebar.selectbox(
        "Idioma / Language",
        IDIOMAS,
        key="app_language",
        format_func=lambda codigo: NOMBRES_IDIOMA[codigo],
    )


def t(clave: str, **kwargs) -> str:
    """Texto fijo en el idioma activo.

    Si falta la traducción al inglés cae al español, y si falta la clave entera
    devuelve la clave: una pantalla con una etiqueta rara se puede arreglar
    mañana, una que revienta deja al donante sin ver las cuentas."""
    entrada = TEXTOS.get(clave)
    if entrada is None:
        return clave
    texto = entrada.get(get_language()) or entrada.get(IDIOMA_POR_DEFECTO) or clave
    return texto.format(**kwargs) if kwargs else texto


# Cuánto puede tardar como mucho el precalentado de una pantalla. Lo que no
# entre en ese presupuesto se muestra en español: para un tablero de
# transparencia, un nombre de artículo sin traducir es un costo menor que una
# página que no carga.
#
# translate_batch() de deep-translator NO sirve acá: por dentro traduce de a uno
# y propaga la primera excepción, así que un solo texto problemático tira abajo
# el lote entero. Medido contra los datos reales de este proyecto, fallaban
# todos los lotes. De a uno, cada falla afecta sólo a ese texto.
PRESUPUESTO_SEGUNDOS = 10.0


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def _traducir_conjunto(textos: tuple[str, ...]) -> dict[str, str]:
    """Traduce los textos que alcancen dentro del presupuesto de tiempo.

    Cacheado por el conjunto exacto: la primera visita en inglés paga la espera
    y las siguientes lo encuentran resuelto."""
    try:
        from deep_translator import GoogleTranslator
    except Exception:
        return {}

    traductor = GoogleTranslator(source="es", target="en")
    limite = time.monotonic() + PRESUPUESTO_SEGUNDOS
    resultado: dict[str, str] = {}

    for original in textos:
        if time.monotonic() >= limite:
            break
        try:
            traducido = traductor.translate(original)
        except Exception:
            continue  # ese texto queda en español; el resto sigue
        if traducido:
            resultado[original] = traducido
    return resultado


def _memoria() -> dict:
    return st.session_state.setdefault("_traducciones_memo", {})


# Tope de textos que una sola pantalla manda a traducir en vivo. Es un respaldo
# para lo que se cargó antes de que existieran las columnas _en, no el camino
# normal: con la base ya traducida (migration_idioma_ingles.sql + el script
# backfill_traducciones.py) esto queda en cero. El tope evita que una campaña
# con miles de renglones deje la página colgada esperando a la red.
MAXIMO_EN_VIVO = 300


def prime_translations(textos) -> None:
    """Traduce de una sola vez, en lote, todo lo que la pantalla va a mostrar.

    Ésta es la ÚNICA función de este módulo que sale a la red al dibujar. El
    resto (localize/localize_field) sólo lee lo que quedó acá, así que armar la
    página nunca se queda esperando una petición: en el peor caso muestra el
    texto en español."""
    if get_language() == "es":
        return

    memoria = _memoria()
    pendientes = sorted(
        {
            texto.strip()
            for texto in textos
            if texto
            and texto.strip()
            and texto.strip() not in memoria
            and texto.strip().casefold() not in GLOSARIO
        }
    )
    if not pendientes:
        return
    memoria.update(_traducir_conjunto(tuple(pendientes[:MAXIMO_EN_VIVO])))


def translate_dynamic(texto: str) -> str:
    """Traducción ya resuelta para este texto: glosario o lo que dejó el lote.

    No sale a la red a propósito. Cuando esta función se llama ya se está
    armando la pantalla, y una petición acá se multiplica por cada renglón de
    cada factura — que fue exactamente lo que hacía que el tablero tardara casi
    un minuto en abrir. Si el texto no está resuelto, se muestra en español."""
    original = (texto or "").strip()
    if not original or get_language() == "es":
        return texto

    del_glosario = GLOSARIO.get(original.casefold())
    if del_glosario:
        return del_glosario

    return _memoria().get(original, texto)


def localize(texto_es: str | None, texto_en: str | None) -> str:
    """Elige la versión guardada que corresponde al idioma activo. Si la inglesa
    todavía no existe (registro cargado antes de esta función), usa lo que
    prime_translations() haya dejado resuelto para ese texto."""
    if get_language() == "es":
        return texto_es or ""
    if texto_en and texto_en.strip():
        return texto_en
    return translate_dynamic(texto_es or "")


def localize_field(fila: dict, campo: str) -> str:
    """Igual que localize() pero tomando ambas versiones de una fila de la base,
    donde la inglesa siempre se llama <campo>_en."""
    if not fila:
        return ""
    return localize(fila.get(campo), fila.get(f"{campo}_en"))
