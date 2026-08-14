"""
Design tokens for the app. Light-surface palette built around trust and help.

Palette roles (chosen by the owner, verified here — not eyeballed):
  Azul Confianza  #1565C0 — seguridad, trazabilidad. Dinero como dinero.
  Verde Esmeralda #2E7D32 — crecimiento, ayuda, impacto. Dinero ya convertido
                            en artículos entregados; también metas cumplidas.
  Naranja Suave   #F57F17 — estados intermedios / atención moderada.
  Rojo Vinotinto  #C62828 — errores y alertas críticas, nada más.

Measured with the data-viz checks (Machado-Oliveira-Fernandes CVD simulation,
OKLab ΔE, WCAG) against the white card surface:
  * blue vs green (the two chart series): CVD ΔE 23.6, normal-vision 24.4 —
    far above the 8 / 15 floors. The semantic pairing is also the safest pairing.
  * full 4-slot set: all checks pass; #F57F17 sits at 2.65:1 contrast, so any
    chart using it MUST carry visible direct labels (the documented relief) —
    every chart here already does.
  * text ramp: INK 13.2:1, INK_SOFT 7.2:1, MUTED 5.4:1 on white — all clear the
    4.5:1 bar for normal-size text, so captions and axis labels stay readable.

Colour-assignment rule this app follows: colour tracks MEANING, held constant
across every view — blue is always money, green is always help delivered. A
reader who learns it once is never re-taught.
"""

from datetime import datetime

# --- Surfaces & ink -------------------------------------------------------
PAGE = "#F5F5F5"          # page plane
SURFACE = "#FFFFFF"       # cards & chart surface
SURFACE_SUNKEN = "#ECEFF1"  # subtle inset panels
INK = "#263238"           # primary text (13.2:1 on white)
INK_SOFT = "#455A64"      # secondary text (7.2:1)
MUTED = "#546E7A"         # captions, axis labels (5.4:1)
GRID = "#ECEFF1"          # hairline gridline
AXIS = "#CFD8DC"          # baseline / axis rule
BORDER = "rgba(38,50,56,0.12)"

# --- Categorical slots ----------------------------------------------------
SERIES_MONEY = "#1565C0"   # Azul Confianza — recibido, gasto, trazabilidad
SERIES_IMPACT = "#2E7D32"  # Verde Esmeralda — ejecutado, artículos entregados

# Only real data series belong here. Orange and red are STATUS colours (aviso /
# error), never series identity: darkened enough to be legible as text they sit
# ~1.3 deltaE from each other under deuteranopia, so as two adjacent series they
# would be indistinguishable. As status they never appear as bare swatches —
# always with an icon and a word.
CATEGORICAL_PALETTE = [SERIES_MONEY, SERIES_IMPACT]

# Banner "cómo aportar": verde muy claro del mismo tono de la marca. El texto
# principal mide 11.9:1 sobre este fondo, así que resalta sin costar lectura.
BANNER_BG = "#E8F5E9"
BANNER_BORDER = SERIES_IMPACT

# --- Status (reserved meaning; always paired with an icon or label) --------
STATUS_WARNING = "#F57F17"
STATUS_CRITICAL = "#C62828"

# Colombian flag stripe, kept on-palette.
FLAG_YELLOW = "#F57F17"
FLAG_BLUE = SERIES_MONEY
FLAG_RED = STATUS_CRITICAL

# Categorías base. "Otros" se mantiene siempre al final de la lista que ve el
# usuario; las categorías propias que él cree se insertan entre medias
# (ver views/admin_panel.category_options).
CATEGORY_OPTIONS = [
    "Alimentos", "Equipos", "Herramientas", "Hogar", "Insumos Médicos", "Logística", "Otros",
]


def format_currency(value: float) -> str:
    return "$" + f"{value:,.0f}".replace(",", ".")


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def format_date(iso_date: str) -> str:
    return datetime.fromisoformat(iso_date).strftime("%d/%m/%Y")


# Plotly rotula los meses en inglés salvo que se cargue un bundle de locale.
# Como las marcas del eje se generan a mano, basta con esta tabla.
MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def format_day_short(value) -> str:
    """'11 ago' — para las marcas del eje de las gráficas diarias."""
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
        # Colombian number format: decimal comma, thousands period — matches
        # format_currency() so axis ticks and card values agree.
        separators=",.",
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


# NOTE: there is deliberately no CSS injection here. Every colour, border and
# radius in this app is set natively in .streamlit/config.toml — that survives
# Streamlit upgrades, whereas selectors into Streamlit's generated class names
# do not. Cards are st.container(border=True) / st.metric(border=True), which
# pick up borderColor and baseRadius from the config.
