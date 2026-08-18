"""
Data access layer for Supabase. See schema.sql for the exact table definitions.

Tables: campaigns, donations, invoices, invoice_items, gallery_photos.
Every donation/invoice/gallery_photos row belongs to exactly one campaign
(campaign_id) — each campaign is a separate person/org being tracked, with its
own login. donations intentionally has no donor-identifying columns (public
transparency app). invoice_items.total_price is a generated column in
Postgres — never set it directly. Storage bucket expected for gallery photos:
"evidencias" (objects are namespaced "{campaign_slug}/{uuid}.{ext}").

donations/invoices/invoice_items/gallery_photos have RLS enabled with a public
"select" policy only (see schema.sql) — anon can read but never write. campaigns
has RLS enabled with NO select policy at all, since it holds password_hash —
only the admin (service_role) client can ever read it, and the functions below
always explicitly allowlist safe columns when returning campaign data to
callers. Every create/update/delete function below therefore goes through
get_admin_client(), which uses the service_role key (bypasses RLS) instead of
the anon key used for reads. The service_role key must never reach the
browser; that's safe here because Streamlit only runs it server-side, and
write access is gated by a per-campaign username/password check
(verify_campaign_login) or the operator password (views/auth.py) before any of
these functions are reachable.
"""

import os
from datetime import date
from uuid import uuid4

import bcrypt
import streamlit as st
from supabase import create_client, Client

from translator import translate_to_english

GALLERY_BUCKET = "evidencias"
CAMPAIGN_BASE_COLUMNS = "id,slug,name,description,is_active,created_at"
CAMPAIGN_PUBLIC_COLUMNS = CAMPAIGN_BASE_COLUMNS + ",donation_info,photo_url"
CAMPAIGN_I18N_COLUMNS = CAMPAIGN_PUBLIC_COLUMNS + ",description_en,donation_info_en"

# Cada juego de columnas depende de una migración distinta: donation_info y
# photo_url llegaron con migration_como_aportar.sql, y las _en con
# migration_idioma_ingles.sql. El código no puede exigir que las migraciones
# vayan primero, así que prueba del juego más completo al más pobre y se queda
# con el primero que la base acepte: sin la migración de idioma el tablero
# traduce en vivo, y sin la del banner ese bloque simplemente no aparece —
# mucho mejor que tumbar todo el tablero.
_CASCADA_COLUMNAS = (CAMPAIGN_I18N_COLUMNS, CAMPAIGN_PUBLIC_COLUMNS, CAMPAIGN_BASE_COLUMNS)
_campaign_columns = CAMPAIGN_I18N_COLUMNS


def _campaign_rows(build):
    """build recibe la lista de columnas y devuelve la consulta ya armada."""
    global _campaign_columns
    try:
        return build(_campaign_columns).execute().data
    except Exception:
        for siguiente in _CASCADA_COLUMNAS[_CASCADA_COLUMNAS.index(_campaign_columns) + 1:]:
            try:
                filas = build(siguiente).execute().data
            except Exception:
                continue
            _campaign_columns = siguiente
            return filas
        raise  # no era una columna faltante: es un error real


@st.cache_resource
def get_client() -> Client:
    """Anon-key client — read-only under RLS. Used by every get_*/list function."""
    url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise RuntimeError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY "
            "in .streamlit/secrets.toml or as environment variables."
        )
    return create_client(url, key)


@st.cache_resource
def get_admin_client() -> Client:
    """Service-role client — bypasses RLS. Used only by create/update/delete functions."""
    url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_KEY"))
    if not url or not key:
        raise RuntimeError(
            "Missing Supabase admin credentials. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_KEY in .streamlit/secrets.toml or as environment variables."
        )
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Campaigns (one per person/org being tracked; each has its own login)
# ---------------------------------------------------------------------------

def get_campaigns_public(active_only: bool = True) -> list[dict]:
    def build(columns):
        query = get_admin_client().table("campaigns").select(columns)
        if active_only:
            query = query.eq("is_active", True)
        return query.order("name")

    return _campaign_rows(build)


def get_campaigns_admin() -> list[dict]:
    """Same as get_campaigns_public but includes username — for the operator's
    management screen only (views/super_admin.py), never for public-facing views."""
    return _campaign_rows(
        lambda columns: get_admin_client().table("campaigns").select(f"{columns},username").order("name")
    )


def get_global_totals(campaign_ids: list[str]) -> dict:
    """Totales sumados de un conjunto de campañas, para la portada.

    Dos consultas en vez de una por campaña: los ítems llegan con el
    campaign_id de su factura embebido, ya que invoice_items no lo tiene
    propio. Se agrega en Python porque el conjunto es chico; si algún día
    fueran decenas de miles de filas, esto debería pasar a una vista o a una
    función de agregación en Postgres."""
    vacio = {"donado": 0.0, "ejecutado": 0.0, "pendiente": 0.0, "articulos": 0.0, "aportes": 0}
    if not campaign_ids:
        return vacio

    permitidas = set(campaign_ids)

    donaciones = (
        get_client().table("donations").select("amount,campaign_id").limit(20000).execute().data
    )
    propias = [d for d in donaciones if d["campaign_id"] in permitidas]

    items = (
        get_client()
        .table("invoice_items")
        .select("quantity,total_price,invoices!inner(campaign_id)")
        .limit(20000)
        .execute()
        .data
    )
    items_propios = [i for i in items if (i.get("invoices") or {}).get("campaign_id") in permitidas]

    donado = sum(float(d["amount"]) for d in propias)
    ejecutado = sum(float(i["total_price"]) for i in items_propios)
    return {
        "donado": donado,
        "ejecutado": ejecutado,
        "pendiente": donado - ejecutado,
        "articulos": sum(float(i["quantity"]) for i in items_propios),
        "aportes": len(propias),
    }


def get_campaign_by_slug(slug: str) -> dict | None:
    rows = _campaign_rows(
        lambda columns: get_admin_client().table("campaigns").select(columns).eq("slug", slug)
    )
    return rows[0] if rows else None


def verify_campaign_login(username: str, password: str) -> dict | None:
    """Returns the campaign dict (without password_hash) on success, else None."""
    response = (
        get_admin_client()
        .table("campaigns")
        .select("id,slug,name,username,password_hash,is_active")
        .eq("username", username.strip().lower())
        .execute()
    )
    if not response.data:
        return None
    campaign = response.data[0]
    if not campaign["is_active"]:
        return None
    if not bcrypt.checkpw(password.encode(), campaign["password_hash"].encode()):
        return None
    campaign.pop("password_hash")
    return campaign


# ---------------------------------------------------------------------------
# Traducción al inglés en el momento de guardar
# ---------------------------------------------------------------------------

# Qué texto libre de cada tabla se guarda además en inglés, en la columna
# <campo>_en (ver migration_idioma_ingles.sql). Sólo campos que un donante
# llega a leer: no tiene sentido traducir un número de factura.
CAMPOS_TRADUCIBLES = {
    "campaigns": ("description", "donation_info"),
    "donations": ("notes",),
    "invoices": ("notes", "merchant"),
    "invoice_items": ("item_name", "category"),
    "gallery_photos": ("title", "description"),
}


def _parece_columna_en_faltante(error: Exception) -> bool:
    mensaje = str(error).lower()
    return "_en" in mensaje and any(
        pista in mensaje for pista in ("does not exist", "schema cache", "pgrst204", "column")
    )


def _con_traduccion(tabla: str, payload: dict) -> dict:
    """Devuelve el payload con la versión en inglés de sus campos de texto.

    La traducción nunca puede tumbar un guardado: translate_to_english() ya
    devuelve el original ante cualquier falla, así que lo peor que pasa es que
    una nota quede en español en las dos columnas."""
    completo = dict(payload)
    for campo in CAMPOS_TRADUCIBLES.get(tabla, ()):
        if campo in payload:
            completo[f"{campo}_en"] = translate_to_english(payload.get(campo))
    return completo


def _sin_columnas_en(payload: dict) -> dict:
    return {clave: valor for clave, valor in payload.items() if not clave.endswith("_en")}


def _insert_traducido(tabla: str, payload: dict) -> dict:
    """Inserta guardando también la versión en inglés. Si esas columnas todavía
    no existen (migración sin correr), reintenta sin ellas: el registro se
    guarda igual y la app traduce en vivo al mostrarlo."""
    completo = _con_traduccion(tabla, payload)
    try:
        return get_admin_client().table(tabla).insert(completo).execute().data[0]
    except Exception as error:
        if not _parece_columna_en_faltante(error):
            raise
        return get_admin_client().table(tabla).insert(_sin_columnas_en(completo)).execute().data[0]


def _update_traducido(tabla: str, campos: dict, aplicar_filtros):
    """Igual que _insert_traducido pero para updates. `aplicar_filtros` recibe la
    consulta y le encadena los .eq() que correspondan, para que cada tabla
    mantenga su propio criterio de pertenencia a la campaña."""
    completo = _con_traduccion(tabla, campos)
    try:
        return aplicar_filtros(get_admin_client().table(tabla).update(completo)).execute()
    except Exception as error:
        if not _parece_columna_en_faltante(error):
            raise
        return aplicar_filtros(get_admin_client().table(tabla).update(_sin_columnas_en(completo))).execute()


def _pendientes_en_tabla(tabla: str, campos: tuple[str, ...], filtro) -> list[tuple[dict, list[str]]]:
    """Filas de esa tabla con texto en español pero sin su versión en inglés."""
    columnas = ",".join(["id", *campos, *[f"{campo}_en" for campo in campos]])
    try:
        filas = filtro(get_admin_client().table(tabla).select(columnas)).limit(5000).execute().data
    except Exception as error:
        if _parece_columna_en_faltante(error):
            return []  # sin migration_idioma_ingles.sql no hay nada que completar
        raise

    pendientes = []
    for fila in filas:
        faltan = [
            campo
            for campo in campos
            if (fila.get(campo) or "").strip() and not (fila.get(f"{campo}_en") or "").strip()
        ]
        if faltan:
            pendientes.append((fila, faltan))
    return pendientes


def textos_sin_traducir(campaign_id: str) -> list[tuple[str, dict, list[str]]]:
    """Todo lo de una campaña que todavía no tiene su versión en inglés guardada.

    Normalmente esto da vacío: cada registro se traduce al guardarse. Se llena
    cuando el servicio de traducción estaba caído en ese momento, o con lo que
    se cargó antes de que existiera el bilingüe."""
    facturas = (
        get_admin_client().table("invoices").select("id")
        .eq("campaign_id", campaign_id).limit(5000).execute().data
    )
    ids_facturas = [f["id"] for f in facturas]

    objetivos = [
        ("campaigns", lambda consulta: consulta.eq("id", campaign_id)),
        ("donations", lambda consulta: consulta.eq("campaign_id", campaign_id)),
        ("invoices", lambda consulta: consulta.eq("campaign_id", campaign_id)),
        ("gallery_photos", lambda consulta: consulta.eq("campaign_id", campaign_id)),
    ]
    if ids_facturas:
        objetivos.append(
            ("invoice_items", lambda consulta: consulta.in_("invoice_id", ids_facturas))
        )

    resultado = []
    for tabla, filtro in objetivos:
        for fila, faltan in _pendientes_en_tabla(tabla, CAMPOS_TRADUCIBLES[tabla], filtro):
            resultado.append((tabla, fila, faltan))
    return resultado


def traducir_pendientes(campaign_id: str) -> tuple[int, int]:
    """Traduce y guarda lo que haya quedado sin inglés.

    Devuelve (campos traducidos, campos que siguen pendientes). Los que siguen
    pendientes son aquellos donde el traductor volvió a fallar: se dejan vacíos
    a propósito, para poder reintentarlos más adelante."""
    traducidos = 0
    fallidos = 0
    for tabla, fila, campos in textos_sin_traducir(campaign_id):
        nuevos = {}
        for campo in campos:
            traducido = translate_to_english(fila.get(campo))
            if traducido:
                nuevos[f"{campo}_en"] = traducido
            else:
                fallidos += 1
        if nuevos:
            get_admin_client().table(tabla).update(nuevos).eq("id", fila["id"]).execute()
            traducidos += len(nuevos)
    return traducidos, fallidos


# La tabla operators sólo existe después de correr migration_operadores.sql.
# Igual que con donation_info, el código no puede exigir que la migración vaya
# primero: entre que se despliega esto y que alguien corre el SQL hay una
# ventana en la que la tabla no está, y dejar al operador afuera de su propio
# panel en esa ventana sería peor que aceptar el esquema viejo un rato más.
OPERATORS_TABLE_MISSING = "operators_table_missing"


def _looks_like_missing_operators_table(error: Exception) -> bool:
    mensaje = str(error).lower()
    if "operators" not in mensaje:
        return False
    return any(
        pista in mensaje
        for pista in ("does not exist", "schema cache", "pgrst205", "relation")
    )


def verify_operator_login(username: str, password: str):
    """True/False según las credenciales del operador del sitio.

    Devuelve OPERATORS_TABLE_MISSING si la tabla todavía no existe, para que la
    vista sepa que tiene que caer al esquema viejo de sólo ADMIN_PASSWORD en vez
    de mostrar 'usuario o contraseña incorrectos' sobre una tabla que no está."""
    try:
        response = (
            get_admin_client()
            .table("operators")
            .select("username,password_hash,is_active")
            .eq("username", username.strip().lower())
            .execute()
        )
    except Exception as error:
        if _looks_like_missing_operators_table(error):
            return OPERATORS_TABLE_MISSING
        raise

    if not response.data:
        return False
    operator = response.data[0]
    if not operator["is_active"]:
        return False
    return bcrypt.checkpw(password.encode(), operator["password_hash"].encode())


def create_campaign(
    slug: str,
    name: str,
    username: str,
    password: str,
) -> dict:
    """El operador crea la campaña y le da acceso; nada más. La descripción, los
    datos para aportar y la foto los escribe la campaña desde su propio panel."""
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    payload = {
        "slug": slug.strip().lower(),
        "name": name,
        "username": username.strip().lower(),
        "password_hash": password_hash,
    }
    response = get_admin_client().table("campaigns").insert(payload).execute()
    return response.data[0]


def upload_campaign_photo(
    campaign_id: str,
    campaign_slug: str,
    file_bytes: bytes,
    original_filename: str,
    content_type: str,
) -> str:
    """Foto de perfil de quien lidera la campaña. Va al mismo bucket que las
    evidencias pero bajo un prefijo propio, para no mezclarse con las fotos de
    entregas. Devuelve la URL pública ya guardada en la campaña."""
    client = get_admin_client()
    previous = _campaign_photo_url(campaign_id)

    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"
    storage_path = f"perfiles/{campaign_slug}/{uuid4()}.{extension}"

    client.storage.from_(GALLERY_BUCKET).upload(
        storage_path, file_bytes, {"content-type": content_type}
    )
    photo_url = client.storage.from_(GALLERY_BUCKET).get_public_url(storage_path)
    update_campaign(campaign_id, photo_url=photo_url)
    # La anterior ya no la referencia nadie: se limpia recién ahora, con la
    # nueva URL guardada, para no quedarse sin foto si algo falla en el medio.
    _remove_storage_object(previous)
    return photo_url


def _campaign_photo_url(campaign_id: str) -> str | None:
    rows = (
        get_admin_client().table("campaigns").select("photo_url").eq("id", campaign_id).execute().data
    )
    return rows[0].get("photo_url") if rows else None


def remove_campaign_photo(campaign_id: str) -> None:
    """Quita la foto de la campaña y borra el archivo. Igual que en la galería,
    la referencia se limpia primero y el archivo después."""
    previous = _campaign_photo_url(campaign_id)
    update_campaign(campaign_id, photo_url=None)
    _remove_storage_object(previous)


def update_campaign(campaign_id: str, **fields) -> dict:
    if "password" in fields:
        password = fields.pop("password")
        fields["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    if "username" in fields:
        fields["username"] = fields["username"].strip().lower()
    if "slug" in fields:
        fields["slug"] = fields["slug"].strip().lower()
    return _update_traducido(
        "campaigns", fields, lambda consulta: consulta.eq("id", campaign_id)
    ).data[0]


# ---------------------------------------------------------------------------
# Donations (anonymous — no donor name or personal data is ever stored)
# ---------------------------------------------------------------------------

def create_donation(campaign_id: str, amount: float, donation_date: date = None, notes: str = None) -> dict:
    payload = {
        "campaign_id": campaign_id,
        "amount": amount,
        "donation_date": (donation_date or date.today()).isoformat(),
        "notes": notes,
    }
    return _insert_traducido("donations", payload)


def get_donations(campaign_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    response = (
        get_client()
        .table("donations")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("donation_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data


def get_donation(donation_id: str) -> dict | None:
    response = get_client().table("donations").select("*").eq("id", donation_id).execute()
    return response.data[0] if response.data else None


def update_donation(donation_id: str, campaign_id: str, **fields) -> dict:
    """campaign_id scopes the update so a logged-in campaign can never touch
    another campaign's row (RLS doesn't help here since this runs on the
    service_role client — the .eq("campaign_id", ...) filter IS the check)."""
    response = _update_traducido(
        "donations",
        fields,
        lambda consulta: consulta.eq("id", donation_id).eq("campaign_id", campaign_id),
    )
    if not response.data:
        raise PermissionError("Donación no encontrada para esta campaña.")
    return response.data[0]


def delete_donation(donation_id: str, campaign_id: str) -> None:
    get_admin_client().table("donations").delete().eq("id", donation_id).eq("campaign_id", campaign_id).execute()


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

def create_invoice(
    campaign_id: str,
    merchant: str,
    invoice_number: str = None,
    invoice_date: date = None,
    notes: str = None,
) -> dict:
    payload = {
        "campaign_id": campaign_id,
        "merchant": merchant,
        "invoice_number": invoice_number,
        "invoice_date": (invoice_date or date.today()).isoformat(),
        "notes": notes,
    }
    return _insert_traducido("invoices", payload)


def get_invoices(campaign_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    response = (
        get_client()
        .table("invoices")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("invoice_date", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data


def get_invoices_with_items(campaign_id: str, limit: int = 1000) -> list[dict]:
    """Facturas con sus artículos anidados, en UNA sola consulta (embed sobre
    la FK invoice_items -> invoices).

    Existe para poder etiquetar una factura con su monto y sus artículos sin
    disparar una consulta por factura: hay varias del mismo comercio en la misma
    fecha, y sin el monto son indistinguibles al elegirla."""
    response = (
        get_client()
        .table("invoices")
        .select("id,merchant,invoice_number,invoice_date,notes,invoice_items(item_name,quantity,total_price)")
        .eq("campaign_id", campaign_id)
        .order("invoice_date", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def create_invoice_with_items(
    campaign_id: str,
    merchant: str,
    items: list[dict],
    invoice_number: str = None,
    invoice_date: date = None,
    notes: str = None,
) -> dict:
    """Insert the invoice and all of its items atomically via the
    create_invoice_with_items Postgres RPC (see schema.sql), so a failed item
    never leaves an invoice with a partial item list.

    items: list of {"item_name", "quantity", "unit_price", "category"?, "tax_amount"?}
    """
    payload = {
        "p_campaign_id": campaign_id,
        "p_merchant": merchant,
        "p_invoice_number": invoice_number,
        "p_invoice_date": (invoice_date or date.today()).isoformat(),
        "p_notes": notes,
        "p_items": [
            {
                "item_name": item["item_name"],
                "category": item.get("category"),
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "tax_amount": item.get("tax_amount", 0),
            }
            for item in items
        ],
    }
    response = get_admin_client().rpc("create_invoice_with_items", payload).execute()
    _traducir_factura_creada(response.data)
    return response.data


def _traducir_factura_creada(resultado: dict) -> None:
    """Completa las columnas en inglés después de que la RPC guardó la factura.

    Va después y no adentro a propósito: la RPC es la que garantiza que una
    factura nunca quede a medias, y meterle una llamada de red a un servicio de
    traducción sería poner el registro contable a merced de que ese servicio
    ande. Si esto falla, la factura ya está guardada y el tablero la traduce en
    vivo al mostrarla."""
    if not resultado:
        return
    try:
        factura = resultado.get("invoice") or {}
        campos = {
            campo: factura.get(campo)
            for campo in CAMPOS_TRADUCIBLES["invoices"]
            if factura.get(campo)
        }
        if campos and factura.get("id"):
            _update_traducido(
                "invoices", campos, lambda consulta: consulta.eq("id", factura["id"])
            )

        for item in resultado.get("items") or []:
            campos_item = {
                campo: item.get(campo)
                for campo in CAMPOS_TRADUCIBLES["invoice_items"]
                if item.get(campo)
            }
            if campos_item and item.get("id"):
                _update_traducido(
                    "invoice_items", campos_item, lambda consulta, _id=item["id"]: consulta.eq("id", _id)
                )
    except Exception:
        pass


def get_invoice(invoice_id: str) -> dict | None:
    response = get_client().table("invoices").select("*").eq("id", invoice_id).execute()
    return response.data[0] if response.data else None


def update_invoice(invoice_id: str, campaign_id: str, **fields) -> dict:
    response = _update_traducido(
        "invoices",
        fields,
        lambda consulta: consulta.eq("id", invoice_id).eq("campaign_id", campaign_id),
    )
    if not response.data:
        raise PermissionError("Factura no encontrada para esta campaña.")
    return response.data[0]


def delete_invoice(invoice_id: str, campaign_id: str) -> None:
    # invoice_items has "on delete cascade" on invoice_id, so its rows go with it.
    get_admin_client().table("invoices").delete().eq("id", invoice_id).eq("campaign_id", campaign_id).execute()


# ---------------------------------------------------------------------------
# Invoice items (total_price is computed by Postgres, never sent on write)
# ---------------------------------------------------------------------------

def _invoice_owned_by_campaign(invoice_id: str, campaign_id: str) -> bool:
    response = (
        get_admin_client()
        .table("invoices")
        .select("id")
        .eq("id", invoice_id)
        .eq("campaign_id", campaign_id)
        .execute()
    )
    return bool(response.data)


def create_invoice_item(
    invoice_id: str,
    campaign_id: str,
    item_name: str,
    quantity: float,
    unit_price: float,
    category: str = None,
    tax_amount: float = 0,
) -> dict:
    if not _invoice_owned_by_campaign(invoice_id, campaign_id):
        raise PermissionError("Factura no encontrada para esta campaña.")
    payload = {
        "invoice_id": invoice_id,
        "item_name": item_name,
        "category": category,
        "quantity": quantity,
        "unit_price": unit_price,
        "tax_amount": tax_amount,
    }
    return _insert_traducido("invoice_items", payload)


def get_invoice_items(invoice_id: str) -> list[dict]:
    response = (
        get_client()
        .table("invoice_items")
        .select("*")
        .eq("invoice_id", invoice_id)
        .order("id")
        .execute()
    )
    return response.data


def get_used_categories(campaign_id: str) -> list[str]:
    """Distinct categories this campaign has actually used, in one round trip.

    invoice_items has no campaign_id of its own (it is scoped through its
    invoice), so this rides the FK with an inner embed instead of fetching
    every invoice and then its items."""
    response = (
        get_client()
        .table("invoice_items")
        .select("category, invoices!inner(campaign_id)")
        .eq("invoices.campaign_id", campaign_id)
        .execute()
    )
    return sorted({row["category"] for row in response.data if row.get("category")})


def get_invoice_item(item_id: str) -> dict | None:
    response = get_client().table("invoice_items").select("*").eq("id", item_id).execute()
    return response.data[0] if response.data else None


def _item_owned_by_campaign(item_id: str, campaign_id: str) -> bool:
    item = get_invoice_item(item_id)
    return item is not None and _invoice_owned_by_campaign(item["invoice_id"], campaign_id)


def update_invoice_item(item_id: str, campaign_id: str, **fields) -> dict:
    if not _item_owned_by_campaign(item_id, campaign_id):
        raise PermissionError("Ítem no encontrado para esta campaña.")
    fields.pop("total_price", None)
    return _update_traducido(
        "invoice_items", fields, lambda consulta: consulta.eq("id", item_id)
    ).data[0]


def delete_invoice_item(item_id: str, campaign_id: str) -> None:
    if not _item_owned_by_campaign(item_id, campaign_id):
        raise PermissionError("Ítem no encontrado para esta campaña.")
    get_admin_client().table("invoice_items").delete().eq("id", item_id).execute()


# ---------------------------------------------------------------------------
# Gallery photos
# ---------------------------------------------------------------------------

def create_gallery_photo(
    campaign_id: str,
    title: str,
    photo_url: str,
    description: str = None,
    invoice_id: str = None,
) -> dict:
    """invoice_id is optional: a photo can back a specific purchase, or just be
    general evidence of a delivery (see migration_evidencia_facturas.sql)."""
    payload = {
        "campaign_id": campaign_id,
        "title": title,
        "description": description,
        "photo_url": photo_url,
        "invoice_id": invoice_id,
    }
    return _insert_traducido("gallery_photos", payload)


def upload_gallery_photo(
    campaign_id: str,
    campaign_slug: str,
    file_bytes: bytes,
    original_filename: str,
    content_type: str,
    title: str,
    description: str = None,
    invoice_id: str = None,
) -> dict:
    if invoice_id and not _invoice_owned_by_campaign(invoice_id, campaign_id):
        raise PermissionError("Factura no encontrada para esta campaña.")

    client = get_admin_client()
    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"
    storage_path = f"{campaign_slug}/{uuid4()}.{extension}"

    client.storage.from_(GALLERY_BUCKET).upload(
        storage_path, file_bytes, {"content-type": content_type}
    )
    photo_url = client.storage.from_(GALLERY_BUCKET).get_public_url(storage_path)

    return create_gallery_photo(
        campaign_id=campaign_id,
        title=title,
        photo_url=photo_url,
        description=description,
        invoice_id=invoice_id,
    )


def get_gallery_photos(campaign_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    response = (
        get_client()
        .table("gallery_photos")
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data


def get_gallery_photo(photo_id: str) -> dict | None:
    response = get_client().table("gallery_photos").select("*").eq("id", photo_id).execute()
    return response.data[0] if response.data else None


def _storage_path_from_url(photo_url: str) -> str | None:
    """La ruta dentro del bucket, sacada de la URL pública.

    get_public_url devuelve algo como
    .../storage/v1/object/public/evidencias/<ruta>?<query>, así que la ruta es
    lo que va después del nombre del bucket y antes de la query."""
    if not photo_url:
        return None
    marker = f"/{GALLERY_BUCKET}/"
    if marker not in photo_url:
        return None
    return photo_url.split(marker, 1)[1].split("?")[0] or None


def _remove_storage_object(photo_url: str) -> None:
    """Borra el archivo del bucket.

    No propaga errores a propósito: esto siempre corre DESPUÉS de haber borrado
    la fila, y a esa altura el borrado ya es un hecho para el usuario. Si el
    archivo no se puede eliminar (ya no existe, permiso, red), lo peor que queda
    es un huérfano invisible que no afecta al tablero."""
    path = _storage_path_from_url(photo_url)
    if not path:
        return
    try:
        get_admin_client().storage.from_(GALLERY_BUCKET).remove([path])
    except Exception:
        pass


def update_gallery_photo(photo_id: str, campaign_id: str, **fields) -> dict:
    """campaign_id acota la escritura a la campaña dueña. Igual que en el resto
    de los update/delete: corre con la llave service_role, así que la RLS no
    protege nada acá — el filtro ES la comprobación."""
    if "invoice_id" in fields and fields["invoice_id"]:
        if not _invoice_owned_by_campaign(fields["invoice_id"], campaign_id):
            raise PermissionError("Factura no encontrada para esta campaña.")
    response = _update_traducido(
        "gallery_photos",
        fields,
        lambda consulta: consulta.eq("id", photo_id).eq("campaign_id", campaign_id),
    )
    if not response.data:
        raise PermissionError("Evidencia no encontrada para esta campaña.")
    return response.data[0]


def delete_gallery_photo(photo_id: str, campaign_id: str) -> None:
    """Borra la fila y también el archivo del bucket.

    El orden importa: la fila va PRIMERO. Si fallara el borrado del archivo
    queda un huérfano inofensivo; al revés, un archivo borrado con la fila viva
    dejaría una foto rota a la vista de todos en el tablero público."""
    rows = (
        get_admin_client()
        .table("gallery_photos")
        .select("photo_url")
        .eq("id", photo_id)
        .eq("campaign_id", campaign_id)
        .execute()
        .data
    )
    if not rows:
        return  # no existe o es de otra campaña: no hay nada que borrar

    get_admin_client().table("gallery_photos").delete().eq("id", photo_id).eq(
        "campaign_id", campaign_id
    ).execute()
    _remove_storage_object(rows[0]["photo_url"])
