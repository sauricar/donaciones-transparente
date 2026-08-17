# Manual del administrador

Guía para quien vaya a operar una instalación de este tablero — ya sea la
original o una copia propia desplegada a partir de este repositorio.

Hay dos roles distintos, con contraseñas distintas:

| Rol | Qué hace | Dónde entra |
|---|---|---|
| **Operador del sitio** | Crea las campañas y da los accesos: nombre, link, usuario y contraseña | `/admin-campanas` |
| **Encargado de campaña** | Carga donaciones, facturas y evidencias, y escribe cómo se presenta SU campaña | `/panel-de-gestion` |

Una misma persona puede tener los dos roles (por ejemplo, si sos el único
administrador y también el único que recibe donaciones), pero son dos
inicios de sesión separados con dos contraseñas separadas.

---

## 1. Antes de empezar: ¿tenés instancia propia o vas a usar una copia?

Si estás usando el tablero que ya está desplegado, saltá a la
[sección 3](#3-crear-una-campaña-rol-operador). Esta sección es para quien
copió el repositorio y está montando su propia instancia desde cero.

### 1.1. Requisitos

- Una cuenta de [Supabase](https://supabase.com) (plan gratuito alcanza).
- Una cuenta de [GitHub](https://github.com).
- Una cuenta de [Streamlit Community Cloud](https://share.streamlit.io).

### 1.2. Base de datos

1. Creá un proyecto nuevo en Supabase.
2. Andá a **SQL Editor** y ejecutá el contenido completo de
   [`schema.sql`](schema.sql). Esto crea las tablas, la seguridad a nivel de
   fila y la función que registra facturas con sus artículos de forma atómica.
3. Andá a **Storage** y creá un bucket llamado exactamente **`evidencias`**,
   marcado como **público**. Ahí se guardan las fotos de evidencia y las de
   perfil de cada campaña. Si no queda público, las fotos no se van a poder
   ver desde el tablero.

### 1.3. Secretos

En **Project Settings → API** de Supabase vas a encontrar tres valores:
la URL del proyecto, la clave `anon`/`publishable`, y la clave `service_role`.

La clave `service_role` **salta toda la seguridad de la base de datos**.
Nunca la compartas, nunca la subas a un repositorio, nunca la pongas en un
mensaje. Si alguna vez sospechás que se filtró, rotala de inmediato desde el
mismo panel de Supabase.

Además de esos tres valores, definí una contraseña propia para el rol de
operador (no viene de Supabase, la elegís vos).

### 1.4. Desplegar en Streamlit Community Cloud

1. Forkeá o cloná este repositorio en tu propia cuenta de GitHub.
2. En [share.streamlit.io](https://share.streamlit.io), **Create app** →
   *Deploy a public app from GitHub*.
3. Repositorio: el tuyo. Rama: `main`. Archivo principal: `app.py`.
4. Antes de darle a *Deploy*, abrí **Advanced settings → Secrets** y pegá:

   ```toml
   SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
   SUPABASE_KEY = "tu clave anon/publishable"
   SUPABASE_SERVICE_KEY = "tu clave service_role"
   ADMIN_PASSWORD = "contraseña de respaldo del operador"
   ```

   `ADMIN_PASSWORD` es sólo el acceso de respaldo, para entrar la primera vez
   y poder correr `migration_operadores.sql`, que es la que crea tu usuario
   de operador de verdad ([sección 2.1](#21-crear-el-usuario-de-operador)).

5. Deploy. La primera carga tarda unos minutos.

Nunca pongas estos valores dentro de un archivo del repositorio. Si tu copia
del repo es pública, cualquiera que vea `secrets.toml` con valores reales
tiene acceso total a tu base de datos.

### 1.5. Migrando una instalación que ya tenía datos

Si estás actualizando una instalación anterior a este cambio en vez de armar
una nueva, no vuelvas a correr `schema.sql` (fallaría porque las tablas ya
existen). En cambio, corré en orden los archivos `migration_*.sql` que estén
en la raíz del repo — cada uno indica en su propio encabezado qué agrega y
si hace falta completar algún dato antes de ejecutarlo.

---

## 2. Iniciar sesión

Desde la portada (`/inicio`), arriba a la derecha, están los accesos a las
tres pantallas: **Campañas**, **Gestión** y **Administración**.

- **Operador**: entrá a `/admin-campanas`, o con el botón **"Administración"**
  de la portada. Ingresá tu **usuario y contraseña** de operador (los que
  definiste al correr `migration_operadores.sql` — ver
  [sección 2.1](#21-crear-el-usuario-de-operador)).
- **Encargado de campaña**: entrá a `/panel-de-gestion`, o con el botón
  **"Gestión"**, e ingresá el usuario y la contraseña que el operador creó
  para tu campaña.

Dentro de cualquiera de los dos paneles, los botones de arriba a la derecha
te devuelven a la portada.

Que el enlace al panel de operador esté a la vista no lo deja expuesto: lo
que lo protege es la contraseña. El tablero público de cada campaña —el que
se comparte con quien dona— no muestra ese acceso.

### 2.1. Crear el usuario de operador

El acceso de operador vive en la tabla `operators` de la base, con el mismo
esquema que las campañas: usuario único y contraseña hasheada.

1. Abrí el **SQL Editor** de Supabase.
2. Pegá el contenido de `migration_operadores.sql`, reemplazando
   `<tu-usuario>` y `<TU_CONTRASENA>` por los que quieras.
3. Ejecutalo. Se puede correr más de una vez sin duplicar nada.

Para agregar otro operador más adelante, corré sólo el `insert` de ese
archivo con los datos nuevos.

> **Mientras no corras esta migración**, el panel sigue abriéndose con el
> secreto `ADMIN_PASSWORD` y el usuario que escribas se ignora. Es a
> propósito: así actualizar la app no te deja afuera de tu propio panel
> mientras encontrás el momento de correr el SQL. En cuanto la tabla existe,
> `ADMIN_PASSWORD` deja de servir para entrar.

---

## 3. Crear una campaña (rol operador)

Como operador definís **quién entra y con qué link**. Cómo se presenta la
campaña —descripción, datos para aportar y foto— lo escribe ella misma desde
su panel de gestión.

1. En `/admin-campanas`, completá el bloque **"Nueva campaña"**:
   - **Nombre de la campaña / persona**: como se va a mostrar públicamente.
   - **Slug para el link público**: la parte de la URL que identifica la
     campaña (por ejemplo `maria-perez` da como resultado
     `.../campana?c=maria-perez`). Si lo dejás vacío, se genera solo a partir
     del nombre. Solo minúsculas, números y guiones.
   - **Usuario de acceso** y **Contraseña**: las credenciales que vas a
     entregarle al encargado de esa campaña para que entre a
     `/panel-de-gestion`.
2. Botón **"Crear campaña"**.
3. La campaña queda activa de inmediato y visible en el selector público
   (`/inicio`). Hasta que su encargado escriba la descripción, el selector
   muestra un texto genérico en su lugar.

### Editar una campaña existente

Cada campaña aparece en un panel expandible en **"Campañas existentes"**,
con:

- **Nombre**, **Slug** y **Usuario**, editables, más el interruptor
  **"Activa"** (desactivarla la oculta del selector público y del acceso
  directo, sin borrar sus datos).
- El botón **"Restablecer contraseña"**, para cuando el encargado la olvida.

> La **descripción pública**, los **datos para aportar** y la **foto** no se
> editan desde acá: los maneja cada campaña desde su propio panel, en la
> pestaña "⚙️ Mi campaña"
> ([sección 7](#7-cómo-se-presenta-tu-campaña)). Así el encargado puede
> corregir un número de Nequi sin tener que pedírtelo.

---

## 4. Cargar donaciones recibidas (rol encargado de campaña)

En `/panel-de-gestion`, pestaña **"💰 Donaciones"**:

1. Completá **Monto**, **Fecha** y una **Nota / Concepto** opcional.
2. **"Registrar Donación"**.

Debajo del formulario aparece la tabla **"Donaciones registradas"**: es
editable directamente sobre la celda (fecha, monto, notas) y tiene una
columna **"Borrar"** para marcar las que hay que eliminar. Los cambios no se
aplican solos — hacé clic en **"Guardar cambios en donaciones"** al terminar.

> Este tablero no guarda ningún dato de quién donó — ni nombre, ni contacto.
> Es intencional: es una app de transparencia sobre el dinero, no un CRM de
> donantes.

---

## 5. Cargar una factura con sus artículos

Pestaña **"🧾 Facturas"**:

1. **Datos generales**: Comercio/Proveedor, Número de factura (opcional) y
   Fecha.
2. **Artículos**: una tabla editable. Por cada artículo cargá nombre,
   categoría, cantidad, precio unitario e impuestos. Con el botón **+** de la
   tabla agregás filas para más artículos de la misma factura.
   - Si necesitás una categoría que no está en la lista, usá el botón
     **"➕ Nueva categoría"** al lado del título. Queda disponible de
     inmediato, y en cuanto guardás una factura con ella, se vuelve
     permanente — no hace falta crearla de nuevo la próxima vez.
3. **"Guardar Factura Completa"**. La factura y todos sus artículos se
   guardan juntos: si algo falla, no queda una factura a medias.

El formulario se vacía solo después de guardar, listo para la siguiente
factura.

### Editar o borrar una factura ya cargada

Debajo del formulario, **"Facturas registradas"** lista todas las facturas
en paneles expandibles. Adentro de cada una podés corregir los datos
generales y la tabla de artículos (agregar, quitar, modificar), y guardar con
**"Guardar cambios"**. El botón **"🗑️ Borrar factura"** pide una confirmación
extra antes de eliminarla — borra la factura y todos sus artículos, y no se
puede deshacer.

---

## 6. Cargar evidencias fotográficas

Pestaña **"📸 Cargar Evidencias"**:

### Antes de empezar: revisá qué factura es cuál

Si tenés varias facturas del mismo comercio en la misma fecha, el selector
de factura las distingue por su **monto** y sus primeros **artículos** — por
ejemplo `Ferreteria D' Forja · 12/08/2026 · $579.000 · Linternas, Palas +3`.
Fijate en ese detalle antes de elegir, para no vincular una foto a la
factura equivocada. Un ⬜ al principio de la etiqueta marca las facturas que
todavía no tienen ninguna evidencia asociada; un ✅, las que ya tienen.

Si hay facturas sin evidencia, aparece un aviso arriba de todo con el
listado — no hace falta ir a buscarlas una por una.

### Cargar fotos

1. Arrastrá o seleccioná **una o varias fotos** a la vez en el cargador.
2. Si varias fotos son de la misma compra, usá el bloque **"Completar todas
   de una vez"**: escribí un título base y elegí la factura, tocá
   **"Aplicar"**, y las fotos quedan numeradas automáticamente
   ("Entrega … 1", "Entrega … 2", …).
3. Revisá o ajustá cada foto individualmente: cada una tiene su propia
   miniatura, su campo de **título** (obligatorio) y su selector de
   **factura que respalda** (opcional — una foto también puede ser evidencia
   general sin vincularse a ninguna compra puntual).
4. **"Cargar N evidencia(s)"**. Una barra de progreso muestra el avance; si
   alguna falla, te dice cuál sin perder las demás.

### Corregir una evidencia ya cargada

Más abajo, **"Evidencias publicadas"** lista todas las fotos con su estado
(✅ / ⬜ sin factura). El interruptor **"Ver sólo las que no tienen factura
asignada"** filtra la lista para terminar de vincular las que quedaron
sueltas. Dentro de cada una podés corregir el título o la factura y
**"Guardar"**, o **"Borrar"** (con confirmación) — el borrado elimina tanto
el registro como el archivo de la foto.

---

## 7. Cómo se presenta tu campaña

Pestaña **"⚙️ Mi campaña"**. Todo lo de esta pestaña lo manejás vos: el
operador del sitio crea la campaña y te da el acceso, pero de ahí en adelante
sos vos quien decide cómo se ve de cara al público.

### Los textos

- **Descripción pública**: una o dos líneas sobre tu campaña. Aparecen bajo tu
  nombre en el directorio de campañas y arriba de tu tablero público. Si la
  dejás vacía, el directorio muestra un texto genérico.
- **Cómo aportar** (opcional): texto libre con los datos para donar (Nequi,
  Daviplata, cuenta bancaria, contacto…). Si lo completás, aparece como un
  banner destacado arriba de tu tablero, con un botón para copiar el texto. Si
  lo dejás vacío, el banner simplemente no aparece.

Se guardan con **"Guardar cambios"** y el tablero público los toma enseguida.

### La foto

Subís una foto tuya y aparece en ese mismo banner, junto a los datos para
aportar. Ponerle cara a quien recibe y ejecuta el dinero le da confianza a
quien está decidiendo si ayuda.

**"Guardar foto"** la publica; **"Quitar foto"** la elimina, también del
almacenamiento. Si subís una nueva, la anterior se borra sola.

---

## 7.1. El tablero en inglés

El tablero se ve completo en español y en inglés. Quien lo visita elige el
idioma en el selector **"Idioma / Language"** de la barra lateral, y el enlace
`...?lang=en` abre directamente en inglés — ese es el que conviene compartir
con donantes que no leen español.

**No tenés que escribir nada dos veces.** Lo que cargues (artículos, notas,
pies de foto, tu descripción y tus datos para aportar) se traduce solo al
guardarlo y queda guardado en los dos idiomas.

Dos cosas que conviene saber:

- Los montos en inglés se muestran como `COP 21,923,796`, con la moneda
  explícita, para que nadie los confunda con dólares.
- Revisá una vez cómo quedó tu bloque **"Cómo aportar"** en inglés: los
  números de cuenta y de Nequi se conservan tal cual, pero vale la pena
  confirmarlo, porque es el dato con el que la gente te va a transferir.

> **Instalación que ya tenía datos**: lo cargado antes de esta función no está
> traducido todavía. Corré `migration_idioma_ingles.sql` y después, una sola
> vez, `python backfill_traducciones.py`. Mientras tanto el tablero traduce en
> vivo lo que alcanza y deja el resto en español.

---

## 8. Compartir el tablero

El enlace público de una campaña es
`https://tu-instancia.streamlit.app/campana?c=<slug>` — lo encontrás en el
panel de operador, debajo del nombre de cada campaña ("Link público:
`?c=slug`"), o simplemente navegando a esa campaña desde el selector
(`/inicio`) y copiando la URL del navegador.

Ese es el único enlace que hace falta compartir con la comunidad de
donantes. `/panel-de-gestion` y `/admin-campanas` son solo para quien
administra.

---

## 9. Preguntas frecuentes

**¿Puedo tener más de una campaña activa a la vez?** Sí, son completamente
independientes: cada una con sus propias donaciones, facturas, fotos,
usuario y contraseña.

**¿Qué pasa si pauso una campaña?** Desaparece del selector público y su
enlace directo muestra un aviso de "campaña pausada", pero los datos siguen
intactos. Reactivarla la devuelve tal cual estaba.

**¿Se puede recuperar una factura o foto borrada?** No. Los dos borrados
piden confirmación explícita porque son irreversibles.

**¿Por qué no se puede cargar un beneficiario o una lista de personas
ayudadas?** Es una decisión de diseño: la app mide lo que se compró y
entregó (auditable con factura), no a quién llegó, porque en muchos casos
la entrega la hace un centro de acopio externo y ese dato no se puede
verificar.
