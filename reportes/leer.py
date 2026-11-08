"""Paso 1: leer los archivos de ventas, sean CSV o Excel, y juntarlos en una sola tabla.

Cada sistema de caja exporta distinto: separador ; o , , títulos antes de la
tabla, columnas con otros nombres ("Artículo" en vez de "Producto")...
Acá se detecta todo eso para que el resto del programa reciba siempre
las mismas columnas.

Conceptos de Python que aparecen acá:
- pathlib.Path: manejar rutas de archivos sin pelear con las barras \\ y /.
- pandas.DataFrame: una tabla en memoria (como una hoja de Excel).
- excepciones (raise / try): avisar de un problema con un mensaje claro.
"""
import csv
import unicodedata
from pathlib import Path

import pandas as pd

# Nombre estándar de cada columna -> nombres que puede traer el archivo.
COLUMNAS = {
    "fecha": ["fecha", "fecha venta", "dia", "fecha de venta"],
    "hora": ["hora", "hora venta"],
    "ticket": ["ticket", "n ticket", "nro ticket", "numero de ticket", "comprobante"],
    "producto": ["producto", "articulo", "descripcion", "item"],
    "cantidad": ["cantidad", "cant", "unidades"],
    "precio": ["precio unitario", "precio", "p unitario"],
    "total": ["total", "importe", "monto", "subtotal"],
    "pago": ["medio de pago", "forma de pago", "pago", "medio"],
}
OBLIGATORIAS = ["fecha", "producto"]


class ErrorDeArchivo(Exception):
    """Problema con un archivo, con un mensaje pensado para el usuario."""


def _sin_tildes(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def _normalizar_encabezado(texto):
    texto = _sin_tildes(str(texto).replace("º", "").replace("°", "")).lower()  # "Nº" -> "N"
    return " ".join("".join(c if c.isalnum() else " " for c in texto).split())


def _columna_estandar(encabezado):
    limpio = _normalizar_encabezado(encabezado)
    for estandar, opciones in COLUMNAS.items():
        if limpio in opciones:
            return estandar
    return None


def _fila_de_encabezados(tabla):
    """Busca en las primeras filas la que tiene los títulos (por si hay un título arriba)."""
    for i in range(min(15, len(tabla))):
        encontradas = {_columna_estandar(v) for v in tabla.iloc[i] if pd.notna(v)}
        if set(OBLIGATORIAS) <= encontradas:
            return i
    return None


def _leer_crudo(ruta):
    if ruta.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(ruta, header=None, dtype=object)
    with open(ruta, encoding="utf-8-sig", errors="replace") as archivo:
        muestra = archivo.read(4096)
    separador = csv.Sniffer().sniff(muestra, delimiters=";,\t").delimiter
    return pd.read_csv(ruta, sep=separador, header=None, dtype=str, encoding="utf-8-sig",
                       encoding_errors="replace", keep_default_na=False, skip_blank_lines=False)


def leer_archivo(ruta):
    """Lee un archivo y devuelve una tabla con las columnas estándar."""
    ruta = Path(ruta)
    try:
        crudo = _leer_crudo(ruta)
    except Exception as error:
        raise ErrorDeArchivo(f"No se pudo abrir «{ruta.name}». Puede estar dañado, abierto en otro programa "
                             "o no ser un archivo de ventas.") from error

    fila = _fila_de_encabezados(crudo)
    if fila is None:
        raise ErrorDeArchivo(f"En «{ruta.name}» no encontré las columnas de fecha y producto.")

    tabla = crudo.iloc[fila + 1:].copy()
    nombres = {}
    for posicion, encabezado in enumerate(crudo.iloc[fila]):
        estandar = _columna_estandar(encabezado) if pd.notna(encabezado) else None
        if estandar and estandar not in nombres.values():
            nombres[tabla.columns[posicion]] = estandar
    tabla = tabla[list(nombres)].rename(columns=nombres)
    for falta in COLUMNAS:
        if falta not in tabla.columns:
            tabla[falta] = None
    tabla["archivo"] = ruta.name
    tabla["fila_original"] = tabla.index + 1   # para poder ubicar errores en el archivo
    return tabla[list(COLUMNAS) + ["archivo", "fila_original"]].reset_index(drop=True)


def leer_archivos(rutas):
    """Lee varios archivos y los junta. Devuelve (tabla, lista de avisos)."""
    tablas, avisos = [], []
    for ruta in rutas:
        tabla = leer_archivo(ruta)
        avisos.append(f"«{Path(ruta).name}»: {len(tabla)} filas leídas")
        tablas.append(tabla)
    if not tablas:
        raise ErrorDeArchivo("No se eligió ningún archivo.")
    return pd.concat(tablas, ignore_index=True), avisos
