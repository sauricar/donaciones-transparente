-- Versión en inglés de todo el texto que escriben las campañas.
--
-- Por qué en columnas y no traduciendo al vuelo: el texto libre de una campaña
-- (el nombre de un artículo, la nota de una factura, el pie de una foto) no se
-- puede anticipar en un diccionario, pero tampoco cambia casi nunca una vez
-- cargado. Traducirlo una sola vez al guardarlo y dejarlo acá significa que el
-- donante que lee en inglés no espera a ningún servicio externo, y que el
-- tablero sigue mostrando todo aunque ese servicio esté caído.
--
-- Todas las columnas son opcionales. Mientras estén vacías, la app traduce en
-- vivo como respaldo, así que lo que ya estaba cargado antes de esta migración
-- se sigue viendo en inglés sin necesidad de tocar nada.
--
-- Ejecutar una sola vez en el SQL Editor de Supabase. Es idempotente.

alter table campaigns      add column if not exists description_en   text;
alter table campaigns      add column if not exists donation_info_en text;

alter table donations      add column if not exists notes_en         text;

alter table invoices       add column if not exists notes_en         text;
alter table invoices       add column if not exists merchant_en      text;

alter table invoice_items  add column if not exists item_name_en     text;
alter table invoice_items  add column if not exists category_en      text;

alter table gallery_photos add column if not exists title_en         text;
alter table gallery_photos add column if not exists description_en   text;

-- Supabase cachea el esquema en PostgREST: sin esto las columnas recién
-- creadas tardan en ser visibles para la app.
notify pgrst, 'reload schema';
