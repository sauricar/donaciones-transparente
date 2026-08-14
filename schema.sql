-- ############################################################################
-- OJO: este archivo describe un montaje LIMPIO desde cero. La base de datos
-- que está en producción hoy NO coincide con él: sus tablas se crearon desde
-- la interfaz de Supabase, así que al menos invoices.id (y por lo tanto
-- invoice_items.invoice_id) es bigint, no uuid como se declara acá.
--
-- Por eso cualquier migración sobre la base existente debe detectar el tipo
-- real en vez de asumirlo — ver migration_evidencia_facturas.sql, que falló
-- justamente por asumir uuid. Usá este archivo como referencia del modelo,
-- no como descripción fiel de la base actual.
-- ############################################################################

-- Transparency app schema for Supabase (Postgres).
-- donations intentionally has no donor name or personal data columns.
-- Multi-tenant: every donation/invoice/gallery_photos row belongs to exactly
-- one campaign (one person/org being tracked, with its own login).

create extension if not exists pgcrypto;

-- donation_info: texto libre con los datos para recibir aportes (Nequi, cuenta,
-- contacto). photo_url: foto de quien lidera la campaña. Ambos opcionales; si
-- están vacíos, el banner del tablero público no aparece.
create table campaigns (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique check (slug ~ '^[a-z0-9-]+$'),
    name text not null,
    description text,
    donation_info text,
    photo_url text,
    username text not null unique,
    password_hash text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table donations (
    id uuid primary key default gen_random_uuid(),
    campaign_id uuid not null references campaigns(id),
    amount numeric not null check (amount > 0),
    donation_date date not null default current_date,
    notes text,
    created_at timestamptz not null default now()
);

create table invoices (
    id uuid primary key default gen_random_uuid(),
    campaign_id uuid not null references campaigns(id),
    merchant text not null,
    invoice_number text,
    invoice_date date not null default current_date,
    notes text,
    created_at timestamptz not null default now()
);

create table invoice_items (
    id uuid primary key default gen_random_uuid(),
    invoice_id uuid not null references invoices(id) on delete cascade,
    item_name text not null,
    category text,
    quantity numeric not null default 1 check (quantity >= 0),
    unit_price numeric not null default 0 check (unit_price >= 0),
    tax_amount numeric not null default 0 check (tax_amount >= 0),
    total_price numeric generated always as ((quantity * unit_price) + tax_amount) stored
);

-- invoice_id is optional: a photo can back a specific purchase, or just be
-- general evidence of a delivery. "on delete set null" keeps the photo in the
-- gallery when its invoice is deleted — it only loses the link.
create table gallery_photos (
    id uuid primary key default gen_random_uuid(),
    campaign_id uuid not null references campaigns(id),
    invoice_id uuid references invoices(id) on delete set null,
    title text not null,
    description text,
    photo_url text not null,
    created_at timestamptz not null default now()
);

create index invoice_items_invoice_id_idx on invoice_items(invoice_id);
create index donations_donation_date_idx on donations(donation_date);
create index invoices_invoice_date_idx on invoices(invoice_date);
create index donations_campaign_id_idx on donations(campaign_id);
create index invoices_campaign_id_idx on invoices(campaign_id);
create index gallery_photos_campaign_id_idx on gallery_photos(campaign_id);
create index gallery_photos_invoice_id_idx on gallery_photos(invoice_id);

-- Row Level Security: this is a public transparency site, so donations/
-- invoices/invoice_items/gallery_photos are readable by anyone (anon +
-- authenticated) — the app filters by campaign_id per query. No insert/
-- update/delete policy is defined for anon/authenticated on any table —
-- writes are only possible with the service_role key, which bypasses RLS by
-- design and is never sent to the browser (database.py's get_admin_client()
-- is the only caller that uses it, gated behind a per-campaign username/
-- password check or the operator password).
--
-- campaigns is different: it holds password_hash, so it gets RLS enabled
-- with NO select policy at all for anon/authenticated — nothing is readable
-- through the anon key, full stop. Only the service_role client can read it,
-- and database.py always explicitly allowlists safe columns when returning
-- campaign data to callers.
alter table campaigns enable row level security;
alter table donations enable row level security;
alter table invoices enable row level security;
alter table invoice_items enable row level security;
alter table gallery_photos enable row level security;

create policy "public can read donations" on donations
    for select to anon, authenticated using (true);

create policy "public can read invoices" on invoices
    for select to anon, authenticated using (true);

create policy "public can read invoice_items" on invoice_items
    for select to anon, authenticated using (true);

create policy "public can read gallery_photos" on gallery_photos
    for select to anon, authenticated using (true);

-- Atomically inserts an invoice and all of its items in one transaction.
-- A plpgsql function body runs as a single statement in the caller's transaction:
-- any exception raised (e.g. a check constraint violation on one item) rolls back
-- the invoice insert and every item insert that already ran in this same call.
create or replace function create_invoice_with_items(
    p_campaign_id uuid,
    p_merchant text,
    p_items jsonb,
    p_invoice_number text default null,
    p_invoice_date date default current_date,
    p_notes text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_invoice invoices;
    v_item jsonb;
begin
    if p_items is null or jsonb_array_length(p_items) = 0 then
        raise exception 'p_items must contain at least one item';
    end if;

    insert into invoices (campaign_id, merchant, invoice_number, invoice_date, notes)
    values (p_campaign_id, p_merchant, p_invoice_number, coalesce(p_invoice_date, current_date), p_notes)
    returning * into v_invoice;

    for v_item in select * from jsonb_array_elements(p_items)
    loop
        insert into invoice_items (invoice_id, item_name, category, quantity, unit_price, tax_amount)
        values (
            v_invoice.id,
            v_item->>'item_name',
            v_item->>'category',
            (v_item->>'quantity')::numeric,
            (v_item->>'unit_price')::numeric,
            coalesce((v_item->>'tax_amount')::numeric, 0)
        );
    end loop;

    return jsonb_build_object(
        'invoice', to_jsonb(v_invoice),
        'items', (select jsonb_agg(to_jsonb(ii)) from invoice_items ii where ii.invoice_id = v_invoice.id)
    );
end;
$$;

-- security definer bypasses RLS, so this must NOT be callable by anon/authenticated —
-- only the service_role key (used server-side by database.py's admin client) can call it.
revoke execute on function create_invoice_with_items(uuid, text, jsonb, text, date, text) from public, anon, authenticated;
grant execute on function create_invoice_with_items(uuid, text, jsonb, text, date, text) to service_role;
