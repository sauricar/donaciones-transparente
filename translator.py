"""Traducción al inglés, sin Streamlit de por medio.

Vive fuera de views/ porque lo usan tres lugares con necesidades distintas:

- `database.py`, al guardar un registro. La capa de datos no tiene por qué
  importar una vista para traducir una nota.
- `views/i18n.py`, para el respaldo en vivo del contenido que todavía no tiene
  su versión guardada.
- `backfill_traducciones.py`, que corre desde la terminal. Ahí no hay sesión de
  Streamlit, y arrastrarlo sólo servía para llenar la salida de avisos sobre un
  runtime que no existe.

Acá no hay caché ni estado de sesión: eso es responsabilidad de quien llama.
"""

import time

from views.translations import GLOSARIO

# El endpoint gratuito de Google que usa deep-translator falla cada tanto sin
# razón: la misma frase que revienta ahora anda al segundo intento. Medido
# contra los datos reales de este proyecto, con tres intentos no quedó ninguna
# sin traducir.
REINTENTOS = 3


def translate_to_english(texto: str | None) -> str | None:
    """Devuelve el texto en inglés, o None si no se pudo traducir.

    Nunca levanta una excepción: que el traductor esté caído no puede impedir
    que se guarde una factura ni tumbar el tablero de un donante.

    None significa "no hay traducción para guardar", y quien llama debe dejar la
    columna _en vacía. Es importante que NO devuelva el texto original ante una
    falla: guardar el español dentro de la columna inglesa haría que ese
    registro se vea como ya traducido, y ni el tablero ni backfill_traducciones
    volverían a intentarlo nunca — quedaría en español para siempre.

    Ojo: una traducción que sale idéntica al original NO es una falla. Pasa con
    nombres propios ('Dollarcity', 'Enalapril') y se guarda como cualquier otra,
    justamente para no reintentarla en cada visita."""
    original = (texto or "").strip()
    if not original:
        return None

    del_glosario = GLOSARIO.get(original.casefold())
    if del_glosario:
        return del_glosario

    # Import adentro: si deep-translator no está instalado, la app tiene que
    # seguir andando en español en vez de no arrancar.
    try:
        from deep_translator import GoogleTranslator
    except Exception:
        return None

    for intento in range(REINTENTOS):
        try:
            resultado = GoogleTranslator(source="es", target="en").translate(original)
            if resultado:
                return resultado
        except Exception:
            time.sleep(0.8 * (intento + 1))
    return None
