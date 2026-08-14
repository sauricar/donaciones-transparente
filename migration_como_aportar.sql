-- Banner de campaña: datos para aportar + foto de quien lidera la actividad.
--
--   donation_info : texto libre (Nequi, Daviplata, cuenta, contacto). Se muestra
--                   en un banner destacado arriba del tablero, con botón de copiar.
--   photo_url     : foto de perfil de la persona a cargo, para ponerle cara a la
--                   campaña. Se sube desde /admin-campanas al bucket "evidencias".
--
-- Ambas columnas son opcionales: si quedan vacías, el banner no aparece.
-- Ejecutar una sola vez en el SQL Editor de Supabase. Es idempotente, así que
-- no pasa nada si ya corriste una versión anterior de este archivo.

alter table campaigns add column if not exists donation_info text;
alter table campaigns add column if not exists photo_url text;

notify pgrst, 'reload schema';
