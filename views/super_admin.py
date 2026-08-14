import re

import streamlit as st

import database as db
from views.auth import get_operator_password

_ACCENTS = str.maketrans("áéíóúüñ", "aeiouun")


def slugify(name: str) -> str:
    slug = name.strip().lower().translate(_ACCENTS)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def render_create_form():
    st.markdown("**Nueva campaña**")
    with st.form("create_campaign_form", clear_on_submit=True):
        name = st.text_input("Nombre de la campaña / persona")
        slug = st.text_input("Slug para el link público (se sugiere a partir del nombre si lo dejás vacío)")
        description = st.text_area("Descripción pública (opcional)")
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Usuario de acceso")
        with col2:
            password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Crear campaña")

    if submitted:
        final_slug = slugify(slug or name)
        if not name.strip():
            st.error("El nombre es obligatorio.")
        elif not final_slug:
            st.error("No se pudo generar un slug válido a partir de esos datos.")
        elif not username.strip():
            st.error("El usuario es obligatorio.")
        elif not password:
            st.error("La contraseña es obligatoria.")
        else:
            try:
                db.create_campaign(
                    slug=final_slug,
                    name=name.strip(),
                    username=username.strip(),
                    password=password,
                    description=description.strip() or None,
                )
                st.success(f"Campaña creada. Link público: ?c={final_slug}")
                st.rerun()
            except Exception as error:
                st.error(_friendly_update_error(error))


def _friendly_update_error(error: Exception) -> str:
    message = str(error)
    if "slug" in message and "duplicate" in message.lower() or "campaigns_slug_key" in message:
        return "Ya existe una campaña con ese slug. Elegí otro."
    if "username" in message and "duplicate" in message.lower() or "campaigns_username_key" in message:
        return "Ya existe una campaña con ese usuario. Elegí otro."
    return f"No se pudo guardar: {message}"


def render_photo_uploader(campaign: dict):
    """Foto de quien lidera la campaña. Va aparte del formulario de edición
    porque un file_uploader dentro de un st.form sólo se procesa al enviar, y
    acá conviene que la foto se suba y se vea de inmediato."""
    current = campaign.get("photo_url")
    cols = st.columns([1, 3], vertical_alignment="center")
    with cols[0]:
        if current:
            st.image(current, width=90)
        else:
            st.caption("Sin foto")
    with cols[1]:
        uploaded = st.file_uploader(
            "Foto de quien lidera la campaña",
            type=["jpg", "jpeg", "png"],
            key=f"photo_{campaign['id']}",
            help="Se muestra en el banner del tablero público, para ponerle cara a la campaña.",
        )
        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button("Guardar foto", key=f"savephoto_{campaign['id']}", disabled=uploaded is None):
                try:
                    db.upload_campaign_photo(
                        campaign_id=campaign["id"],
                        campaign_slug=campaign["slug"],
                        file_bytes=uploaded.getvalue(),
                        original_filename=uploaded.name,
                        content_type=uploaded.type,
                    )
                    st.success("Foto actualizada.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo subir la foto: {error}")
        with action_cols[1]:
            if current and st.button("Quitar foto", key=f"delphoto_{campaign['id']}"):
                db.remove_campaign_photo(campaign["id"])
                st.rerun()


def render_campaign_list():
    st.markdown("**Campañas existentes**")
    campaigns = db.get_campaigns_admin()
    if not campaigns:
        st.info("Todavía no hay campañas.")
        return

    for campaign in campaigns:
        status_label = "🟢 Activa" if campaign["is_active"] else "⏸️ Pausada"
        with st.expander(f"{campaign['name']} — {status_label}"):
            st.caption(f"Link público: ?c={campaign['slug']}")

            with st.form(f"edit_campaign_{campaign['id']}"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Nombre", value=campaign["name"], key=f"name_{campaign['id']}")
                    slug = st.text_input("Slug", value=campaign["slug"], key=f"slug_{campaign['id']}")
                with col2:
                    username = st.text_input("Usuario", value=campaign["username"], key=f"username_{campaign['id']}")
                    is_active = st.toggle("Activa", value=campaign["is_active"], key=f"active_{campaign['id']}")
                description = st.text_area(
                    "Descripción pública", value=campaign.get("description") or "", key=f"desc_{campaign['id']}"
                )
                donation_info = st.text_area(
                    "Cómo aportar (opcional)",
                    value=campaign.get("donation_info") or "",
                    key=f"dinfo_{campaign['id']}",
                    help="Nequi, Daviplata, cuenta bancaria, contacto… Si lo dejás vacío, "
                         "el tablero público no muestra este bloque.",
                )
                if st.form_submit_button("Guardar cambios"):
                    final_slug = slugify(slug)
                    if not name.strip():
                        st.error("El nombre es obligatorio.")
                    elif not final_slug:
                        st.error("El slug no puede quedar vacío.")
                    elif not username.strip():
                        st.error("El usuario es obligatorio.")
                    else:
                        try:
                            db.update_campaign(
                                campaign["id"],
                                name=name.strip(),
                                slug=final_slug,
                                username=username.strip(),
                                description=description.strip() or None,
                                donation_info=donation_info.strip() or None,
                                is_active=is_active,
                            )
                            st.success("Campaña actualizada.")
                            st.rerun()
                        except Exception as error:
                            st.error(_friendly_update_error(error))

            render_photo_uploader(campaign)

            with st.popover("Restablecer contraseña"):
                with st.form(f"reset_password_{campaign['id']}"):
                    new_password = st.text_input("Nueva contraseña", type="password", key=f"pw_{campaign['id']}")
                    if st.form_submit_button("Guardar"):
                        if new_password:
                            db.update_campaign(campaign["id"], password=new_password)
                            st.success("Contraseña actualizada.")
                        else:
                            st.error("Ingresá una contraseña.")


def render():
    if "is_operator" not in st.session_state:
        st.session_state.is_operator = False

    st.title("🛠️ Administración de Campañas")
    st.caption("Acceso exclusivo para el operador del sitio.")

    if not st.session_state.is_operator:
        _, center, _ = st.columns([1, 1.2, 1])
        with center:
            with st.container(border=True):
                with st.form("operator_login_form"):
                    password = st.text_input("Contraseña de operador", type="password")
                    submitted = st.form_submit_button("Iniciar sesión", width="stretch")
                if submitted:
                    operator_password = get_operator_password()
                    if operator_password and password == operator_password:
                        st.session_state.is_operator = True
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta.")
        return

    if st.button("Cerrar sesión"):
        st.session_state.is_operator = False
        st.rerun()

    st.divider()
    render_create_form()
    st.divider()
    render_campaign_list()
