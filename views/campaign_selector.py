import streamlit as st

import database as db
from views.data import show_connection_error
from views.public_dashboard import flag_stripe


def render():
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
