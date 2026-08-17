import streamlit as st

import database as db
from views.data import load_global_totals, show_connection_error
from views.public_dashboard import flag_stripe, render_top_nav
from views.theme import format_currency, format_number


def render_global_totals(campaigns: list[dict]):
    """Lo que suman todas las campañas juntas. Va arriba de la lista para que
    quien llega vea primero el tamaño del esfuerzo colectivo y no una lista
    suelta de nombres."""
    try:
        totales = load_global_totals(tuple(c["id"] for c in campaigns))
    except Exception:
        return  # sin totales la portada sigue sirviendo; no vale tumbarla por esto

    st.markdown("#### Entre todas las campañas")
    fila = st.columns(5)
    tarjetas = [
        (":material/campaign:", "Campañas activas", format_number(len(campaigns))),
        (":material/volunteer_activism:", "Recibido", format_currency(totales["donado"])),
        (":material/shopping_cart:", "Ya ejecutado", format_currency(totales["ejecutado"])),
        (":material/account_balance_wallet:", "Por ejecutar", format_currency(totales["pendiente"])),
        (":material/inventory_2:", "Artículos entregados", format_number(totales["articulos"])),
    ]
    for columna, (icono, etiqueta, valor) in zip(fila, tarjetas):
        with columna:
            st.metric(label=etiqueta, value=valor, icon=icono, border=True)

    if totales["aportes"]:
        st.caption(
            f"{format_number(totales['aportes'])} aportes de personas y organizaciones, "
            "con cada peso respaldado por su factura."
        )


def render():
    # La portada es el punto de partida de las tres puertas: el tablero público
    # de cada campaña, el panel de quien la gestiona y el del operador del sitio.
    render_top_nav(include_operator=True)

    st.title("🤝 Transparencia de Donaciones")
    st.caption(
        "Personas que recibieron donaciones y muestran, peso por peso, en qué las convirtieron. "
        "Elegí una campaña para ver su rendición de cuentas."
    )
    flag_stripe()

    try:
        campaigns = db.get_campaigns_public()
    except Exception as error:
        show_connection_error(error)
        return

    campaign_page = st.session_state.get("_campaign_page")

    if not campaigns:
        st.info("Todavía no hay campañas publicadas.")
        return

    render_global_totals(campaigns)

    st.divider()
    st.markdown("#### Campañas")

    columns = st.columns(3)
    for index, campaign in enumerate(campaigns):
        with columns[index % 3]:
            with st.container(border=True):
                st.markdown(f"##### {campaign['name']}")
                st.caption(
                    campaign.get("description") or "Rendición de cuentas de las donaciones recibidas."
                )
                if campaign_page is not None:
                    st.page_link(
                        campaign_page,
                        label="Ver rendición de cuentas",
                        icon=":material/arrow_forward:",
                        query_params={"c": campaign["slug"]},
                        width="stretch",
                    )
