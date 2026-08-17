"""Traduce al inglés lo que ya estaba cargado antes de que existieran las
columnas _en, y lo guarda en la base.

Se corre UNA vez, después de `migration_idioma_ingles.sql`. De ahí en adelante
cada registro nuevo se traduce solo al guardarse, así que este script no hace
falta nunca más (aunque volver a correrlo es inofensivo: sólo toca las filas
que todavía no tienen su versión en inglés).

Por qué existe: sin esto, el tablero traduce en vivo cada vez que un donante lo
abre en inglés. Eso es lento, depende de que el servicio de traducción esté
disponible en ese momento, y con el tope de seguridad de views/i18n.py deja
parte del contenido en español. Traducirlo una vez y guardarlo resuelve las
tres cosas.

    python backfill_traducciones.py            # traduce lo que falte
    python backfill_traducciones.py --dry-run  # sólo muestra qué haría
"""

import sys

import database as db
from views.i18n import translate_to_english

# tabla -> (campos a traducir, columna que identifica la fila)
OBJETIVOS = {
    "campaigns": ("description", "donation_info"),
    "donations": ("notes",),
    "invoices": ("notes", "merchant"),
    "invoice_items": ("item_name", "category"),
    "gallery_photos": ("title", "description"),
}

LOTE = 500


def filas_pendientes(tabla: str, campos: tuple[str, ...]) -> list[dict]:
    """Trae las filas donde al menos un campo tiene texto pero le falta su _en."""
    columnas = ",".join(["id", *campos, *[f"{c}_en" for c in campos]])
    filas: list[dict] = []
    desde = 0
    while True:
        pagina = (
            db.get_admin_client()
            .table(tabla)
            .select(columnas)
            .range(desde, desde + LOTE - 1)
            .execute()
            .data
        )
        if not pagina:
            break
        filas.extend(pagina)
        if len(pagina) < LOTE:
            break
        desde += LOTE

    return [
        fila
        for fila in filas
        if any(
            (fila.get(campo) or "").strip() and not (fila.get(f"{campo}_en") or "").strip()
            for campo in campos
        )
    ]


def main() -> int:
    solo_mirar = "--dry-run" in sys.argv
    total_filas = 0
    total_campos = 0

    for tabla, campos in OBJETIVOS.items():
        try:
            pendientes = filas_pendientes(tabla, campos)
        except Exception as error:
            print(f"[{tabla}] no se pudo leer: {error}")
            print("  ¿Corriste migration_idioma_ingles.sql en el SQL Editor de Supabase?")
            return 1

        if not pendientes:
            print(f"[{tabla}] al día — nada que traducir.")
            continue

        print(f"[{tabla}] {len(pendientes)} fila(s) por traducir…")
        for fila in pendientes:
            nuevos = {}
            for campo in campos:
                original = (fila.get(campo) or "").strip()
                if not original or (fila.get(f"{campo}_en") or "").strip():
                    continue
                traducido = translate_to_english(original)
                if traducido and traducido != original:
                    nuevos[f"{campo}_en"] = traducido
                elif traducido:
                    # El traductor devolvió lo mismo (falló, o el texto ya
                    # estaba en inglés). Se guarda igual: deja constancia de que
                    # esta fila ya se procesó y evita reintentarla para siempre.
                    nuevos[f"{campo}_en"] = traducido

            if not nuevos:
                continue
            total_filas += 1
            total_campos += len(nuevos)

            muestra = next(iter(nuevos.values()))[:60]
            print(f"  {fila['id']}: {', '.join(nuevos)} → {muestra!r}")
            if not solo_mirar:
                db.get_admin_client().table(tabla).update(nuevos).eq("id", fila["id"]).execute()

    print()
    verbo = "se traducirían" if solo_mirar else "traducidos"
    print(f"{total_campos} campo(s) en {total_filas} fila(s) {verbo}.")
    if solo_mirar:
        print("Fue una corrida en seco: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
