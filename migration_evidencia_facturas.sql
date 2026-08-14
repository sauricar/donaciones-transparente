-- Vincula cada foto de evidencia (opcionalmente) con la factura que respalda.
-- Ejecutar una sola vez en el SQL Editor de Supabase.
--
-- Esta versión NO asume el tipo de invoices.id: lo detecta y crea
-- gallery_photos.invoice_id con exactamente el mismo tipo. (La versión anterior
-- asumía uuid y falló con "incompatible types: uuid and bigint", porque las
-- tablas de esta base se crearon con id bigint, no uuid.)
--
-- La columna queda NULLABLE a propósito: una foto puede ser evidencia general
-- (una entrega, una jornada) sin corresponder a una compra puntual.
-- "on delete set null" hace que borrar una factura no borre la foto: la foto
-- sobrevive en la galería, solo pierde el vínculo.
--
-- Es idempotente: si algo ya existe, lo salta en vez de fallar.

do $$
declare
    v_type text;
begin
    select format_type(a.atttypid, a.atttypmod)
      into v_type
      from pg_attribute a
     where a.attrelid = 'public.invoices'::regclass
       and a.attname  = 'id'
       and a.attnum   > 0
       and not a.attisdropped;

    if v_type is null then
        raise exception 'No se encontró la columna public.invoices.id';
    end if;

    -- 1. La columna, con el tipo que realmente tiene invoices.id
    if not exists (
        select 1 from pg_attribute
         where attrelid = 'public.gallery_photos'::regclass
           and attname  = 'invoice_id'
           and attnum   > 0
           and not attisdropped
    ) then
        execute format('alter table public.gallery_photos add column invoice_id %s', v_type);
        raise notice 'Columna gallery_photos.invoice_id creada con tipo %', v_type;
    else
        raise notice 'La columna gallery_photos.invoice_id ya existía; no se toca.';
    end if;

    -- 2. La llave foránea
    if not exists (
        select 1 from pg_constraint
         where conrelid = 'public.gallery_photos'::regclass
           and conname  = 'gallery_photos_invoice_id_fkey'
    ) then
        execute 'alter table public.gallery_photos
                   add constraint gallery_photos_invoice_id_fkey
                   foreign key (invoice_id) references public.invoices(id)
                   on delete set null';
        raise notice 'Llave foránea creada.';
    end if;
end $$;

create index if not exists gallery_photos_invoice_id_idx on public.gallery_photos(invoice_id);

notify pgrst, 'reload schema';

-- ---------------------------------------------------------------------------
-- DIAGNÓSTICO (opcional): mostrame este resultado para saber cómo es tu base
-- realmente, porque schema.sql del repo no coincide con ella.
-- ---------------------------------------------------------------------------
select table_name, column_name, data_type
  from information_schema.columns
 where table_schema = 'public'
   and table_name in ('campaigns', 'donations', 'invoices', 'invoice_items', 'gallery_photos')
   and (column_name = 'id' or column_name like '%\_id')
 order by table_name, column_name;
