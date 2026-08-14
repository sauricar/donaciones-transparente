import streamlit as st

from views import admin_panel, campaign_selector, public_dashboard, super_admin

st.set_page_config(page_title="Transparencia de Donaciones", page_icon="🤝", layout="wide")

selector_page = st.Page(campaign_selector.render, title="Inicio", url_path="inicio", default=True)
campaign_page = st.Page(public_dashboard.render, title="Campaña", url_path="campana")
admin_page = st.Page(admin_panel.render, title="Panel de Gestión", url_path="panel-de-gestion")
operator_page = st.Page(super_admin.render, title="Administración", url_path="admin-campanas")

st.session_state["_selector_page"] = selector_page
st.session_state["_campaign_page"] = campaign_page
st.session_state["_admin_page"] = admin_page
st.session_state["_operator_page"] = operator_page

navigation = st.navigation([selector_page, campaign_page, admin_page, operator_page], position="hidden")
navigation.run()
