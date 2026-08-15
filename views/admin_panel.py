from datetime import date

import pandas as pd
import streamlit as st

import database as db
from views.data import clear_caches, load_invoice_picker, load_used_categories
from views.public_dashboard import render_top_nav
from views.theme import CATEGORY_OPTIONS, format_currency, format_date


def category_options(campaign_id: str) -> list[str]:
    """Las categorías que ve el usuario: las base, más las que esta campaña ya
    usó en facturas anteriores, más las que agregó en esta sesión y todavía no
    guardó. Una categoría propia sobrevive así al reinicio: en cuanto se guarda
    una factura con ella, vuelve por la vía de las 'ya usadas'."""
    session_extras = st.session_state.setdefault("extra_categories", [])
    try:
        used = load_used_categories(campaign_id)
    except Exception:
        used = []  # sin conexión, al menos las base siguen disponibles
    base = [c for c in CATEGORY_OPTIONS if c != "Otros"]
    custom = sorted({c for c in [*used, *session_extras] if c and c not in CATEGORY_OPTIONS})
    return [*base, *custom, "Otros"]


def render_category_adder(campaign_id: str):
    with st.popover("Nueva categoría", icon=":material/add:"):
        st.caption("Se agrega a la lista de categorías de esta campaña.")
        with st.form("new_category_form", clear_on_submit=True):
            name = st.text_input("Nombre de la categoría")
            submitted = st.form_submit_button("Agregar")
        if submitted:
            clean = name.strip()
            existing = category_options(campaign_id)
            if not clean:
                st.error("Escribí un nombre.")
            elif clean.casefold() in {c.casefold() for c in existing}:
                st.warning(f"'{clean}' ya está en la lista.")
            else:
                st.session_state.extra_categories.append(clean)
                st.rerun()


def render_donation_form():
    campaign_id = st.session_state.campaign["id"]

    with st.form("donation_form", clear_on_submit=True):
        amount = st.number_input("Monto", min_value=0, step=1000, format="%d")
        donation_date = st.date_input("Fecha", value=date.today())
        notes = st.text_area("Nota / Concepto (opcional)")
        submitted = st.form_submit_button("Registrar Donación")

    if submitted:
        if amount <= 0:
            st.error("El monto debe ser mayor a cero.")
        else:
            db.create_donation(
                campaign_id=campaign_id, amount=amount, donation_date=donation_date, notes=notes.strip() or None
            )
            st.success("Donación registrada.")
            clear_caches()
            st.rerun()

    render_donation_management(campaign_id)


def render_donation_management(campaign_id: str):
    donations = db.get_donations(campaign_id, limit=1000)
    if not donations:
        return

    st.divider()
    st.markdown("**Donaciones registradas**")
    df = pd.DataFrame(
        [
            {
                "id": d["id"],
                "Fecha": date.fromisoformat(d["donation_date"]),
                "Monto": d["amount"],
                "Notas": d.get("notes") or "",
                "Borrar": False,
            }
            for d in donations
        ]
    )
    edited = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        key="donations_editor",
        column_config={
            "id": None,
            "Fecha": st.column_config.DateColumn(required=True),
            "Monto": st.column_config.NumberColumn(min_value=0, step=1000),
            "Notas": st.column_config.TextColumn(),
            "Borrar": st.column_config.CheckboxColumn(help="Marcar para eliminar al guardar"),
        },
    )

    if st.button("Guardar cambios en donaciones"):
        originals = {d["id"]: d for d in donations}
        for _, row in edited.iterrows():
            donation_id = row["id"]
            original = originals[donation_id]
            if row["Borrar"]:
                db.delete_donation(donation_id, campaign_id)
                continue
            new_date = row["Fecha"].isoformat()
            new_notes = row["Notas"].strip() or None
            if (
                float(row["Monto"]) != float(original["amount"])
                or new_date != original["donation_date"]
                or new_notes != original.get("notes")
            ):
                db.update_donation(donation_id, campaign_id, amount=row["Monto"], donation_date=new_date, notes=new_notes)
        st.success("Cambios guardados.")
        clear_caches()
        st.rerun()


def render_invoice_form():
    campaign_id = st.session_state.campaign["id"]

    if "invoice_form_key" not in st.session_state:
        st.session_state.invoice_form_key = 0
    form_key = st.session_state.invoice_form_key

    st.markdown("**Datos generales**")
    merchant = st.text_input("Comercio / Proveedor", key=f"invoice_merchant_{form_key}")
    invoice_number = st.text_input("Número de factura", key=f"invoice_number_{form_key}")
    invoice_date = st.date_input("Fecha", value=date.today(), key=f"invoice_date_{form_key}")

    categories = category_options(campaign_id)

    header_cols = st.columns([3, 1], vertical_alignment="bottom")
    with header_cols[0]:
        st.markdown("**Artículos**")
    with header_cols[1]:
        render_category_adder(campaign_id)

    empty_items = pd.DataFrame(
        [{"Artículo": "", "Categoría": categories[0], "Cantidad": 1, "Precio Unitario": 0, "Impuestos": 0}]
    )
    items_df = st.data_editor(
        empty_items,
        num_rows="dynamic",
        width="stretch",
        key=f"invoice_items_editor_{form_key}",
        column_config={
            "Artículo": st.column_config.TextColumn(required=True),
            "Categoría": st.column_config.SelectboxColumn(options=categories, required=True),
            "Cantidad": st.column_config.NumberColumn(min_value=0, step=1),
            "Precio Unitario": st.column_config.NumberColumn(min_value=0, step=100),
            "Impuestos": st.column_config.NumberColumn(min_value=0, step=100),
        },
    )

    if st.button("Guardar Factura Completa"):
        valid_items = items_df[items_df["Artículo"].fillna("").str.strip() != ""]
        if not merchant.strip():
            st.error("El comercio/proveedor es obligatorio.")
        elif valid_items.empty:
            st.error("Agrega al menos un artículo con nombre.")
        else:
            items_payload = [
                {
                    "item_name": row["Artículo"].strip(),
                    "category": row["Categoría"],
                    "quantity": row["Cantidad"],
                    "unit_price": row["Precio Unitario"],
                    "tax_amount": row["Impuestos"],
                }
                for _, row in valid_items.iterrows()
            ]
            db.create_invoice_with_items(
                campaign_id=campaign_id,
                merchant=merchant.strip(),
                items=items_payload,
                invoice_number=invoice_number.strip() or None,
                invoice_date=invoice_date,
            )
            st.success("Factura registrada con sus ítems.")
            clear_caches()
            # Cambiar la key del formulario fuerza a Streamlit a montar widgets
            # nuevos en blanco — a diferencia de popear las keys viejas de
            # session_state, esto sí resetea de forma confiable el data_editor.
            st.session_state.invoice_form_key += 1
            st.rerun()

    render_invoice_management(campaign_id)


def render_invoice_management(campaign_id: str):
    invoices = db.get_invoices(campaign_id, limit=1000)
    if not invoices:
        return

    st.divider()
    st.markdown("**Facturas registradas**")
    categories = category_options(campaign_id)
    for invoice in invoices:
        items = db.get_invoice_items(invoice["id"])
        total = sum(item["total_price"] for item in items)
        title = f"{invoice['merchant']} — {invoice['invoice_date']} — {format_currency(total)}"

        with st.expander(title):
            col1, col2 = st.columns(2)
            with col1:
                merchant = st.text_input(
                    "Comercio / Proveedor", value=invoice["merchant"], key=f"inv_merchant_{invoice['id']}"
                )
                invoice_number = st.text_input(
                    "Número de factura", value=invoice.get("invoice_number") or "", key=f"inv_number_{invoice['id']}"
                )
            with col2:
                invoice_date_value = st.date_input(
                    "Fecha", value=date.fromisoformat(invoice["invoice_date"]), key=f"inv_date_{invoice['id']}"
                )
                notes = st.text_input("Notas", value=invoice.get("notes") or "", key=f"inv_notes_{invoice['id']}")

            st.markdown("**Artículos**")
            if items:
                items_df = pd.DataFrame(
                    [
                        {
                            "id": item["id"],
                            "Artículo": item["item_name"],
                            "Categoría": item.get("category") or categories[0],
                            "Cantidad": item["quantity"],
                            "Precio Unitario": item["unit_price"],
                            "Impuestos": item["tax_amount"],
                        }
                        for item in items
                    ]
                )
            else:
                items_df = pd.DataFrame(
                    columns=["id", "Artículo", "Categoría", "Cantidad", "Precio Unitario", "Impuestos"]
                )

            edited_items = st.data_editor(
                items_df,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key=f"inv_items_editor_{invoice['id']}",
                column_config={
                    "id": None,
                    "Artículo": st.column_config.TextColumn(required=True),
                    "Categoría": st.column_config.SelectboxColumn(options=categories, required=True),
                    "Cantidad": st.column_config.NumberColumn(min_value=0, step=1),
                    "Precio Unitario": st.column_config.NumberColumn(min_value=0, step=100),
                    "Impuestos": st.column_config.NumberColumn(min_value=0, step=100),
                },
            )

            action_cols = st.columns([2, 1])
            with action_cols[0]:
                if st.button("Guardar cambios", key=f"inv_save_{invoice['id']}"):
                    if not merchant.strip():
                        st.error("El comercio/proveedor es obligatorio.")
                    else:
                        db.update_invoice(
                            invoice["id"],
                            campaign_id,
                            merchant=merchant.strip(),
                            invoice_number=invoice_number.strip() or None,
                            invoice_date=invoice_date_value.isoformat(),
                            notes=notes.strip() or None,
                        )
                        original_ids = {item["id"] for item in items}
                        kept_ids = set()
                        for _, row in edited_items.iterrows():
                            item_name = str(row["Artículo"]).strip()
                            if not item_name:
                                continue
                            item_id = row.get("id")
                            item_fields = dict(
                                item_name=item_name,
                                category=row["Categoría"],
                                quantity=row["Cantidad"],
                                unit_price=row["Precio Unitario"],
                                tax_amount=row["Impuestos"],
                            )
                            if pd.notna(item_id):
                                kept_ids.add(item_id)
                                db.update_invoice_item(item_id, campaign_id, **item_fields)
                            else:
                                db.create_invoice_item(invoice["id"], campaign_id, **item_fields)
                        for removed_id in original_ids - kept_ids:
                            db.delete_invoice_item(removed_id, campaign_id)
                        st.success("Factura actualizada.")
                        clear_caches()
                        st.rerun()
            with action_cols[1]:
                with st.popover("🗑️ Borrar factura"):
                    st.warning("Esto borra la factura y todos sus ítems. No se puede deshacer.")
                    if st.button("Sí, borrar definitivamente", key=f"inv_delete_confirm_{invoice['id']}"):
                        db.delete_invoice(invoice["id"], campaign_id)
                        st.success("Factura eliminada.")
                        clear_caches()
                        st.rerun()


def build_invoice_picker(campaign_id: str):
    """Arma las opciones de factura para las evidencias.

    La etiqueta lleva comercio, fecha, MONTO y los primeros artículos porque hay
    varias facturas del mismo comercio en la misma fecha: sin el monto son
    indistinguibles y las fotos terminan colgadas de la factura equivocada.
    El prefijo marca cuáles todavía no tienen ninguna foto.

    Devuelve (choices, label_fn, facturas_sin_evidencia)."""
    invoices, photos = load_invoice_picker(campaign_id)
    con_foto = {photo["invoice_id"] for photo in photos if photo.get("invoice_id")}

    labels, sin_evidencia = {}, []
    for invoice in invoices:
        items = invoice.get("invoice_items") or []
        total = sum(float(item["total_price"]) for item in items)
        nombres = ", ".join(item["item_name"] for item in items[:2]) or "sin artículos"
        extra = f" +{len(items) - 2}" if len(items) > 2 else ""
        tiene_foto = invoice["id"] in con_foto
        if not tiene_foto:
            sin_evidencia.append((invoice, total))
        labels[invoice["id"]] = (
            f"{'✅' if tiene_foto else '⬜'} {invoice['merchant']} · "
            f"{format_date(invoice['invoice_date'])} · {format_currency(total)} · {nombres}{extra}"
        )

    # None = evidencia general (una entrega, una jornada) sin compra puntual.
    choices = [None] + [invoice["id"] for invoice in invoices]

    def label_fn(value):
        return "— Sin factura (evidencia general) —" if value is None else labels.get(value, "Factura")

    return choices, label_fn, sin_evidencia


def render_missing_evidence_notice(sin_evidencia):
    if not sin_evidencia:
        return
    with st.container(border=True):
        st.markdown(f"**{len(sin_evidencia)} factura(s) todavía sin evidencia**")
        for invoice, total in sin_evidencia:
            st.caption(
                f"⬜ {invoice['merchant']} · {format_date(invoice['invoice_date'])} · {format_currency(total)}"
            )


def render_evidence_form():
    """Carga masiva: se sueltan todas las fotos de una, y después se completa
    título y factura foto por foto. El formulario NO va dentro de un st.form
    porque hace falta que la miniatura y los campos aparezcan apenas se
    seleccionan los archivos, no recién al enviar."""
    campaign = st.session_state.campaign
    invoice_choices, invoice_label, sin_evidencia = build_invoice_picker(campaign["id"])
    render_missing_evidence_notice(sin_evidencia)

    # Cambiar esta clave monta un uploader nuevo y vacío: es la forma confiable
    # de limpiarlo después de subir (igual que en el formulario de facturas).
    uploader_key = st.session_state.setdefault("evidence_uploader_key", 0)

    files = st.file_uploader(
        "Fotos (JPG/PNG) — podés arrastrar varias a la vez",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"evidence_files_{uploader_key}",
    )

    if not files:
        st.caption("Seleccioná una o varias fotos para empezar.")
        render_gallery_management(campaign, invoice_label, invoice_choices)
        return

    st.markdown(f"**{len(files)} foto(s) lista(s).** Poneles título y, si respaldan una compra, la factura.")

    with st.container(border=True):
        st.markdown("**Completar todas de una vez** _(opcional)_")
        bulk_cols = st.columns([3, 3, 1], vertical_alignment="bottom")
        base_title = bulk_cols[0].text_input(
            "Título base", key=f"bulk_title_{uploader_key}",
            placeholder="Ej: Entrega centro de acopio",
            help="Se numera automáticamente: '… 1', '… 2', …",
        )
        bulk_invoice = bulk_cols[1].selectbox(
            "Factura para todas", options=invoice_choices,
            format_func=invoice_label, key=f"bulk_invoice_{uploader_key}",
        )
        if bulk_cols[2].button("Aplicar", width="stretch"):
            for position, file in enumerate(files, start=1):
                if base_title.strip():
                    suffix = f" {position}" if len(files) > 1 else ""
                    st.session_state[f"evtitle_{file.file_id}"] = f"{base_title.strip()}{suffix}"
                st.session_state[f"evinvoice_{file.file_id}"] = bulk_invoice
            st.rerun()

    for position, file in enumerate(files, start=1):
        with st.container(border=True):
            cols = st.columns([1, 3, 3], vertical_alignment="center")
            with cols[0]:
                st.image(file.getvalue(), width=110)
            with cols[1]:
                st.text_input(f"Título de la foto {position}", key=f"evtitle_{file.file_id}")
            with cols[2]:
                st.selectbox(
                    "Factura que respalda", options=invoice_choices,
                    format_func=invoice_label, key=f"evinvoice_{file.file_id}",
                )

    sin_titulo = [
        position for position, file in enumerate(files, start=1)
        if not st.session_state.get(f"evtitle_{file.file_id}", "").strip()
    ]

    if st.button(f"Cargar {len(files)} evidencia(s)", type="primary"):
        if sin_titulo:
            st.error(f"Falta el título de la(s) foto(s): {', '.join(map(str, sin_titulo))}.")
        else:
            progress = st.progress(0.0, text="Subiendo…")
            subidas, fallidas = 0, []
            for position, file in enumerate(files, start=1):
                try:
                    db.upload_gallery_photo(
                        campaign_id=campaign["id"],
                        campaign_slug=campaign["slug"],
                        file_bytes=file.getvalue(),
                        original_filename=file.name,
                        content_type=file.type,
                        title=st.session_state[f"evtitle_{file.file_id}"].strip(),
                        invoice_id=st.session_state.get(f"evinvoice_{file.file_id}"),
                    )
                    subidas += 1
                except Exception as error:
                    fallidas.append((file.name, str(error)))
                progress.progress(position / len(files), text=f"Subiendo {position} de {len(files)}…")
            progress.empty()

            # Las claves van por file_id, que no se repite: se limpian para que
            # la sesión no acumule basura carga tras carga.
            for file in files:
                st.session_state.pop(f"evtitle_{file.file_id}", None)
                st.session_state.pop(f"evinvoice_{file.file_id}", None)

            if fallidas:
                st.error(f"{subidas} subida(s) y {len(fallidas)} con error:")
                for nombre, detalle in fallidas:
                    st.caption(f"• {nombre}: {detalle}")
            else:
                st.success(f"{subidas} evidencia(s) cargada(s).")
                st.session_state.evidence_uploader_key += 1
                clear_caches()
                st.rerun()

    render_gallery_management(campaign, invoice_label, invoice_choices)


def render_campaign_photo_form():
    """Foto de quien lidera la campaña. Cada campaña administra la suya; el
    operador del sitio no tiene que hacerlo por ella.

    Va fuera de un st.form porque un file_uploader dentro de un formulario sólo
    se procesa al enviarlo, y acá conviene que la foto se suba y se vea al toque."""
    campaign = st.session_state.campaign

    try:
        actual = db.get_campaign_by_slug(campaign["slug"]) or {}
    except Exception as error:
        st.error(f"No se pudo leer la campaña: {error}")
        return
    foto = actual.get("photo_url")

    st.markdown("**Tu foto en el tablero público**")
    st.caption(
        "Aparece en el banner de tu campaña, junto a los datos para aportar. "
        "Ponerle cara a la campaña le da confianza a quien está decidiendo si ayuda."
    )

    cols = st.columns([1, 3], vertical_alignment="center")
    with cols[0]:
        if foto:
            st.image(foto, width="stretch")
        else:
            st.caption("Todavía sin foto")
    with cols[1]:
        subida = st.file_uploader(
            "Elegí una foto (JPG/PNG)", type=["jpg", "jpeg", "png"], key="campaign_photo"
        )
        acciones = st.columns(2)
        with acciones[0]:
            if st.button("Guardar foto", disabled=subida is None, width="stretch"):
                try:
                    db.upload_campaign_photo(
                        campaign_id=campaign["id"],
                        campaign_slug=campaign["slug"],
                        file_bytes=subida.getvalue(),
                        original_filename=subida.name,
                        content_type=subida.type,
                    )
                    st.success("Foto actualizada.")
                    clear_caches()
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo subir la foto: {error}")
        with acciones[1]:
            if foto and st.button("Quitar foto", width="stretch"):
                db.remove_campaign_photo(campaign["id"])
                clear_caches()
                st.rerun()


def render_gallery_management(campaign: dict, invoice_label, invoice_choices):
    """Fotos ya publicadas: permite corregir el título, reasignar la factura a
    la que pertenecen, y borrar. La miniatura va en el encabezado plegado para
    poder reconocer la foto sin tener que abrir una por una."""
    photos = db.get_gallery_photos(campaign["id"], limit=300)
    if not photos:
        return

    st.divider()
    st.markdown(f"**Evidencias publicadas ({len(photos)})**")
    st.caption("Acá podés corregir a qué factura pertenece cada foto.")

    solo_sin_factura = st.toggle(
        "Ver sólo las que no tienen factura asignada", key="filtro_sin_factura"
    )
    visibles = [p for p in photos if not p.get("invoice_id")] if solo_sin_factura else photos
    if not visibles:
        st.success("Todas las evidencias tienen su factura asignada.")
        return

    for photo in visibles:
        estado = "⬜ sin factura" if not photo.get("invoice_id") else "✅"
        with st.expander(f"{estado} · {photo['title']} · {format_date(photo['created_at'][:10])}"):
            cols = st.columns([1, 3], vertical_alignment="center")
            with cols[0]:
                st.image(photo["photo_url"], width="stretch")
            with cols[1]:
                title = st.text_input("Título", value=photo["title"], key=f"gtitle_{photo['id']}")
                current = photo.get("invoice_id")
                invoice_id = st.selectbox(
                    "Factura que respalda",
                    options=invoice_choices,
                    index=invoice_choices.index(current) if current in invoice_choices else 0,
                    format_func=invoice_label,
                    key=f"ginvoice_{photo['id']}",
                )
                action_cols = st.columns(2)
                with action_cols[0]:
                    if st.button("Guardar", key=f"gsave_{photo['id']}", width="stretch"):
                        if not title.strip():
                            st.error("El título es obligatorio.")
                        else:
                            db.update_gallery_photo(
                                photo["id"], campaign["id"],
                                title=title.strip(), invoice_id=invoice_id,
                            )
                            st.success("Actualizada.")
                            clear_caches()
                            st.rerun()
                with action_cols[1]:
                    with st.popover("Borrar", width="stretch"):
                        st.warning("Se quita del tablero público. No se puede deshacer.")
                        if st.button("Sí, borrar", key=f"gdel_{photo['id']}"):
                            db.delete_gallery_photo(photo["id"], campaign["id"])
                            clear_caches()
                            st.rerun()


def render():
    if "campaign" not in st.session_state:
        st.session_state.campaign = None

    selector_page = st.session_state.get("_selector_page")

    if st.session_state.campaign is None:
        st.title("🔒 Panel de Gestión")
        st.caption("Acceso exclusivo para la campaña correspondiente.")

        _, center, _ = st.columns([1, 1.2, 1])
        with center:
            with st.container(border=True):
                with st.form("login_form"):
                    username = st.text_input("Usuario")
                    password = st.text_input("Contraseña", type="password")
                    submitted = st.form_submit_button("Iniciar sesión", width="stretch")
                if submitted:
                    campaign = db.verify_campaign_login(username, password)
                    if campaign:
                        st.session_state.campaign = campaign
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")

        st.write("")
        if selector_page is not None:
            st.page_link(selector_page, label="← Volver al selector de campañas")
        return

    campaign = st.session_state.campaign

    # Accesos arriba de todo, incluido el del operador: esta pantalla ya está
    # detrás de credenciales, así que acá sí corresponde mostrarlo.
    render_top_nav(include_operator=True)

    header_cols = st.columns([4, 1], vertical_alignment="center")
    with header_cols[0]:
        st.title("🔒 Panel de Gestión")
        st.caption(f"Campaña: **{campaign['name']}** — registra donaciones, facturas y evidencias.")
    with header_cols[1]:
        if st.button("Cerrar sesión", width="stretch"):
            st.session_state.campaign = None
            st.rerun()

    st.divider()

    tab_donacion, tab_factura, tab_evidencia, tab_campana = st.tabs(
        ["💰 Donaciones", "🧾 Facturas", "📸 Cargar Evidencias", "⚙️ Mi campaña"]
    )
    with tab_donacion:
        render_donation_form()
    with tab_factura:
        render_invoice_form()
    with tab_evidencia:
        render_evidence_form()
    with tab_campana:
        render_campaign_photo_form()
