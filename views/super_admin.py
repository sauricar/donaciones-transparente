import re

import streamlit as st

import database as db
from views.auth import get_operator_password
from views.public_dashboard import render_top_nav

_ACCENTS = str.maketrans("áéíóúüñ", "aeiouun")


def slugify(name: str) -> str:
    slug = name.strip().lower().translate(_ACCENTS)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def render_create_form():
    st.markdown("**Nueva campaña**")
    st.caption(
        "Acá se define quién entra y con qué link. Cómo se presenta la campaña "
        "—descripción, datos para aportar y foto— lo escribe ella misma desde su "
        "panel de gestión."
    )
    with st.form("create_campaign_form", clear_on_submit=True):
        name = st.text_input("Nombre de la campaña / persona")
        slug = st.text_input("Slug para el link público (se sugiere a partir del nombre si lo dejás vacío)")
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
                                is_active=is_active,
                            )
                            st.success("Campaña actualizada.")
                            st.rerun()
                        except Exception as error:
                            st.error(_friendly_update_error(error))

            st.caption(
                "La descripción pública, los datos para aportar y la foto los edita "
                "cada campaña desde su panel de gestión, no desde acá."
            )

            with st.popover("Restablecer contraseña"):
                with st.form(f"reset_password_{campaign['id']}"):
                    new_password = st.text_input("Nueva contraseña", type="password", key=f"pw_{campaign['id']}")
                    if st.form_submit_button("Guardar"):
                        if new_password:
                            db.update_campaign(campaign["id"], password=new_password)
                            st.success("Contraseña actualizada.")
                        else:
                            st.error("Ingresá una contraseña.")


def _operator_login(username: str, password: str) -> bool:
    """Valida contra la tabla operators. Si esa tabla todavía no existe (base sin
    migrar), cae al esquema viejo: sólo la contraseña ADMIN_PASSWORD, ignorando
    el usuario. Ver migration_operadores.sql."""
    resultado = db.verify_operator_login(username, password)
    if resultado is not db.OPERATORS_TABLE_MISSING:
        return bool(resultado)

    operator_password = get_operator_password()
    return bool(operator_password) and password == operator_password


def render():
    if "is_operator" not in st.session_state:
        st.session_state.is_operator = False

    selector_page = st.session_state.get("_selector_page")

    st.title("🛠️ Administración de Campañas")
    st.caption("Acceso exclusivo para el operador del sitio.")

    if not st.session_state.is_operator:
        _, center, _ = st.columns([1, 1.2, 1])
        with center:
            with st.container(border=True, key="operator_login_card"):
                with st.form("operator_login_form"):
                    username = st.text_input("Usuario")
                    password = st.text_input("Contraseña", type="password")
                    submitted = st.form_submit_button("Iniciar sesión", width="stretch")
                if submitted:
                    try:
                        autorizado = _operator_login(username, password)
                    except Exception as error:
                        st.error(f"No se pudo verificar el acceso: {error}")
                    else:
                        if autorizado:
                            st.session_state.is_operator = True
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

        st.write("")
        if selector_page is not None:
            st.page_link(selector_page, label="← Volver a la página principal")
        return

    # Los accesos de arriba (Campañas / Gestión) son la vuelta a la portada:
    # antes, una vez adentro de este panel no había forma de salir sin editar
    # la URL a mano.
    render_top_nav()

    if st.button("Cerrar sesión"):
        st.session_state.is_operator = False
        st.rerun()

    st.divider()
    render_create_form()
    st.divider()
    render_campaign_list()
