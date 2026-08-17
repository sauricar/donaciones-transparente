-- Usuario y contraseña para el operador del sitio.
--
-- Hasta ahora /admin-campanas se abría sólo con una contraseña suelta (el
-- secreto ADMIN_PASSWORD, herencia de cuando había una sola campaña). Esta
-- migración le da al operador el mismo esquema de credenciales que ya tienen
-- las campañas: usuario único + hash bcrypt, nunca la contraseña en claro.
--
-- ANTES DE CORRER: reemplazá los dos valores marcados <...> en el insert.
-- Ejecutar una sola vez en el SQL Editor de Supabase. Es idempotente: si ya
-- corriste este archivo, volver a correrlo no duplica ni pisa nada.
--
-- Mientras esta tabla no exista, la app sigue andando con ADMIN_PASSWORD y
-- ese usuario que escribas se ignora — así el deploy no deja al operador
-- afuera de su propio panel si la migración se corre unos minutos después.
-- En cuanto la tabla existe, ADMIN_PASSWORD deja de servir para entrar.

create extension if not exists pgcrypto;

create table if not exists operators (
    id uuid primary key default gen_random_uuid(),
    username text not null unique,
    password_hash text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

-- Igual que campaigns: esta tabla guarda hashes de contraseña, así que va con
-- RLS activo y SIN policy de select. Nadie la lee con la clave anon; sólo el
-- cliente service_role del backend, que nunca llega al navegador.
alter table operators enable row level security;

insert into operators (username, password_hash)
values (
    lower('<tu-usuario>'),                        -- ej: 'santiago'
    crypt('<TU_CONTRASENA>', gen_salt('bf', 12))  -- se guarda hasheada, no en claro
)
on conflict (username) do nothing;

-- Supabase cachea el esquema en PostgREST: sin esto la tabla recién creada
-- tarda en ser visible para la app.
notify pgrst, 'reload schema';
