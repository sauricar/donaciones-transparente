# Tablero de Transparencia de Donaciones

Aplicación web para que una persona que recibió donaciones pueda mostrar,
peso por peso, en qué las convirtió: cuánto entró, qué se compró, con qué
factura y con qué foto de la entrega.

Nació para dar cuentas de las donaciones recibidas tras el terremoto que
afectó a Colombia, y está hecha para que **varias personas** puedan usarla:
cada una tiene su propia campaña, su propio enlace público y sus propias
credenciales.

📘 **¿Vas a administrar una instalación (propia o de otra persona)?** Empezá
por el [**Manual del administrador**](MANUAL_ADMINISTRADOR.md) — cómo crear
campañas, cargar donaciones, facturas y evidencias, y desplegar tu propia
copia desde cero.

## Qué muestra

- **Cuánto se recibió y cuánto se ejecutó**, con el porcentaje ya convertido en ayuda.
- **En qué se convirtió**: los artículos comprados y entregados, por cantidad.
- **El ritmo día por día**: aportes recibidos frente a gastos, cantidad de
  aportes, artículos comprados.
- **Facturas** con su detalle de artículos y las fotos que respaldan cada compra.
- **Qué logró tu aporte**: dado un monto, una combinación equivalente de cosas
  que ya se compraron — sin inventar cantidades que no existieron.

## Estructura

| Ruta | Qué es |
|---|---|
| `/inicio` | Directorio de campañas |
| `/campana?c=<slug>` | Tablero público de una campaña (este es el enlace para compartir) |
| `/panel-de-gestion` | Panel de cada campaña: cargar donaciones, facturas y evidencias, y editar cómo se presenta |
| `/admin-campanas` | Panel del operador: crear campañas y dar los accesos |

```
app.py              Navegación y registro de páginas
database.py         Acceso a Supabase (lecturas con anon key, escrituras con service_role)
views/theme.py      Paleta, formatos y tema de gráficas
views/*.py          Una vista por pantalla
schema.sql          Esquema de referencia para una instalación nueva
migration_*.sql     Migraciones sobre una base existente, en orden
```

## Puesta en marcha

Versión rápida para correrlo en local — la guía completa para desplegarlo
(incluyendo Streamlit Community Cloud) está en el
[Manual del administrador, sección 1](MANUAL_ADMINISTRADOR.md#1-antes-de-empezar-tenés-instancia-propia-o-vas-a-usar-una-copia).

1. Crear un proyecto en [Supabase](https://supabase.com) y ejecutar `schema.sql`
   en el SQL Editor. Sobre una base que ya tenga datos, correr en cambio las
   `migration_*.sql` en orden.
2. Crear un bucket de Storage **público** llamado `evidencias`.
3. Configurar los secretos (ver abajo).
4. `pip install -r requirements.txt` y `streamlit run app.py`.

### Secretos

**Nunca se versionan.** En local van en `.streamlit/secrets.toml` (ignorado por
git); en Streamlit Cloud, en *Settings → Secrets*:

```toml
SUPABASE_URL = "https://<proyecto>.supabase.co"
SUPABASE_KEY = "<clave anon / publishable>"
SUPABASE_SERVICE_KEY = "<clave service_role>"
ADMIN_PASSWORD = "<contraseña de respaldo del operador>"
```

`SUPABASE_SERVICE_KEY` salta las políticas de seguridad de la base por diseño.
Sólo se usa del lado del servidor y nunca llega al navegador — pero por eso
mismo no debe salir de ahí.

El operador entra con **usuario y contraseña**, guardados en la tabla
`operators` (`migration_operadores.sql`). `ADMIN_PASSWORD` queda como acceso de
respaldo mientras esa migración no se haya corrido.

## Decisiones de diseño

**El color sigue al significado.** Azul es siempre dinero; verde es siempre
ayuda ya entregada. Quien lo aprende una vez no lo vuelve a aprender.

**Accesibilidad medida, no estimada.** La paleta se validó con simulación de
daltonismo (Machado-Oliveira-Fernandes) y contraste WCAG: todos los elementos
funcionales pasan AA, y las dos series de las gráficas están a ΔE 23.6 bajo
protanopia, muy por encima del mínimo de 8.

**El tema es nativo.** Colores, bordes y radios se definen en
`.streamlit/config.toml`, no con CSS inyectado, para que sobrevivan a las
actualizaciones de Streamlit. La única excepción es el banner destacado.

**Nada de números inventados.** La sección "qué logró tu aporte" arma la
combinación únicamente con unidades que de verdad se compraron; si el monto no
alcanza a cubrirse con lo comprado, lo dice en vez de inflar cantidades.

## Licencia

Sin licencia definida. Si vas a reutilizarlo, avisá.
