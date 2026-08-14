-- Migración a multi-campaña para una base de datos que YA tiene datos
-- (donaciones/facturas/fotos existentes de una sola campaña implícita).
-- Ejecutar una sola vez en el SQL Editor de Supabase, de arriba hacia abajo.
--
-- ANTES DE CORRER: reemplazá los 4 valores marcados <...> en el bloque
-- "do $$ ... $$" más abajo (slug, nombre, usuario, contraseña temporal).
-- La contraseña es solo temporal — cambiala desde /admin-campanas apenas
-- termine la migración.

create table campaigns (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique check (slug ~ '^[a-z0-9-]+$'),
    name text not null,
    description text,
    username text not null unique,
    password_hash text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

alter table campaigns enable row level security;
-- Sin policy de select para anon/authenticated: nadie puede leer esta tabla
-- salvo el cliente admin (service_role) desde el backend de la app.

alter table donations add column campaign_id uuid references campaigns(id);
alter table invoices add column campaign_id uuid references campaigns(id);
alter table gallery_photos add column campaign_id uuid references campaigns(id);

-- Crea la primera campaña con los datos existentes y migra todo hacia ella.
do $$
declare v_campaign_id uuid;
begin
    insert into campaigns (slug, name, username, password_hash, is_active)
    values (
        '<tu-slug>',            -- ej: 'maria-perez' (solo minúsculas, números y guiones)
        '<Tu Nombre>',           -- ej: 'María Pérez'
        '<tu-usuario>',          -- ej: 'maria'
        crypt('<CONTRASENA_TEMPORAL>', gen_salt('bf', 12)),
        true
    )
    returning id into v_campaign_id;

    update donations set campaign_id = v_campaign_id where campaign_id is null;
    update invoices set campaign_id = v_campaign_id where campaign_id is null;
    update gallery_photos set campaign_id = v_campaign_id where campaign_id is null;
end $$;

alter table donations alter column campaign_id set not null;
alter table invoices alter column campaign_id set not null;
alter table gallery_photos alter column campaign_id set not null;

create index donations_campaign_id_idx on donations(campaign_id);
create index invoices_campaign_id_idx on invoices(campaign_id);
create index gallery_photos_campaign_id_idx on gallery_photos(campaign_id);

-- create_invoice_with_items cambia de firma (nuevo parámetro p_campaign_id),
-- así que hay que borrar la versión vieja explícitamente: "create or replace"
-- NO reemplaza una función cuando cambian los tipos/cantidad de argumentos,
-- dejaría las dos versiones conviviendo.
drop function if exists create_invoice_with_items(text, jsonb, text, date, text);

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

revoke execute on function create_invoice_with_items(uuid, text, jsonb, text, date, text) from public, anon, authenticated;
grant execute on function create_invoice_with_items(uuid, text, jsonb, text, date, text) to service_role;

-- Evita el error PGRST202 (schema cache desactualizado) que ya vimos antes
-- al agregar/cambiar una función RPC.
notify pgrst, 'reload schema';
