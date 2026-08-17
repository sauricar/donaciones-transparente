"""Catálogo de textos fijos (es/en) y glosario de términos del dominio.

Sólo datos: la lógica está en views/i18n.py.

Dos convenciones que conviene respetar al agregar textos:

- Las claves se agrupan por pantalla (`nav.`, `portada.`, `tablero.`…) para que
  se pueda ver de un vistazo qué falta traducir de una sección.
- Los marcadores van con formato de `str.format` (`{monto}`), nunca concatenando
  pedazos de frase: el orden de las palabras cambia entre idiomas y armar la
  oración por partes produce inglés roto.

El GLOSARIO del final es la respuesta al riesgo real de un traductor automático
en este dominio: 'colchoneta' no es 'mat' a secas y 'mercado' no es 'market'
cuando se refiere a la remesa de comida. Lo que esté acá no se manda a traducir
nunca — se responde con la traducción curada, gratis y siempre igual en todas
las facturas.
"""

TEXTOS: dict[str, dict[str, str]] = {
    # --- Navegación y comunes ---------------------------------------------
    "nav.campanas": {"es": "Campañas", "en": "Campaigns"},
    "nav.gestion": {"es": "Gestión", "en": "Management"},
    "nav.administracion": {"es": "Administración", "en": "Administration"},
    "nav.volver_campanas": {"es": "← Ver todas las campañas", "en": "← See all campaigns"},
    "nav.volver_principal": {"es": "← Volver a la página principal", "en": "← Back to the main page"},
    "comun.sin_categoria": {"es": "Sin categoría", "en": "Uncategorized"},
    "comun.traduciendo": {"es": "Traduciendo…", "en": "Translating…"},
    "comun.moneda_nota": {
        "es": "Todos los montos están en pesos colombianos (COP).",
        "en": "All amounts are in Colombian pesos (COP).",
    },
    "error.conexion": {
        "es": (
            "😕 No pudimos conectarnos a la base de datos en este momento. "
            "Es un problema temporal del servidor, no de tus datos — "
            "volvé a intentarlo en unos minutos."
        ),
        "en": (
            "😕 We couldn't reach the database right now. It's a temporary "
            "server problem, not a problem with your data — please try again "
            "in a few minutes."
        ),
    },
    "error.detalle_tecnico": {"es": "Detalle técnico", "en": "Technical details"},

    # --- Portada / selector de campañas -----------------------------------
    "portada.titulo": {
        "es": "🤝 Transparencia de Donaciones",
        "en": "🤝 Donation Transparency",
    },
    "portada.subtitulo": {
        "es": (
            "Personas que recibieron donaciones y muestran, peso por peso, en qué "
            "las convirtieron. Elegí una campaña para ver su rendición de cuentas."
        ),
        "en": (
            "People who received donations and show, peso by peso, what they turned "
            "them into. Pick a campaign to see its accounting."
        ),
    },
    "portada.entre_todas": {"es": "#### Entre todas las campañas", "en": "#### Across all campaigns"},
    "portada.campanas_activas": {"es": "Campañas activas", "en": "Active campaigns"},
    "portada.recibido": {"es": "Recibido", "en": "Received"},
    "portada.ejecutado": {"es": "Ya ejecutado", "en": "Already spent"},
    "portada.por_ejecutar": {"es": "Por ejecutar", "en": "Yet to be spent"},
    "portada.articulos_entregados": {"es": "Artículos entregados", "en": "Items delivered"},
    "portada.resumen_aportes": {
        "es": "{aportes} aportes de personas y organizaciones, con cada peso respaldado por su factura.",
        "en": "{aportes} contributions from people and organizations, every peso backed by its receipt.",
    },
    "portada.campanas": {"es": "#### Campañas", "en": "#### Campaigns"},
    "portada.sin_campanas": {
        "es": "Todavía no hay campañas publicadas.",
        "en": "No campaigns have been published yet.",
    },
    "portada.descripcion_defecto": {
        "es": "Rendición de cuentas de las donaciones recibidas.",
        "en": "Accounting for the donations received.",
    },
    "portada.ver_rendicion": {"es": "Ver rendición de cuentas", "en": "See the accounting"},

    # --- Tablero público: encabezado y KPIs -------------------------------
    "tablero.subtitulo": {
        "es": "Cada peso que llegó y en qué se convirtió — con las facturas y las fotos que lo respaldan.",
        "en": "Every peso that came in and what it became — with the receipts and photos that back it up.",
    },
    "tablero.no_encontrada": {"es": "No encontramos esa campaña.", "en": "We couldn't find that campaign."},
    "tablero.pausada": {
        "es": "La campaña **{nombre}** está pausada por el momento.",
        "en": "The **{nombre}** campaign is paused for now.",
    },
    "tablero.recibido": {"es": "Recibido de la gente", "en": "Received from people"},
    "tablero.convertido": {"es": "Ya convertido en ayuda", "en": "Already turned into aid"},
    "tablero.pendiente": {"es": "Pendiente por ejecutar", "en": "Still to be spent"},
    "tablero.medidor": {
        "es": "{pct}% de lo recibido ya se transformó en artículos comprados y entregados.",
        "en": "{pct}% of what was received has already become items bought and delivered.",
    },
    "tablero.aportes": {"es": "Aportes", "en": "Contributions"},
    "tablero.promedio_aporte": {"es": "Promedio por aporte", "en": "Average contribution"},
    "tablero.ultimo_movimiento": {"es": "Último movimiento", "en": "Latest activity"},
    "tablero.explora": {"es": "#### Explorá el detalle", "en": "#### Explore the detail"},
    "tablero.secciones": {"es": "Secciones del tablero", "en": "Dashboard sections"},
    "tablero.accesos_arriba": {
        "es": "Los accesos a los paneles de gestión están arriba, en la parte superior de la página.",
        "en": "Links to the management panels are at the top of the page.",
    },

    # --- Banner "cómo aportar" --------------------------------------------
    "banner.como_aportar": {
        "es": "##### :green[Cómo aportar a esta campaña]",
        "en": "##### :green[How to contribute to this campaign]",
    },
    "banner.quien_recibe": {
        "es": "Quien recibe y ejecuta estos aportes: **{nombre}**",
        "en": "Who receives and spends these contributions: **{nombre}**",
    },

    # --- Secciones del tablero --------------------------------------------
    "seccion.entregado": {"es": "📦 Entregado", "en": "📦 Delivered"},
    "seccion.facturas": {"es": "🧾 Facturas", "en": "🧾 Receipts"},
    "seccion.aportes": {"es": "💚 Aportes", "en": "💚 Contributions"},
    "seccion.galeria": {"es": "📸 Galería", "en": "📸 Gallery"},
    "seccion.tu_aporte": {"es": "🧮 Tu aporte", "en": "🧮 Your contribution"},
    # Sin el emoji: va como rótulo de una tarjeta, no como botón de sección.
    "seccion.facturas_llanas": {"es": "Facturas publicadas", "en": "Receipts published"},

    # --- Entregado ---------------------------------------------------------
    "entregado.titulo": {
        "es": "**Cada artículo que se compró y entregó**",
        "en": "**Every item bought and delivered**",
    },
    "entregado.ayuda": {
        "es": (
            "Artículos comprados con las donaciones y entregados a los centros de acopio, "
            "que son quienes los reparten entre las familias afectadas."
        ),
        "en": (
            "Items bought with the donations and handed over to the collection centers, "
            "which distribute them among the affected families."
        ),
    },
    "entregado.top": {
        "es": "Se muestran los 8 artículos más entregados de {total} en total.",
        "en": "Showing the 8 most delivered items out of {total} in total.",
    },
    "entregado.tipo_ayuda": {
        "es": "**En qué tipo de ayuda se invirtió**",
        "en": "**What kind of aid the money went to**",
    },
    "entregado.sin_articulos": {
        "es": "Todavía no se han registrado artículos.",
        "en": "No items have been recorded yet.",
    },
    # Encabezados de tabla. Van sueltos porque los mismos rótulos se repiten en
    # varias tablas del tablero.
    "tabla.articulo": {"es": "Artículo", "en": "Item"},
    "tabla.categoria": {"es": "Categoría", "en": "Category"},
    "tabla.cantidad": {"es": "Cantidad", "en": "Quantity"},
    "tabla.invertido": {"es": "Invertido", "en": "Spent"},
    "tabla.valor_unitario": {"es": "Valor Unitario", "en": "Unit price"},
    "tabla.impuestos": {"es": "Impuestos", "en": "Taxes"},
    "tabla.subtotal": {"es": "Subtotal", "en": "Subtotal"},
    "tabla.fecha": {"es": "Fecha", "en": "Date"},
    "tabla.monto": {"es": "Monto", "en": "Amount"},
    "tabla.notas": {"es": "Notas", "en": "Notes"},
    "aportes.cada_aporte": {"es": "**Cada aporte recibido**", "en": "**Every contribution received**"},

    # --- Ritmo diario ------------------------------------------------------
    "ritmo.titulo": {"es": "**El ritmo día por día**", "en": "**Day-by-day pace**"},
    "ritmo.entrada_salida": {
        "es": "**Lo que entró y lo que salió, cada día**",
        "en": "**What came in and what went out, each day**",
    },
    "ritmo.aportes_dia": {"es": "**Aportes por día**", "en": "**Contributions per day**"},
    "ritmo.articulos_dia": {"es": "**Artículos comprados por día**", "en": "**Items bought per day**"},
    "ritmo.hover": {
        "es": "Pasá el cursor sobre una barra para ver el detalle del día.",
        "en": "Hover over a bar to see that day's detail.",
    },
    "ritmo.sin_gastos": {
        "es": "Todavía no hay gastos para mostrar.",
        "en": "There are no expenses to show yet.",
    },

    # --- Facturas ----------------------------------------------------------
    "facturas.evidencia": {"es": "**Evidencia de esta compra**", "en": "**Evidence of this purchase**"},
    "facturas.ayuda": {
        "es": (
            "Cada compra con su factura y, cuando existe, la foto de la entrega. "
            "Nada de lo que aparece arriba sale de otro lado."
        ),
        "en": (
            "Every purchase with its receipt and, where available, the delivery photo. "
            "Nothing shown above comes from anywhere else."
        ),
    },
    "facturas.sin_items": {
        "es": "Esta factura no tiene ítems registrados.",
        "en": "This receipt has no items recorded.",
    },
    "facturas.sin_facturas": {
        "es": "Aún no se han publicado facturas.",
        "en": "No receipts have been published yet.",
    },

    # --- Aportes -----------------------------------------------------------
    "aportes.ayuda": {
        "es": (
            "Cada aporte es alguien que decidió ayudar. "
            "No se guarda ningún dato personal de quienes donaron."
        ),
        "en": (
            "Each contribution is someone who decided to help. "
            "No personal data about donors is stored."
        ),
    },
    "aportes.sin_aportes": {
        "es": "Aún no se han registrado aportes.",
        "en": "No contributions have been recorded yet.",
    },
    "aportes.ayuda_corta": {
        "es": "Cada aporte es alguien que decidió ayudar.",
        "en": "Each contribution is someone who decided to help.",
    },

    # --- Galería -----------------------------------------------------------
    "galeria.ayuda": {
        "es": "Fotos de las compras y las entregas.",
        "en": "Photos of the purchases and the deliveries.",
    },
    "galeria.sin_fotos": {
        "es": "Aún no se han publicado fotos.",
        "en": "No photos have been published yet.",
    },

    # --- "Tu aporte" -------------------------------------------------------
    "aporte.titulo": {
        "es": "🎁 En esto se convirtió el aporte de todos",
        "en": "🎁 This is what everyone's contribution became",
    },
    "aporte.intro": {
        "es": (
            "Escribí lo que aportaste y te mostramos una combinación equivalente "
            "de artículos que ya están comprados y entregados."
        ),
        "en": (
            "Enter what you contributed and we'll show you an equivalent combination "
            "of items that have already been bought and delivered."
        ),
    },
    "aporte.monto": {"es": "Lo que aportaste", "en": "What you contributed"},
    "aporte.monto_extra": {
        "es": "Monto que estás pensando aportar",
        "en": "Amount you're thinking of contributing",
    },
    "aporte.monto_invalido": {
        "es": "Ingresá un monto mayor a cero.",
        "en": "Enter an amount greater than zero.",
    },
    "aporte.equivale": {
        "es": "**Tu aporte, reflejado en lo que ya se compró**",
        "en": "**Your contribution, reflected in what has already been bought**",
    },
    "aporte.con_monto_se_compro": {
        "es": "Con {monto} se compró, por ejemplo:",
        "en": "With {monto} the campaign bought, for example:",
    },
    "aporte.con_monto_se_podria": {
        "es": "Con {monto} se podría comprar, por ejemplo:",
        "en": "With {monto} you could buy, for example:",
    },
    "aporte.suma_real": {
        "es": "Suma {monto} a precios reales de compra.",
        "en": "That adds up to {monto} at real purchase prices.",
    },
    "aporte.participacion": {
        "es": "Tu aporte fue el **{pct}%** de todo lo recaudado.",
        "en": "Your contribution was **{pct}%** of everything raised.",
    },
    "aporte.no_alcanza": {
        "es": "Con ese monto todavía no alcanza para un artículo completo.",
        "en": "That amount isn't quite enough for a whole item yet.",
    },
    "aporte.no_alcanza_sumado": {
        "es": (
            "Con ese monto no alcanzaba ni un artículo completo por sí solo — "
            "pero sumado al de los demás, sí hizo la diferencia."
        ),
        "en": (
            "On its own that amount wasn't enough for a single whole item — "
            "but added to everyone else's, it did make the difference."
        ),
    },
    "aporte.tope": {
        "es": (
            "No se llega a {monto} porque la combinación sólo usa unidades que de "
            "verdad se compraron, así que la combinación se arma sobre ese tope."
        ),
        "en": (
            "It doesn't reach {monto} because the combination only uses units that "
            "were actually bought, so it's built up to that ceiling."
        ),
    },
    "aporte.supera_ejecutado": {
        "es": (
            "Tu aporte supera lo ejecutado hasta hoy ({monto}), "
            "así que la combinación se arma sobre ese tope."
        ),
        "en": (
            "Your contribution is larger than what has been spent so far ({monto}), "
            "so the combination is built up to that ceiling."
        ),
    },
    "aporte.otra_combinacion": {"es": "Ver otra combinación", "en": "Show another combination"},
    "aporte.sin_compras": {
        "es": "Todavía no hay compras registradas para hacer el cálculo.",
        "en": "There are no purchases recorded yet to run the calculation.",
    },
    "aporte.mas_titulo": {
        "es": "**¿Y si quisieras aportar más?**",
        "en": "**And if you wanted to contribute more?**",
    },
    "aporte.mas_ayuda": {
        "es": "Cuántas unidades más caben, por plata y por lo realmente comprado.",
        "en": "How many more units fit, by money and by what was actually bought.",
    },
    "aporte.estimacion": {
        "es": "Esto sí es una estimación, con los precios que se han pagado hasta ahora.",
        "en": "This one is an estimate, using the prices paid so far.",
    },
    "aporte.existen": {
        "es": (
            "Es una forma de dimensionar el aporte: todos estos artículos existen "
            "y están en las facturas publicadas."
        ),
        "en": (
            "It's a way to picture the contribution: all of these items exist "
            "and appear in the published receipts."
        ),
    },
    "aporte.costo_unitario": {
        "es": "Artículos comprados con su costo unitario real (impuestos incluidos).",
        "en": "Items bought, with their real unit cost (taxes included).",
    },

    # --- Gráficas ----------------------------------------------------------
    # Los hovertemplate de Plotly llevan marcadores propios (%{customdata[0]}),
    # así que estos textos se insertan alrededor sin pasar por str.format.
    "grafica.unidades": {"es": "und.", "en": "units"},
    "grafica.cada_uno": {"es": "c/u", "en": "each"},
    "grafica.aportes": {"es": "Aportes", "en": "Contributions"},
    "grafica.suman": {"es": "Suman", "en": "Total"},
    "grafica.promedio": {"es": "Promedio", "en": "Average"},
    "grafica.promedio_aporte": {"es": "Promedio por aporte", "en": "Average contribution"},
    "grafica.articulos": {"es": "Artículos", "en": "Items"},
    "grafica.facturas": {"es": "Facturas", "en": "Receipts"},
    "grafica.gastado": {"es": "Gastado", "en": "Spent"},
    "grafica.recibido": {"es": "Recibido", "en": "Received"},
    "categoria.otros": {"es": "Otros", "en": "Other"},
    "ritmo.aportes_del_dia": {"es": "Aportes del {dia}", "en": "Contributions on {dia}"},
    "ritmo.suman_ese_dia": {"es": "Suman ese día", "en": "Total that day"},
    "ritmo.se_alcanzo": {
        "es": "Lo que se alcanzó a comprar y entregar.",
        "en": "What was actually bought and delivered.",
    },
    "aporte.cesta_linea": {
        "es": "{cantidad} × {nombre}",
        "en": "{cantidad} × {nombre}",
    },
    "aporte.cesta_no_llega": {
        "es": (
            "No se llega a {monto} porque la combinación sólo usa "
            "unidades que de verdad se compraron."
        ),
        "en": (
            "It doesn't reach {monto} because the combination only uses "
            "units that were actually bought."
        ),
    },
}

# Categorías base traducidas. Las categorías propias que cree una campaña no
# están acá y caen al traductor dinámico.
CATEGORIAS = {
    "alimentos": "Food",
    "aseo personal": "Personal hygiene",
    "donación externa": "External donation",
    "donacion externa": "External donation",
    "equipos": "Equipment",
    "herramientas": "Tools",
    "hogar": "Household",
    "insumos médicos": "Medical supplies",
    "insumos medicos": "Medical supplies",
    "logística": "Logistics",
    "logistica": "Logistics",
    "otros": "Other",
    "sin categoría": "Uncategorized",
}

# Términos del dominio donde un traductor automático se equivoca o es ambiguo.
# La clave va en minúsculas (se compara con casefold) y gana siempre sobre el
# traductor: es gratis, instantáneo y garantiza que el mismo artículo se lea
# igual en todas las facturas.
GLOSARIO = {
    **CATEGORIAS,
    # Ayuda humanitaria: 'mat' a secas no dice que es para dormir.
    "colchoneta": "Sleeping mat",
    "colchonetas": "Sleeping mats",
    # 'mercado' acá es la remesa de comida, no un mercado/plaza.
    "mercado": "Groceries",
    "mercados": "Grocery packages",
    "remesa": "Grocery package",
    "kit de aseo": "Hygiene kit",
    "kits de aseo": "Hygiene kits",
    "aseo": "Hygiene supplies",
    # Productos colombianos que conviene no traducir del todo: se explican.
    "panela": "Panela (raw cane sugar)",
    "bocadillo": "Guava paste",
    "arepa": "Arepa (corn flatbread)",
    "arepas": "Arepas (corn flatbreads)",
    # Materiales de reconstrucción.
    "tejas de zinc": "Zinc roofing sheets",
    "teja de zinc": "Zinc roofing sheet",
    "damnificados": "People affected by the disaster",
    "centro de acopio": "Collection center",
    "centros de acopio": "Collection centers",
    "albergue": "Shelter",
}
