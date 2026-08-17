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

GALLERY_BUCKET = "evidencias"
CAMPAIGN_BASE_COLUMNS = "id,slug,name,description,is_active,created_at"
CAMPAIGN_PUBLIC_COLUMNS = CAMPAIGN_BASE_COLUMNS + ",donation_info,photo_url"

# donation_info y photo_url sólo existen después de correr
# migration_como_aportar.sql. El código no puede exigir que la migración vaya
# primero: si las columnas todavía no están, se degrada a las columnas base y
# el banner simplemente no aparece, en vez de tumbar todo el tablero.
_campaign_columns = CAMPAIGN_PUBLIC_COLUMNS


def _campaign_rows(build):
    """build recibe la lista de columnas y devuelve la consulta ya armada."""
    global _campaign_columns
    try:
        return build(_campaign_columns).execute().data
    except Exception:
        if _campaign_columns == CAMPAIGN_BASE_COLUMNS:
            raise  # no era la columna faltante: es un error real
        _campaign_columns = CAMPAIGN_BASE_COLUMNS
        return build(_campaign_columns).execute().data


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
    return get_admin_client().table("campaigns").update(fields).eq("id", campaign_id).execute().data[0]


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
    return get_admin_client().table("donations").insert(payload).execute().data[0]


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
    response = (
        get_admin_client()
        .table("donations")
        .update(fields)
        .eq("id", donation_id)
        .eq("campaign_id", campaign_id)
        .execute()
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
    return get_admin_client().table("invoices").insert(payload).execute().data[0]


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
    return response.data


def get_invoice(invoice_id: str) -> dict | None:
    response = get_client().table("invoices").select("*").eq("id", invoice_id).execute()
    return response.data[0] if response.data else None


def update_invoice(invoice_id: str, campaign_id: str, **fields) -> dict:
    response = (
        get_admin_client()
        .table("invoices")
        .update(fields)
        .eq("id", invoice_id)
        .eq("campaign_id", campaign_id)
        .execute()
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
    return get_admin_client().table("invoice_items").insert(payload).execute().data[0]


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
    return get_admin_client().table("invoice_items").update(fields).eq("id", item_id).execute().data[0]


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
    return get_admin_client().table("gallery_photos").insert(payload).execute().data[0]


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
    response = (
        get_admin_client()
        .table("gallery_photos")
        .update(fields)
        .eq("id", photo_id)
        .eq("campaign_id", campaign_id)
        .execute()
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
