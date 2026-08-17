import streamlit as st

import database as db
from views.data import load_global_totals, show_connection_error
from views.i18n import localize_field, prime_translations, t
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

    st.markdown(t("portada.entre_todas"))
    fila = st.columns(5)
    tarjetas = [
        (":material/campaign:", t("portada.campanas_activas"), format_number(len(campaigns))),
        (":material/volunteer_activism:", t("portada.recibido"), format_currency(totales["donado"])),
        (":material/shopping_cart:", t("portada.ejecutado"), format_currency(totales["ejecutado"])),
        (":material/account_balance_wallet:", t("portada.por_ejecutar"), format_currency(totales["pendiente"])),
        (":material/inventory_2:", t("portada.articulos_entregados"), format_number(totales["articulos"])),
    ]
    for columna, (icono, etiqueta, valor) in zip(fila, tarjetas):
        with columna:
            st.metric(label=etiqueta, value=valor, icon=icono, border=True)

    if totales["aportes"]:
        st.caption(t("portada.resumen_aportes", aportes=format_number(totales["aportes"])))
    st.caption(t("comun.moneda_nota"))


def render():
    # La portada es el punto de partida de las tres puertas: el tablero público
    # de cada campaña, el panel de quien la gestiona y el del operador del sitio.
    render_top_nav(include_operator=True)

    st.title(t("portada.titulo"))
    st.caption(t("portada.subtitulo"))
    flag_stripe()

    try:
        campaigns = db.get_campaigns_public()
    except Exception as error:
        show_connection_error(error)
        return

    campaign_page = st.session_state.get("_campaign_page")

    if not campaigns:
        st.info(t("portada.sin_campanas"))
        return

    prime_translations(
        c.get("description") for c in campaigns if not (c.get("description_en") or "").strip()
    )

    render_global_totals(campaigns)

    st.divider()
    st.markdown(t("portada.campanas"))

    columns = st.columns(3)
    for index, campaign in enumerate(campaigns):
        with columns[index % 3]:
            with st.container(border=True):
                st.markdown(f"##### {campaign['name']}")
                st.caption(
                    localize_field(campaign, "description") or t("portada.descripcion_defecto")
                )
                if campaign_page is not None:
                    st.page_link(
                        campaign_page,
                        label=t("portada.ver_rendicion"),
                        icon=":material/arrow_forward:",
                        query_params={"c": campaign["slug"]},
                        width="stretch",
                    )
