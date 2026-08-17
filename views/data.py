import streamlit as st

import database as db
from views.i18n import t


def show_connection_error(error: Exception):
    """A public visitor must never see a raw traceback. Supabase returning 503
    (project paused or a transient outage) is the common case."""
    st.error(t("error.conexion"))
    with st.expander(t("error.detalle_tecnico")):
        st.code(str(error))


@st.cache_data(ttl=60)
def load_data(campaign_id: str):
    donations = db.get_donations(campaign_id, limit=1000)
    invoices = db.get_invoices(campaign_id, limit=1000)
    items = []
    for invoice in invoices:
        for item in db.get_invoice_items(invoice["id"]):
            item["invoice_date"] = invoice["invoice_date"]
            items.append(item)
    photos = db.get_gallery_photos(campaign_id, limit=300)
    return donations, invoices, items, photos


@st.cache_data(ttl=60)
def load_used_categories(campaign_id: str) -> list[str]:
    """Cached because the admin forms read it on every rerun — and a data_editor
    reruns on each keystroke."""
    return db.get_used_categories(campaign_id)


@st.cache_data(ttl=60)
def load_global_totals(campaign_ids: tuple[str, ...]):
    """La clave del caché es una tupla (hashable) de ids de campaña, así que
    cambia sola si se activa o pausa una campaña."""
    return db.get_global_totals(list(campaign_ids))


@st.cache_data(ttl=60)
def load_invoice_picker(campaign_id: str):
    """Facturas con sus artículos + fotos ya vinculadas, para armar el selector
    de factura. Cacheado porque el formulario de evidencias se re-ejecuta en
    cada interacción."""
    return db.get_invoices_with_items(campaign_id), db.get_gallery_photos(campaign_id, limit=300)


def clear_caches():
    """Call after any write. Every cache here is keyed by campaign_id, so
    clearing them together keeps categories, invoices and dashboard data from
    drifting apart."""
    load_data.clear()
    load_used_categories.clear()
    load_invoice_picker.clear()
    load_global_totals.clear()
