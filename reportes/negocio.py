"""Datos del negocio: productos, precios, colores y nombres de los meses.

Si el programa se adapta a otro cliente, este es el único archivo que hay que cambiar.

Conceptos de Python que aparecen acá:
- diccionarios (dict): pares "clave: valor", como una agenda.
- constantes en MAYÚSCULAS: valores que el resto del programa lee pero no cambia.
"""

NEGOCIO = "Panadería Doña Ema"

# Catálogo oficial: nombre correcto -> precio y categoría.
# Al limpiar, cada producto mal escrito se lleva a uno de estos nombres.
PRODUCTOS = {
    "Flauta":                         {"precio": 45,  "categoria": "Panes"},
    "Pan de masa madre (700 g)":      {"precio": 190, "categoria": "Panes"},
    "Pan integral con semillas":      {"precio": 160, "categoria": "Panes"},
    "Felipes (docena)":               {"precio": 120, "categoria": "Panes"},
    "Bizcochos surtidos (kilo)":      {"precio": 420, "categoria": "Bizcochos y dulces"},
    "Medialunas (docena)":            {"precio": 260, "categoria": "Bizcochos y dulces"},
    "Alfajor de maicena":             {"precio": 55,  "categoria": "Bizcochos y dulces"},
    "Pasta frola (porción)":          {"precio": 90,  "categoria": "Bizcochos y dulces"},
    "Torta de cumpleaños (encargo)":  {"precio": 950, "categoria": "Encargos"},
}

# Formas abreviadas o distintas que usa la gente en la caja.
# (Las diferencias de mayúsculas, tildes y plurales se resuelven solas en limpiar.py.)
ALIAS_PRODUCTOS = {
    "pan masa madre": "Pan de masa madre (700 g)",
    "masa madre": "Pan de masa madre (700 g)",
    "integral": "Pan integral con semillas",
    "pan integral": "Pan integral con semillas",
    "bizcocho": "Bizcochos surtidos (kilo)",
    "alfajor": "Alfajor de maicena",
    "pastafrola": "Pasta frola (porción)",
    "torta": "Torta de cumpleaños (encargo)",
    "torta cumpleano": "Torta de cumpleaños (encargo)",
    "felipe": "Felipes (docena)",
}

MEDIOS_DE_PAGO = ["Efectivo", "Débito", "Crédito", "Transferencia"]

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Colores de la panadería (los mismos de su página web).
COLORES = {
    "corteza": "6B3A1E",   # marrón oscuro: títulos
    "manteca": "F2B33D",   # amarillo: destacados
    "harina": "FBF4E9",    # crema: fondos
    "masa": "F3E3C7",      # beige: filas alternadas
    "texto": "2F2118",
    "texto2": "6A5444",
    "verde": "2E7D4F",     # subió
    "rojo": "B3412F",      # bajó
}
# Paleta para gráficos (de más oscuro a más claro).
PALETA = ["#6B3A1E", "#C9A464", "#F2B33D", "#874B27", "#A7C4A0", "#D98C5F", "#8E7CC3", "#5B8DB8", "#B3412F"]


def nombre_mes(fecha, con_anio=True):
    """Devuelve 'Octubre 2026' a partir de una fecha."""
    texto = MESES[fecha.month - 1].capitalize()
    return f"{texto} {fecha.year}" if con_anio else texto


def pesos(valor):
    """Formatea un número como '$ 12.345' (separador de miles uruguayo)."""
    return "$ " + f"{valor:,.0f}".replace(",", ".")
