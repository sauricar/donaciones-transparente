import random

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import database as db
from views.data import load_data, show_connection_error
from views.theme import (
    BANNER_BG, BANNER_BORDER, FLAG_BLUE, FLAG_RED, FLAG_YELLOW, INK_SOFT,
    NAV_ACTIVE_INK, SERIES_IMPACT, SERIES_MONEY, SURFACE, apply_chart_theme,
    format_currency, format_date, format_day_short, format_number,
    format_signed_currency,
)


def flag_stripe():
    """The one piece of custom markup left: a decorative flag rule Streamlit has
    no native element for. It carries no data and no interaction."""
    st.html(
        f"""
        <div style='display:flex;height:5px;border-radius:3px;overflow:hidden;margin:0.25rem 0 1.75rem;'>
            <div style='flex:2;background:{FLAG_YELLOW};'></div>
            <div style='flex:1;background:{FLAG_BLUE};'></div>
            <div style='flex:1;background:{FLAG_RED};'></div>
        </div>
        """
    )


def render_donation_banner(campaign: dict):
    """Banner destacado con los datos para aportar y la cara de quien lidera.

    El CSS acá es deliberado y está pedido explícitamente ('colores que lo
    permitan resaltar'). Va por la clase .st-key-<key> que Streamlit genera a
    partir del `key` del contenedor — el gancho estable que la documentación
    recomienda para estos casos, en vez de apuntarle a clases generadas."""
    info = (campaign.get("donation_info") or "").strip()
    photo = campaign.get("photo_url")
    if not info and not photo:
        return

    st.html(
        f"""
        <style>
          .st-key-donation_banner {{
              background: {BANNER_BG};
              border: 1px solid {BANNER_BORDER};
              border-radius: 12px;
              padding: 0.4rem 0.2rem;
          }}
        </style>
        """
    )

    with st.container(border=True, key="donation_banner"):
        if photo:
            photo_col, body = st.columns([1, 4], vertical_alignment="center")
            with photo_col:
                st.image(photo, width="stretch")
        else:
            body = st.container()

        with body:
            st.markdown("##### :green[Cómo aportar a esta campaña]")
            if photo:
                st.caption(f"Quien recibe y ejecuta estos aportes: **{campaign['name']}**")
            if info:
                # st.code trae botón de copiar nativo: un toque deja el dato en
                # el portapapeles, sin selección manual ni CSS propio.
                st.code(info, language=None, wrap_lines=True)


def metric_card(column, label: str, value: str, accent: str = None, note: str = None):
    """Stat tile. Native st.metric — border and radius come from config.toml.

    The series colour rides a markdown dot in the LABEL, never the number: the
    :blue[…] / :green[…] tokens resolve to blueColor / greenColor from the
    theme, so identity is carried without a line of CSS."""
    marker = {"money": ":blue[●] ", "impact": ":green[●] "}.get(accent, "")
    with column:
        st.metric(label=f"{marker}{label}", value=value, help=note, border=True)


def mini_stat(column, icon: str, value, label: str):
    with column:
        st.metric(label=label, value=value, icon=icon, border=True)


def meter(pct: float, caption: str):
    """Single ratio against a limit. st.progress is the native meter and its
    fill follows primaryColor (the palette green), so it needs no styling."""
    st.progress(min(max(pct, 0), 1.0))
    st.caption(caption)


def aggregate_items(items: list[dict]) -> pd.DataFrame:
    """Group delivered items by name (case/whitespace-insensitive) so the same
    article typed slightly differently doesn't split into two rows."""
    rows = []
    for item in items:
        name = (item["item_name"] or "").strip()
        if not name:
            continue
        rows.append(
            {
                "key": name.casefold(),
                "name": name,
                "quantity": item["quantity"],
                "total_price": item["total_price"],
                "category": item.get("category") or "Sin categoría",
            }
        )
    if not rows:
        return pd.DataFrame(columns=["name", "quantity", "total_price", "category"])

    df = pd.DataFrame(rows)
    grouped = df.groupby("key").agg(
        name=("name", "first"),
        quantity=("quantity", "sum"),
        total_price=("total_price", "sum"),
        category=("category", "first"),
    ).reset_index(drop=True)
    return grouped.sort_values("quantity", ascending=False)


def horizontal_bar(labels, values, value_labels, color: str, height_per_bar: int = 42):
    """One series across nominal categories -> every bar takes ONE colour (never
    a value-ramp, which would re-encode bar length as hue), sorted by magnitude,
    with the value direct-labelled at the tip. No legend: a single series is
    named by the heading above it. The colour carries meaning, not rank —
    green where the subject is help delivered, blue where it is money."""
    figure = go.Figure(
        go.Bar(
            x=list(values),
            y=list(labels),
            orientation="h",
            marker=dict(color=color),
            width=0.62,
            text=list(value_labels),
            # "auto" keeps the label inside the bar when it fits there and moves
            # it outside otherwise. On a phone the longest bar leaves no room to
            # its right, so a fixed "outside" overflows the plot and gets cut;
            # letting it sit inside the bar is the documented way out. The two
            # font slots exist because the label changes background when it
            # moves: white on the saturated fill, ink on the card.
            textposition="auto",
            insidetextfont=dict(color=SURFACE, size=12),
            outsidetextfont=dict(color=INK_SOFT, size=12),
            constraintext="none",
            hovertemplate="%{y}<br>%{text}<extra></extra>",
            cliponaxis=False,
        )
    )
    # The longest bar otherwise fills the whole drawing area, leaving its
    # outside label nowhere to go — it then overflows the plot and gets cut.
    # Reserving headroom on the axis (scaled to the longest label) keeps every
    # label inside the figure, whatever the container width.
    values_list = [float(v) for v in values]
    longest_label = max((len(str(t)) for t in value_labels), default=0)
    headroom = 1 + min(0.30, longest_label * 0.015)

    figure.update_layout(
        xaxis=dict(visible=False, range=[0, max(values_list, default=0) * headroom or 1]),
        yaxis=dict(autorange="reversed", showgrid=False),
        margin=dict(t=8, b=8, l=8, r=16),
        bargap=0.35,
    )
    apply_chart_theme(figure, height=max(160, len(list(labels)) * height_per_bar + 40))
    return figure


def render_delivered_chart(items: list[dict]):
    aggregated = aggregate_items(items)
    if aggregated.empty:
        st.info("Todavía no hay artículos registrados.")
        return

    top = aggregated.head(8)
    figure = horizontal_bar(
        labels=top["name"],
        values=top["quantity"],
        value_labels=[f"{format_number(q)} und." for q in top["quantity"]],
        color=SERIES_IMPACT,
    )
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

    if len(aggregated) > 8:
        st.caption(f"Se muestran los 8 artículos más entregados de {len(aggregated)} en total.")


def render_category_chart(items: list[dict]):
    if not items:
        st.info("Todavía no hay gastos para mostrar.")
        return

    df = pd.DataFrame(items)
    df["category"] = df["category"].fillna("Sin categoría")
    totals = df.groupby("category")["total_price"].sum().sort_values(ascending=False)
    grand_total = totals.sum()

    if len(totals) > 7:
        totals = pd.concat([totals.iloc[:6], pd.Series({"Otros": totals.iloc[6:].sum()})])

    labels = [
        f"{format_currency(v)}  ·  {v / grand_total * 100:.0f}%" if grand_total else format_currency(v)
        for v in totals.values
    ]
    figure = horizontal_bar(
        labels=totals.index, values=totals.values, value_labels=labels, color=SERIES_MONEY
    )
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


DAILY_COLUMNS = ["day", "amount", "count", "avg", "spent", "invoices", "units"]


def daily_series(donations: list[dict], invoices: list[dict], items: list[dict]) -> pd.DataFrame:
    """Un renglón por día calendario, cubriendo todo el período en que hubo
    actividad (aportes o compras), con los días sin movimiento en cero.

    Rellenar los ceros es lo que hace honesta la lectura del ritmo: si se
    graficaran solo los días con movimiento, tres aportes espaciados por semanas
    se verían igual de seguidos que tres de días consecutivos.

    Columnas: amount/count/avg de aportes; spent/invoices/units de compras."""
    if not donations and not invoices:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    frames = []

    if donations:
        don = pd.DataFrame(donations)
        don["day"] = pd.to_datetime(don["donation_date"]).dt.normalize()
        frames.append(don.groupby("day").agg(amount=("amount", "sum"), count=("amount", "size")))

    if invoices:
        inv = pd.DataFrame(invoices)
        inv["day"] = pd.to_datetime(inv["invoice_date"]).dt.normalize()
        frames.append(inv.groupby("day").agg(invoices=("id", "size")))

    if items:
        it = pd.DataFrame(items)
        it["day"] = pd.to_datetime(it["invoice_date"]).dt.normalize()
        frames.append(it.groupby("day").agg(spent=("total_price", "sum"), units=("quantity", "sum")))

    merged = pd.concat(frames, axis=1)
    full_range = pd.date_range(merged.index.min(), merged.index.max(), freq="D")
    merged = merged.reindex(full_range, fill_value=0).rename_axis("day")

    for column in ("amount", "count", "spent", "invoices", "units"):
        if column not in merged:
            merged[column] = 0
    merged = merged.fillna(0)

    # Promedio por aporte del día: sin aportes no hay promedio (no es cero).
    merged["avg"] = (merged["amount"] / merged["count"]).where(merged["count"] > 0, 0)
    return merged.reset_index()[DAILY_COLUMNS]


def _apply_daily_axis(figure, daily: pd.DataFrame, height: int, show_legend: bool = False):
    """Marcas del eje armadas a mano: plotly rotula los meses en inglés, y con
    pocos días inventa una granularidad que los datos no tienen (medios días,
    horas). Se muestran todos los días mientras quepan, y a partir de ahí uno
    de cada N para no amontonarlas."""
    step = max(1, len(daily) // 12)
    ticks = daily["day"].iloc[::step]
    figure.update_layout(
        xaxis=dict(showgrid=False, tickvals=list(ticks), ticktext=[format_day_short(d) for d in ticks]),
        yaxis=dict(rangemode="tozero"),
        margin=dict(t=8, b=8, l=8, r=8),
        hovermode="x unified",
    )
    apply_chart_theme(figure, height=height, show_legend=show_legend)
    figure.update_yaxes(tickformat=",.0f", separatethousands=True)
    return figure


def render_money_flow_chart(daily: pd.DataFrame):
    """Dos series con la MISMA unidad (pesos), así que comparten eje sin
    distorsionar nada — a diferencia de mezclar plata con cantidades, que
    obligaría a dos escalas y fabricaría una correlación inexistente."""
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=daily["day"], y=daily["amount"], name="Recibido",
            marker=dict(color=SERIES_MONEY), width=0.38 * 86_400_000,
            customdata=[[format_currency(v), int(c), format_currency(a)]
                        for v, c, a in zip(daily["amount"], daily["count"], daily["avg"])],
            hovertemplate="Recibido: %{customdata[0]}<br>"
                          "Aportes: %{customdata[1]}<br>"
                          "Promedio por aporte: %{customdata[2]}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            x=daily["day"], y=daily["spent"], name="Gastado",
            marker=dict(color=SERIES_IMPACT), width=0.38 * 86_400_000,
            customdata=[[format_currency(v), int(i), format_number(u)]
                        for v, i, u in zip(daily["spent"], daily["invoices"], daily["units"])],
            hovertemplate="Gastado: %{customdata[0]}<br>"
                          "Facturas: %{customdata[1]}<br>"
                          "Artículos: %{customdata[2]}<extra></extra>",
        )
    )
    figure.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    return _apply_daily_axis(figure, daily, height=300, show_legend=True)


def render_contributions_chart(daily: pd.DataFrame):
    """Cuántos aportes por día. El monto y el promedio viajan en el hover: el
    alto de la barra ya dice cuántos, y ponerle tres números encima a cada
    barra sería ruido que nadie lee."""
    figure = go.Figure(
        go.Bar(
            x=daily["day"], y=daily["count"],
            marker=dict(color=SERIES_MONEY), width=0.62 * 86_400_000,
            customdata=[[int(c), format_currency(v), format_currency(a)]
                        for c, v, a in zip(daily["count"], daily["amount"], daily["avg"])],
            hovertemplate="Aportes: %{customdata[0]}<br>"
                          "Suman: %{customdata[1]}<br>"
                          "Promedio: %{customdata[2]}<extra></extra>",
        )
    )
    return _apply_daily_axis(figure, daily, height=240)


def render_purchases_chart(daily: pd.DataFrame):
    """Artículos comprados por día; el número de facturas va en el hover."""
    figure = go.Figure(
        go.Bar(
            x=daily["day"], y=daily["units"],
            marker=dict(color=SERIES_IMPACT), width=0.62 * 86_400_000,
            customdata=[[format_number(u), int(i), format_currency(s)]
                        for u, i, s in zip(daily["units"], daily["invoices"], daily["spent"])],
            hovertemplate="Artículos: %{customdata[0]}<br>"
                          "Facturas: %{customdata[1]}<br>"
                          "Gastado: %{customdata[2]}<extra></extra>",
        )
    )
    return _apply_daily_axis(figure, daily, height=240)


def render_daily_activity(donations: list[dict], invoices: list[dict], items: list[dict]):
    daily = daily_series(donations, invoices, items)
    if daily.empty:
        st.info("Aún no se han registrado aportes.")
        return

    with_donations = daily[daily["count"] > 0]
    last = with_donations.iloc[-1] if not with_donations.empty else daily.iloc[-1]
    earlier = with_donations.iloc[-2] if len(with_donations) > 1 else None

    tiles = st.columns(3)
    with tiles[0]:
        st.metric(
            label=f"Aportes del {format_day_short(last['day'])}",
            value=format_number(last["count"]),
            delta=(f"{int(last['count'] - earlier['count']):+d}" if earlier is not None else None),
            # delta_color="off" deja la variación en gris: informa el cambio sin
            # calificarlo de bueno ni malo.
            delta_color="off",
            border=True,
        )
    with tiles[1]:
        st.metric(
            label="Suman ese día",
            value=format_currency(last["amount"]),
            delta=(format_signed_currency(last["amount"] - earlier["amount"]) if earlier is not None else None),
            delta_color="off",
            border=True,
        )
    with tiles[2]:
        st.metric(
            label="Promedio por aporte",
            value=format_currency(last["avg"]),
            delta=(format_signed_currency(last["avg"] - earlier["avg"]) if earlier is not None else None),
            delta_color="off",
            border=True,
        )

    st.write("")
    st.markdown("**Lo que entró y lo que salió, cada día**")
    st.caption("Pasá el cursor sobre una barra para ver el detalle del día.")
    st.plotly_chart(render_money_flow_chart(daily), width="stretch", config={"displayModeBar": False})

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.markdown("**Aportes por día**")
        st.caption("Cada aporte es alguien que decidió ayudar.")
        st.plotly_chart(render_contributions_chart(daily), width="stretch", config={"displayModeBar": False})
    with chart_cols[1]:
        st.markdown("**Artículos comprados por día**")
        st.caption("Lo que se alcanzó a comprar y entregar.")
        st.plotly_chart(render_purchases_chart(daily), width="stretch", config={"displayModeBar": False})


def build_basket(rows: list[dict], amount: float, rng: random.Random,
                 respect_stock: bool, max_kinds: int = 4) -> tuple[list[dict], float]:
    """Arma una canasta de artículos reales por hasta `amount` pesos.

    respect_stock=True limita cada artículo a las unidades REALMENTE compradas:
    es la diferencia entre "tu aporte equivale a esto que ya se compró" (un
    hecho) y "con esto se podría comprar" (una estimación). Sin ese tope, la
    primera sección estaría inventando cantidades que nunca existieron.

    El presupuesto se reparte entre varios artículos en vez de gastarlo todo en
    el más barato, que daría "500 tapabocas" en lugar de una canasta creíble."""
    candidates = [r for r in rows if 0 < r["unit_cost"] <= amount and (not respect_stock or r["quantity"] >= 1)]
    if not candidates:
        return [], 0.0

    rng.shuffle(candidates)
    basket, remaining = [], amount

    def espacio(row, ya_tomadas: int) -> int:
        """Cuántas unidades más caben, por plata y por lo realmente comprado."""
        por_plata = int(remaining // row["unit_cost"])
        if respect_stock:
            return max(0, min(por_plata, int(row["quantity"]) - ya_tomadas))
        return por_plata

    # Primera pasada: ningún artículo se lleva más del 40% del monto, para que
    # la canasta sea una mezcla y no "97 unidades de lo más barato".
    tope_por_articulo = amount * 0.4
    for row in candidates:
        if len(basket) >= max_kinds or remaining <= 0:
            break
        quantity = min(int(min(remaining, tope_por_articulo) // row["unit_cost"]), espacio(row, 0))
        if quantity < 1:
            continue
        basket.append({**row, "qty": quantity, "cost": quantity * row["unit_cost"]})
        remaining -= quantity * row["unit_cost"]

    # Segunda pasada: el sobrante se reparte en lo que ya está en la canasta,
    # así el total se acerca al monto en vez de quedar corto por el redondeo.
    for entry in basket:
        extra = espacio(entry, entry["qty"])
        if extra >= 1:
            entry["qty"] += extra
            entry["cost"] += extra * entry["unit_cost"]
            remaining -= extra * entry["unit_cost"]

    # Tercera: si el tope del 40% y el stock dejaron plata sin usar, se suman
    # artículos nuevos hasta agotarla o quedarse sin candidatos.
    if remaining > 0:
        ya_estan = {entry["name"] for entry in basket}
        for row in candidates:
            if remaining <= 0 or len(basket) >= max_kinds + 4:
                break
            if row["name"] in ya_estan:
                continue
            quantity = espacio(row, 0)
            if quantity < 1:
                continue
            basket.append({**row, "qty": quantity, "cost": quantity * row["unit_cost"]})
            remaining -= quantity * row["unit_cost"]

    return basket, amount - remaining


def purchase_catalog(items: list[dict]) -> list[dict]:
    """Artículos comprados con su costo unitario real (impuestos incluidos)."""
    aggregated = aggregate_items(items)
    if aggregated.empty:
        return []
    aggregated = aggregated[aggregated["quantity"] > 0].copy()
    aggregated["unit_cost"] = aggregated["total_price"] / aggregated["quantity"]
    aggregated = aggregated[aggregated["unit_cost"] > 0]
    return aggregated.to_dict("records")


def render_basket(basket: list[dict], spent: float, amount: float = None, stock_limited: bool = False):
    for entry in basket:
        st.markdown(
            f"- **{format_number(entry['qty'])}** × {entry['name']} "
            f":gray[({entry['category']} · {format_currency(entry['unit_cost'])} c/u)]"
        )
    st.caption(f"Suma {format_currency(spent)} a precios reales de compra.")
    # Con montos grandes se agotan las unidades realmente compradas y la canasta
    # queda por debajo del aporte. Decirlo es preferible a inflar cantidades.
    if stock_limited and amount and spent < amount * 0.9:
        st.caption(
            f"No se llega a {format_currency(amount)} porque la combinación sólo usa "
            "unidades que de verdad se compraron."
        )


def render_photo_grid(photos: list[dict], columns_count: int = 3):
    columns = st.columns(columns_count)
    for index, photo in enumerate(photos):
        with columns[index % columns_count]:
            st.image(photo["photo_url"], width="stretch")
            st.markdown(f"**{photo['title']}**")
            st.caption(format_date(photo["created_at"][:10]))
            if photo.get("description"):
                st.caption(photo["description"])


# Las etiquetas viven acá para que el selector y el despacho no puedan
# desincronizarse: una sola fuente para ambos. Son cortas a propósito: en
# celular las etiquetas largas partían la fila de botones en tres renglones
# desparejos y se leía como un amontonamiento.
SECCIONES = (
    "📦 Entregado",
    "🧾 Facturas",
    "💚 Aportes",
    "📸 Galería",
    "🧮 Tu aporte",
)


def render_top_nav(include_operator: bool = False):
    """Accesos a los paneles, arriba de todo y alineados a la derecha.

    Antes vivían al pie de la página: quien administra tenía que bajar hasta
    el final para encontrarlos. El enlace al panel de operador va en la
    portada, junto a los otros dos, para que las tres puertas de la plataforma
    se abran desde el mismo lugar; lo que protege ese panel es su contraseña,
    no lo escondido del enlace. Queda fuera del tablero público de una campaña,
    que es el que se comparte con quien dona."""
    selector_page = st.session_state.get("_selector_page")
    admin_page = st.session_state.get("_admin_page")
    operator_page = st.session_state.get("_operator_page")

    destinos = []
    if selector_page is not None:
        destinos.append((selector_page, "Campañas", ":material/home:"))
    if admin_page is not None:
        destinos.append((admin_page, "Gestión", ":material/lock:"))
    if include_operator and operator_page is not None:
        destinos.append((operator_page, "Administración", ":material/settings:"))
    if not destinos:
        return

    st.html(
        """
        <style>
          .st-key-top_nav a[data-testid="stPageLink-NavLink"] {
              border: 1px solid var(--color-border, #CFD8DC);
              border-radius: 10px;
              padding: 0.45rem 0.7rem;
              justify-content: center;
          }
        </style>
        """
    )
    with st.container(key="top_nav"):
        columnas = st.columns([6] + [1.3] * len(destinos), vertical_alignment="center")
        for columna, (pagina, etiqueta, icono) in zip(columnas[1:], destinos):
            with columna:
                st.page_link(pagina, label=etiqueta, icon=icono, width="stretch")


def section_delivered(items: list[dict]):
    aggregated = aggregate_items(items)
    if aggregated.empty:
        st.info("Todavía no se han registrado artículos.")
        return

    st.markdown("**Cada artículo que se compró y entregó**")
    display_df = pd.DataFrame(
        {
            "Artículo": aggregated["name"],
            "Categoría": aggregated["category"],
            "Cantidad": [format_number(q) for q in aggregated["quantity"]],
            "Invertido": [format_currency(v) for v in aggregated["total_price"]],
        }
    )
    st.dataframe(display_df, hide_index=True, width="stretch")

    st.write("")
    st.markdown("**En qué tipo de ayuda se invirtió**")
    render_category_chart(items)


def section_invoices(invoices: list[dict], items: list[dict], photos: list[dict]):
    if not invoices:
        st.info("Aún no se han publicado facturas.")
        return

    st.caption(
        "Cada compra con su factura y, cuando existe, la foto de la entrega. "
        "Nada de lo que aparece arriba sale de otro lado."
    )
    photos_by_invoice = {}
    for photo in photos:
        if photo.get("invoice_id"):
            photos_by_invoice.setdefault(photo["invoice_id"], []).append(photo)

    for invoice in invoices:
        invoice_items = [i for i in items if i["invoice_id"] == invoice["id"]]
        invoice_total = sum(i["total_price"] for i in invoice_items)
        linked_photos = photos_by_invoice.get(invoice["id"], [])
        evidence_flag = f"  ·  📸 {len(linked_photos)}" if linked_photos else ""
        title = (
            f"{invoice['merchant']} — {format_date(invoice['invoice_date'])} — "
            f"{format_currency(invoice_total)}{evidence_flag}"
        )
        with st.expander(title):
            if invoice.get("notes"):
                st.caption(invoice["notes"])
            if not invoice_items:
                st.info("Esta factura no tiene ítems registrados.")
            else:
                items_df = pd.DataFrame(
                    {
                        "Artículo": [i["item_name"] for i in invoice_items],
                        "Categoría": [i["category"] or "Sin categoría" for i in invoice_items],
                        "Cantidad": [i["quantity"] for i in invoice_items],
                        "Valor Unitario": [format_currency(i["unit_price"]) for i in invoice_items],
                        "Impuestos": [format_currency(i["tax_amount"]) for i in invoice_items],
                        "Subtotal": [format_currency(i["total_price"]) for i in invoice_items],
                    }
                )
                st.dataframe(items_df, hide_index=True, width="stretch")

            if linked_photos:
                st.markdown("**Evidencia de esta compra**")
                render_photo_grid(linked_photos, columns_count=3)


def section_contributions(donations: list[dict], invoices: list[dict], items: list[dict]):
    if not donations:
        st.info("Aún no se han registrado aportes.")
        return

    st.markdown("**El ritmo día por día**")
    render_daily_activity(donations, invoices, items)

    st.write("")
    st.markdown("**Cada aporte recibido**")
    st.caption("No se guarda ningún dato personal de quienes donaron.")
    donations_df = pd.DataFrame(donations).sort_values("donation_date", ascending=False)
    display_df = pd.DataFrame(
        {
            "Fecha": donations_df["donation_date"].apply(format_date),
            "Monto": donations_df["amount"].apply(format_currency),
            "Notas": donations_df["notes"].fillna("—"),
        }
    )
    st.dataframe(display_df, hide_index=True, width="stretch")


def section_gallery(photos: list[dict]):
    if not photos:
        st.info("Aún no se han publicado fotos.")
        return
    st.caption("Fotos de las compras y las entregas.")
    render_photo_grid(photos)


def section_impact(items: list[dict], total_donated: float, total_spent: float):
    catalog = purchase_catalog(items)
    if not catalog:
        st.info("Todavía no hay compras registradas para hacer el cálculo.")
        return

    # --- 1. Lo ya comprado: hechos, no supuestos ---------------------------
    st.markdown("**Tu aporte, reflejado en lo que ya se compró**")
    st.caption(
        "Escribí lo que aportaste y te mostramos una combinación equivalente "
        "de artículos que ya están comprados y entregados."
    )
    contribution = st.number_input(
        "Lo que aportaste", min_value=0, value=100000, step=10000, format="%d",
    )

    if contribution <= 0:
        st.info("Ingresá un monto mayor a cero.")
    else:
        if total_donated > 0:
            share = contribution / total_donated * 100
            st.markdown(f"Tu aporte fue el **{share:.1f}%** de todo lo recaudado.")

        tope = min(contribution, total_spent)
        if contribution > total_spent:
            st.caption(
                f"Tu aporte supera lo ejecutado hasta hoy ({format_currency(total_spent)}), "
                "así que la combinación se arma sobre ese tope."
            )

        seed = st.session_state.setdefault("basket_seed_real", 0)
        # La semilla depende del monto para que el resultado no cambie
        # solo/por teclear, y del contador para el botón de recombinar.
        basket, spent = build_basket(
            catalog, tope, random.Random(f"{int(tope)}-{seed}"), respect_stock=True
        )
        if not basket:
            st.warning(
                "Con ese monto no alcanzaba ni un artículo completo por sí solo — "
                "pero sumado al de los demás, sí hizo la diferencia."
            )
        else:
            st.success(f"Con {format_currency(tope)} se compró, por ejemplo:")
            render_basket(basket, spent, amount=tope, stock_limited=True)
            if st.button("Ver otra combinación", key="reshuffle_real"):
                st.session_state.basket_seed_real += 1
                st.rerun()
            st.caption(
                "Es una forma de dimensionar el aporte: todos estos artículos existen "
                "y están en las facturas publicadas."
            )

    st.divider()

    # --- 2. Lo que vendría después: estimación clara como tal --------------
    st.markdown("**¿Y si quisieras aportar más?**")
    st.caption("Esto sí es una estimación, con los precios que se han pagado hasta ahora.")
    extra = st.number_input(
        "Monto que estás pensando aportar", min_value=0, value=50000, step=10000, format="%d",
    )

    if extra > 0:
        seed_extra = st.session_state.setdefault("basket_seed_extra", 0)
        # respect_stock=False: acá sí se proyecta a futuro, no está
        # limitado a las unidades ya compradas.
        proyeccion, proyectado = build_basket(
            catalog, extra, random.Random(f"{int(extra)}-{seed_extra}"), respect_stock=False
        )
        if not proyeccion:
            st.warning("Con ese monto todavía no alcanza para un artículo completo.")
        else:
            st.info(f"Con {format_currency(extra)} se podría comprar, por ejemplo:")
            render_basket(proyeccion, proyectado)
            if st.button("Ver otra combinación", key="reshuffle_extra"):
                st.session_state.basket_seed_extra += 1
                st.rerun()


def render():
    selector_page = st.session_state.get("_selector_page")
    slug = st.query_params.get("c")

    try:
        campaign = db.get_campaign_by_slug(slug) if slug else None
    except Exception as error:
        st.title("🤝 Transparencia de Donaciones")
        show_connection_error(error)
        return

    if campaign is None or not campaign["is_active"]:
        st.title("🤝 Transparencia de Donaciones")
        if campaign is None:
            st.warning("No encontramos esa campaña.")
        else:
            st.warning(f"La campaña **{campaign['name']}** está pausada por el momento.")
        if selector_page is not None:
            st.page_link(selector_page, label="← Ver todas las campañas")
        return

    try:
        donations, invoices, items, photos = load_data(campaign["id"])
    except Exception as error:
        st.title(f"🤝 {campaign['name']}")
        show_connection_error(error)
        return

    render_top_nav()

    st.title(f"🤝 {campaign['name']}")
    if campaign.get("description"):
        st.caption(campaign["description"])
    st.caption("Cada peso que llegó y en qué se convirtió — con las facturas y las fotos que lo respaldan.")
    flag_stripe()
    render_donation_banner(campaign)

    total_donated = sum(d["amount"] for d in donations)
    total_spent = sum(i["total_price"] for i in items)
    balance = total_donated - total_spent
    pct_used = (total_spent / total_donated) if total_donated > 0 else 0

    kpi_cols = st.columns(3)
    metric_card(kpi_cols[0], "Recibido de la gente", format_currency(total_donated), accent="money")
    metric_card(kpi_cols[1], "Ya convertido en ayuda", format_currency(total_spent), accent="impact")
    metric_card(kpi_cols[2], "Pendiente por ejecutar", format_currency(balance))

    meter(
        pct_used,
        f"{pct_used * 100:,.1f}% de lo recibido ya se transformó en artículos comprados y entregados.".replace(",", "."),
    )

    donation_count = len(donations)
    items_delivered = sum(i["quantity"] for i in items)
    avg_donation = (total_donated / donation_count) if donation_count else 0
    all_dates = [d["donation_date"] for d in donations] + [i["invoice_date"] for i in items]
    last_activity = format_date(max(all_dates)) if all_dates else "—"

    st.write("")
    stat_cols = st.columns(5)
    mini_stat(stat_cols[0], ":material/volunteer_activism:", format_number(donation_count), "Aportes recibidos")
    mini_stat(stat_cols[1], ":material/payments:", format_currency(avg_donation), "Aporte promedio")
    mini_stat(stat_cols[2], ":material/inventory_2:", format_number(items_delivered), "Artículos entregados")
    mini_stat(stat_cols[3], ":material/receipt_long:", format_number(len(invoices)), "Facturas publicadas")
    mini_stat(stat_cols[4], ":material/schedule:", last_activity, "Último movimiento")

    st.divider()

    st.subheader("🎁 En esto se convirtió el aporte de todos")
    st.caption(
        "Artículos comprados con las donaciones y entregados a los centros de acopio, "
        "que son quienes los reparten entre las familias afectadas."
    )
    render_delivered_chart(items)

    st.divider()

    # Navegación con botones en vez de st.tabs: las pestañas de Streamlit son
    # discretas y la gente no las veía. Además, st.tabs calcula el contenido de
    # TODAS las secciones en cada ejecución aunque nadie las abra; así sólo se
    # arma la que está a la vista, que en móvil y en Streamlit Cloud se nota.
    st.markdown("#### Explorá el detalle")
    # El alto por defecto (32px) pasa desapercibido, que es justo el problema a
    # resolver. Se agranda por la clase .st-key-<key> que Streamlit genera a
    # partir del `key` del widget — el gancho estable que la documentación
    # recomienda, en vez de apuntarle a clases autogeneradas.
    st.html(
        f"""
        <style>
          .st-key-nav_secciones button {{
              height: 54px;
              font-size: 1.02rem;
              font-weight: 600;
          }}
          /* El verde de marca sobre el fondo tenue del botón activo mide
             4.49:1, apenas por debajo del 4.5:1 que pide WCAG para texto
             normal. Un paso más oscuro de la misma familia lo lleva a
             6.89:1 sin cambiar el color de acento del resto de la app.
             Lleva !important porque la regla propia de Streamlit para el
             estado activo gana por especificidad. */
          .st-key-nav_secciones button[aria-checked="true"] {{
              color: {NAV_ACTIVE_INK} !important;
          }}
        </style>
        """
    )
    seccion = st.segmented_control(
        "Secciones del tablero",
        options=SECCIONES,
        default=SECCIONES[0],
        selection_mode="single",
        # required evita que un segundo clic deseleccione y deje la página en blanco.
        required=True,
        width="stretch",
        label_visibility="collapsed",
        key="nav_secciones",
    )
    st.write("")

    if seccion == SECCIONES[0]:
        section_delivered(items)
    elif seccion == SECCIONES[1]:
        section_invoices(invoices, items, photos)
    elif seccion == SECCIONES[2]:
        section_contributions(donations, invoices, items)
    elif seccion == SECCIONES[3]:
        section_gallery(photos)
    elif seccion == SECCIONES[4]:
        section_impact(items, total_donated, total_spent)

    st.divider()
    st.caption(
        "Los accesos a los paneles de gestión están arriba, en la parte superior de la página."
    )
