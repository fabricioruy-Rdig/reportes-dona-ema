"""Paso 2: limpiar los datos y contar todo lo que se corrigió.

Arregla fechas, horas, importes, nombres de productos y medios de pago;
borra filas vacías y ventas repetidas, y separa lo que necesita que una
persona lo mire (por ejemplo, un producto que no está en el catálogo).

Conceptos de Python que aparecen acá:
- funciones chicas que hacen una sola cosa (más fáciles de probar).
- dataclass: una "ficha" con campos, para el informe de limpieza.
- difflib: comparar textos parecidos ("Medialunass" ~ "Medialunas").
"""
import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, time

import pandas as pd

from .negocio import ALIAS_PRODUCTOS, PRODUCTOS

PALABRAS_DE_RELLENO = {"de", "con", "c", "x", "la", "el", "por", "docena", "kilo", "kg", "porcion", "unidad",
                       "u", "g", "gr", "700", "encargo"}


@dataclass
class Informe:
    """Lo que se corrigió, para mostrarlo en la ventana y en el reporte."""
    filas_leidas: int = 0
    filas_vacias: int = 0
    duplicadas: int = 0
    nombres_corregidos: int = 0
    pagos_corregidos: int = 0
    fechas_convertidas: int = 0
    importes_convertidos: int = 0
    importes_completados: int = 0
    devoluciones: int = 0
    a_revisar: int = 0
    ejemplos_nombres: dict = field(default_factory=dict)  # "Medialunass" -> "Medialunas (docena)"

    def lineas(self):
        """El informe en frases simples."""
        texto = [f"Se leyeron {self.filas_leidas:,} filas.".replace(",", ".")]
        if self.filas_vacias:
            texto.append(f"Se quitaron {self.filas_vacias} filas vacías.")
        if self.duplicadas:
            texto.append(f"Se borraron {self.duplicadas} ventas registradas dos veces.")
        if self.nombres_corregidos:
            texto.append(f"Se unificaron {self.nombres_corregidos:,} nombres de productos mal escritos.".replace(",", "."))
        if self.pagos_corregidos:
            texto.append(f"Se unificaron {self.pagos_corregidos:,} medios de pago.".replace(",", "."))
        if self.fechas_convertidas:
            texto.append(f"Se pasaron {self.fechas_convertidas:,} fechas a un mismo formato.".replace(",", "."))
        if self.importes_convertidos:
            texto.append(f"Se convirtieron {self.importes_convertidos:,} importes escritos como texto.".replace(",", "."))
        if self.importes_completados:
            texto.append(f"Se completaron {self.importes_completados} importes vacíos con el precio de lista.")
        if self.devoluciones:
            texto.append(f"Se encontraron {self.devoluciones} devoluciones (se descuentan de las ventas).")
        if self.a_revisar:
            texto.append(f"{self.a_revisar} filas quedaron aparte para revisar a mano.")
        return texto


# ---------- textos ----------

def _clave(texto):
    """'MEDIALUNAS (Docena) ' -> 'medialuna'. Sirve para comparar nombres."""
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\(.*?\)", " ", texto)            # saca lo que está entre paréntesis
    palabras = []
    for palabra in re.findall(r"[a-z0-9]+", texto):
        if palabra in PALABRAS_DE_RELLENO:
            continue
        if re.search(r"(res|les|nes)$", palabra):      # alfajores -> alfajor, panes -> pan
            palabra = palabra[:-2]
        elif palabra.endswith("s") and len(palabra) > 3:  # medialunas -> medialuna
            palabra = palabra.rstrip("s")
        palabras.append(palabra)
    return " ".join(palabras)


# Diccionario de búsqueda: clave limpia -> nombre oficial.
_CATALOGO = {_clave(nombre): nombre for nombre in PRODUCTOS}
_CATALOGO.update({_clave(alias): nombre for alias, nombre in ALIAS_PRODUCTOS.items()})


def producto_oficial(texto):
    """Devuelve el nombre oficial del producto, o None si no se reconoce."""
    clave = _clave(texto)
    if not clave:
        return None
    if clave in _CATALOGO:
        return _CATALOGO[clave]
    parecido = difflib.get_close_matches(clave, _CATALOGO, n=1, cutoff=0.8)
    return _CATALOGO[parecido[0]] if parecido else None


def medio_de_pago(texto):
    t = _clave(texto)
    if not t:
        return "Sin dato"
    if t.startswith(("efec", "efvo", "cash", "contado")):
        return "Efectivo"
    if "deb" in t:
        return "Débito"
    if "cred" in t:
        return "Crédito"
    if "transf" in t or "mercado pago" in t or "mercadopago" in t:
        return "Transferencia"
    return "Otro"


# ---------- números y fechas ----------

def a_numero(valor):
    """'$ 1.200' -> 1200.0 · '0,5' -> 0.5 · 1200 -> 1200.0 · '' -> None"""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^\d,.\-]", "", str(valor))
    if not re.search(r"\d", texto):
        return None
    if "," in texto and "." in texto:          # 1.200,50
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:                         # 0,5
        texto = texto.replace(",", ".")
    elif re.search(r"\.\d{3}$", texto):        # 1.200 (punto de miles)
        texto = texto.replace(".", "")
    try:
        return float(texto)
    except ValueError:
        return None


FORMATOS_FECHA = ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y", "%Y/%m/%d"]


def a_fecha(valor):
    if isinstance(valor, datetime):
        return pd.Timestamp(valor).normalize()
    texto = str(valor).strip().split(" ")[0]
    for formato in FORMATOS_FECHA:
        try:
            return pd.Timestamp(datetime.strptime(texto, formato))
        except ValueError:
            continue
    return None


def a_hora(valor):
    if isinstance(valor, time):
        return valor.hour, valor.minute
    m = re.match(r"\s*(\d{1,2})[:.](\d{2})", str(valor))
    if m and int(m.group(1)) < 24:
        return int(m.group(1)), int(m.group(2))
    return None


# ---------- limpieza completa ----------

def limpiar(tabla):
    """Recibe la tabla leída y devuelve (ventas limpias, filas a revisar, informe)."""
    informe = Informe()
    datos = tabla.copy()

    vacia = datos[["fecha", "producto", "total", "cantidad"]].apply(
        lambda fila: all(pd.isna(v) or str(v).strip() == "" for v in fila), axis=1)
    informe.filas_vacias = int(vacia.sum())
    datos = datos[~vacia]
    informe.filas_leidas = len(datos)

    revisar = []

    def apartar(fila, motivo):
        revisar.append({**fila, "motivo": motivo})

    limpias = []
    for fila in datos.to_dict("records"):
        # Fecha
        fecha = a_fecha(fila["fecha"])
        if fecha is None:
            apartar(fila, f"Fecha que no se entiende: «{fila['fecha']}»"); continue
        if not isinstance(fila["fecha"], datetime) and not re.fullmatch(r"\d{2}/\d{2}/\d{4}", str(fila["fecha"]).strip()):
            informe.fechas_convertidas += 1

        # Producto
        original = str(fila["producto"] or "").strip()
        producto = producto_oficial(original)
        if producto is None:
            apartar(fila, f"Producto que no está en el catálogo: «{original}»"); continue
        if original != producto:
            informe.nombres_corregidos += 1
            informe.ejemplos_nombres.setdefault(original, producto)

        # Cantidad, precio e importe
        cantidad = a_numero(fila["cantidad"])
        cantidad = 1.0 if cantidad is None else cantidad
        precio = PRODUCTOS[producto]["precio"]
        total = a_numero(fila["total"])
        if total is None:
            total = round(cantidad * precio)
            informe.importes_completados += 1
        elif isinstance(fila["total"], str) and not re.fullmatch(r"-?\d+", fila["total"].strip()):
            informe.importes_convertidos += 1
        if abs(total) < precio * 0.2:   # un importe absurdo (ej. $ 1 por una torta)
            apartar(fila, f"Importe que no cierra: {fila['total']} por {cantidad:g} × {producto}"); continue

        # Medio de pago
        pago = medio_de_pago(fila["pago"])
        if str(fila["pago"] or "").strip() != pago:
            informe.pagos_corregidos += 1

        hora = a_hora(fila["hora"])
        es_devolucion = total < 0 or cantidad < 0
        informe.devoluciones += int(es_devolucion)
        limpias.append({
            "Fecha": fecha,
            "Hora": f"{hora[0]:02d}:{hora[1]:02d}" if hora else "",
            "hora_num": hora[0] if hora else None,
            "Ticket": str(fila["ticket"]).strip().removesuffix(".0") if pd.notna(fila["ticket"]) else "",
            "Producto": producto,
            "Categoría": PRODUCTOS[producto]["categoria"],
            "Cantidad": -abs(cantidad) if es_devolucion else abs(cantidad),
            "Importe": -abs(total) if es_devolucion else abs(total),
            "Medio de pago": pago,
            "Tipo": "Devolución" if es_devolucion else "Venta",
            "Archivo": fila["archivo"],
        })

    ventas = pd.DataFrame(limpias)
    antes = len(ventas)
    ventas = ventas.drop_duplicates(subset=["Fecha", "Hora", "Ticket", "Producto", "Cantidad", "Importe", "Tipo"])
    informe.duplicadas = antes - len(ventas)
    ventas = ventas.sort_values(["Fecha", "Hora", "Ticket"]).reset_index(drop=True)

    a_revisar = pd.DataFrame(revisar)
    informe.a_revisar = len(a_revisar)
    return ventas, a_revisar, informe


