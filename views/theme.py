"""
Design tokens for the app. Paleta Trada (Claude Design, proyecto
caa604eb-5378-4ed9-9dcc-00e579377b8e), adaptada de una app móvil React a esta
app Streamlit — ver .streamlit/config.toml para el resto de los tokens
nativos (color, tipografía, espaciado, radios). Este archivo cubre lo que
Streamlit no expone por config: colores de gráfica que necesitan una variante
de texto aparte, y el CSS de tarjeta que Trada exige y Streamlit no da nativo.

Roles de color (fuente: tokens/colors.css del design system):
  Ember      #F0562D — dinero recibido. NUNCA como texto (blanco encima da
                        3.46:1, bajo el 4.5:1 que exige AA). Sólo fill.
  Ember Deep #B83410 — dinero como texto/glifo, acción primaria, errores.
                        Es la variante de Ember que SÍ pasa AA como texto.
  Viridine   #C6DEAD — ejecutado/entregado. Fill únicamente, igual que Ember:
                        pálido, ilegible como texto (1.45:1 con blanco encima).
  #2F5220    — "ejecutado" como texto/glifo (el propio Trada ya define esta
                variante oscura de Viridine para texto, no se inventó acá).
  Umbra      #221E1F — texto en general, y el único texto que SÍ es legible
                        tanto sobre Ember (4.77:1) como sobre Viridine (11.4:1)
                        — por eso las gráficas de barra usan texto Umbra
                        adentro de la barra en los dos casos, nunca blanco.

Validado con el mismo método que ya usaba este archivo antes de Trada
(simulación CVD Machado-Oliveira-Fernandes + distancia perceptual OKLab,
contraste WCAG): Ember vs. Viridine da ΔE 32.2 bajo protanopia / 21.5 bajo
deuteranopia — igual o mejor que el par azul/verde anterior (23.6), muy por
encima del piso de 15 que ya exigía este proyecto.

Colour-assignment rule (sin cambios): el color sigue el SIGNIFICADO, constante
en toda la app — Ember es siempre dinero, Viridine es siempre ayuda entregada.
Quien lo aprende una vez no lo vuelve a aprender.
"""

from datetime import datetime

from views.i18n import get_language

# --- Surfaces & ink --------------------------------------------------------
# Stardust/White/Umbra tal cual el design system — ver tokens/colors.css.
PAGE = "#EAEADA"            # plano de página (= backgroundColor de config.toml)
SURFACE = "#FFFFFF"         # tarjetas y superficie de gráfica
SURFACE_SUNKEN = "#F4F4EC"  # paneles internos sutiles (--color-paper de Trada)
INK = "#221E1F"             # texto primario (13.6:1 sobre blanco)
INK_SOFT = "rgba(34,30,31,.68)"   # texto secundario (5.7:1 sobre blanco)
MUTED = "rgba(34,30,31,.68)"      # captions, ejes (5.7 / 5.2:1)
GRID = "rgba(34,30,31,.10)"       # línea de grilla, decorativa
AXIS = "rgba(34,30,31,.30)"       # línea base del eje
BORDER = "rgba(34,30,31,.14)"     # borde decorativo (tooltips) — no es un control

# --- Categorical slots ------------------------------------------------------
SERIES_MONEY = "#F0562D"   # Ember — recibido. Fill únicamente (ver cabecera).
SERIES_IMPACT = "#C6DEAD"  # Viridine — ejecutado, artículos entregados.

# Sólo series de datos reales. Ver cabecera para el porqué del par.
CATEGORICAL_PALETTE = [SERIES_MONEY, SERIES_IMPACT]

# Banner "cómo aportar": tinte muy claro del mismo tono de Viridine — la marca
# ya la usa para "verificado", que es justo lo que este banner comunica.
BANNER_BG = "#EEF5E6"
BANNER_BORDER = "#8FB56B"  # Viridine oscurecido: no es un control, es un acento
                            # decorativo (mismo criterio que las líneas internas de
                            # tabla) — 2.1:1 sobre el fondo del banner, suficiente
                            # para leerse como trazo sin competir con el contenido.

# Texto del botón activo en la navegación por secciones. Medido en el
# navegador: Streamlit tiñe el fondo del botón activo con Ember Deep al 10%
# de opacidad sobre Stardust, y Ember Deep tal cual como texto ahí da 4.23:1
# — por debajo de 4.5:1. Un paso más oscuro de la misma familia (30% Umbra
# mezclado) lo lleva a 6.00:1 sin inventar un color nuevo — mismo ajuste que
# ya le había hecho este archivo al verde de la paleta anterior.
NAV_ACTIVE_INK = "#8B2D14"

# --- Status (reserved meaning; always paired with an icon or label) --------
# Trada reusa sus mismos 4 colores para los 4 estados de trazabilidad en vez
# de inventar uno nuevo por estado (pendiente=Umbra tenue, en tránsito=Ember,
# entregado=Viridine, atención=Ember Deep). Este código sigue la misma lógica:
STATUS_WARNING = "#F0562D"   # Ember — atención moderada / en curso
STATUS_CRITICAL = "#B83410"  # Ember Deep — errores y alertas críticas

# Categorías base. "Otros" se mantiene siempre al final de la lista que ve el
# usuario; las categorías propias que él cree se insertan entre medias
# (ver views/admin_panel.category_options).
CATEGORY_OPTIONS = [
    "Alimentos", "Equipos", "Herramientas", "Hogar", "Insumos Médicos", "Logística", "Otros",
]


LOGO_PATH = "assets/logo.svg"


def render_brand_mark(size_px: int = 48, wordmark_rem: float = 2.4):
    """Isotipo + wordmark 'TRADA', como en guidelines/brand-logo.html del
    design system — pero con 'DA' en Ember Deep, no en Ember crudo como
    muestra la ficha original: medido, Ember como texto grande da 2.84:1
    sobre Stardust (el fondo real de la portada), por debajo del piso de
    3:1 que exige AA incluso para texto grande — sólo pasa sobre blanco
    puro (3.46:1). Ember Deep pasa en cualquier superficie de esta app.

    El isotipo va por st.image(), no inline dentro de st.html(): st.html()
    sanitiza con DOMPurify y el elemento <svg> desaparece por completo del
    HTML final (probado en el navegador, no es una suposición) — st.image()
    es un camino totalmente distinto que si soporta archivos .svg locales."""
    import streamlit as st

    icon_col, word_col = st.columns([1, 5], gap="small", vertical_alignment="center")
    with icon_col:
        st.image(LOGO_PATH, width=size_px)
    with word_col:
        st.html(
            f"""
            <span style="font-family:'Manrope',sans-serif;font-weight:800;
                         font-size:{wordmark_rem}rem;letter-spacing:-.02em;line-height:1;">
              <span style="color:{INK};">TRA</span><span style="color:{STATUS_CRITICAL};">DA</span>
            </span>
            """
        )


def format_currency(value: float) -> str:
    """En español, formato colombiano: '$21.923.796'.

    En inglés se antepone COP y se usan comas de millar: 'COP 21,923,796'. La
    moneda explícita no es un adorno — un donante en Estados Unidos que lee
    '$21.923.796' puede entender dólares y creer que el monto es mil veces
    mayor de lo que es. En un tablero de transparencia esa confusión es
    exactamente lo que hay que evitar."""
    if get_language() == "en":
        return "COP " + f"{value:,.0f}"
    return "$" + f"{value:,.0f}".replace(",", ".")


def format_number(value: float) -> str:
    if get_language() == "en":
        return f"{value:,.0f}"
    return f"{value:,.0f}".replace(",", ".")


def format_decimal(value: float, decimals: int = 1) -> str:
    """Para porcentajes: coma decimal en español, punto en inglés."""
    texto = f"{value:,.{decimals}f}"
    if get_language() == "en":
        return texto
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def format_date(iso_date: str) -> str:
    """En inglés se escribe el mes con letras ('Aug 10, 2026') en vez de
    08/10/2026: quien lee en inglés no comparte una única convención de orden
    día/mes, y una fecha ambigua en una factura resta credibilidad."""
    fecha = datetime.fromisoformat(iso_date)
    if get_language() == "en":
        return f"{MONTHS_EN[fecha.month - 1]} {fecha.day}, {fecha.year}"
    return fecha.strftime("%d/%m/%Y")


# Plotly rotula los meses en inglés salvo que se cargue un bundle de locale.
# Como las marcas del eje se generan a mano, basta con estas tablas.
MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_day_short(value) -> str:
    """'11 ago' / 'Aug 11' — para las marcas del eje de las gráficas diarias."""
    if get_language() == "en":
        return f"{MONTHS_EN[value.month - 1]} {value.day}"
    return f"{value.day} {MONTHS_ES[value.month - 1]}"


def format_signed_currency(value: float) -> str:
    """'-$430.000' y no '$-430.000': el signo va antes del símbolo."""
    sign = "-" if value < 0 else "+"
    return f"{sign}{format_currency(abs(value))}"


def apply_chart_theme(figure, height: int = None, show_legend: bool = False):
    """Shared chart chrome: transparent surface so the card shows through,
    recessive solid hairline grid (never dashed), text in ink tokens."""
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # Los separadores siguen al idioma, igual que format_currency(), para
        # que las marcas de los ejes y los números de las tarjetas no se
        # contradigan dentro de la misma pantalla.
        # (decimal, millar): '.,' en inglés — 21,923,796.5 — y ',.' en español.
        separators=".," if get_language() == "en" else ",.",
        font=dict(color=INK_SOFT, family="system-ui, -apple-system, Segoe UI, sans-serif", size=13),
        margin=dict(t=10, b=10, l=10, r=10),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=BORDER, font=dict(color=INK)),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK_SOFT)),
        xaxis=dict(gridcolor=GRID, griddash="solid", zerolinecolor=AXIS, linecolor=AXIS, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=GRID, griddash="solid", zerolinecolor=AXIS, linecolor=AXIS, tickfont=dict(color=MUTED)),
    )
    if height:
        figure.update_layout(height=height)
    return figure


# La sombra es "la regla que define todo el sistema" en Trada: tarjeta blanca
# elevada sobre el fondo Stardust con sombra suave — nunca un color más
# oscuro para simular profundidad. Streamlit no tiene token de sombra en
# config.toml, así que esto extiende la MISMA técnica ya usada en
# render_top_nav/render_donation_banner (public_dashboard.py): un solo
# bloque de CSS, inyectado una vez, apuntando a un atributo estable de
# Streamlit — nunca a una clase autogenerada sin probar antes en el navegador.
CARD_RADIUS = "14px"
CARD_SHADOW = "0 8px 24px rgba(34,30,31,.1)"  # valor exacto de Trada (brand-elevation)


# st.metric(border=True) sí tiene un testid público y estable (stMetric),
# pero st.container(border=True) NO: el borde real llega por una clase
# "st-emotion-cache-XXXXXX" que Streamlit regenera cada build — probado en el
# navegador, no asumido (stVerticalBlockBorderWrapper, el selector que se
# esperaría, ni existe en esta versión). Por eso cada st.container(border=True)
# de la app lleva su propio `key=` explícito (igual que ya hacía
# donation_banner) y esta lista los recoge a todos en un solo lugar: agregar
# una tarjeta nueva es agregar su key acá, no adivinar una clase.
_CARD_KEYS_EXACTOS = (
    # donation_banner NO va acá: administra su propio fondo/borde en
    # render_donation_banner (public_dashboard.py) — un blanco forzado acá
    # le pisaría el verde pálido que lo distingue como "verificado/aportar".
    # Sólo toma prestada la sombra, directo en su propio bloque de CSS.
    "missing_evidence_card",
    "bulk_evidence_card",
    "campaign_login_card",
    "operator_login_card",
)
# Los que se generan en un loop (una tarjeta por campaña/foto) no tienen un
# nombre fijo: se matchean por prefijo con un selector de atributo
# ([class*=...]), que sí admite sub-cadena aunque `.clase` no admita comodines.
_CARD_KEY_PREFIJOS = (
    "campaign_card_",
    "evidence_upload_card_",
)


def inject_card_shadow():
    """Sombra + radio de tarjeta para todo contenedor con borde
    (st.container(border=True, key=...), st.metric(border=True)). Se llama UNA
    vez desde app.py, no por vista — evita inyectar el mismo <style> en cada
    rerun de cada pantalla."""
    import streamlit as st

    exactos = ", ".join(f'.st-key-{k}' for k in _CARD_KEYS_EXACTOS)
    prefijos = ", ".join(f'[class*="st-key-{p}"]' for p in _CARD_KEY_PREFIJOS)
    st.html(
        f"""
        <style>
          [data-testid="stMetric"], {exactos}, {prefijos} {{
              /* Streamlit no rellena un contenedor con borde con
                 secondaryBackgroundColor por su cuenta — sólo pone el borde.
                 Sin este fondo, la tarjeta blanca de Trada se confunde con el
                 Stardust de la página (comprobado en el navegador: quedaba
                 transparente). */
              background: {SURFACE} !important;
              border-radius: {CARD_RADIUS} !important;
              box-shadow: {CARD_SHADOW};
          }}
        </style>
        """
    )
