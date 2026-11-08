"""Genera los archivos de ventas de ejemplo (agosto, septiembre y octubre de 2026).

Simulan lo que exporta una caja real, con los errores típicos que el programa
tiene que arreglar: nombres escritos de mil formas, fechas e importes en
distintos formatos, filas vacías, ventas repetidas y devoluciones.

Se ejecuta una sola vez:  python herramientas/crear_ejemplos.py
Usa una "semilla" fija, así que siempre genera exactamente los mismos datos.
"""
import calendar
import csv
import random
import sys
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reportes.negocio import PRODUCTOS  # noqa: E402

CARPETA = Path(__file__).resolve().parent.parent / "ejemplos"
azar = random.Random(2026)

# Cómo escriben cada producto en la caja (el primero es el más común).
VARIANTES = {
    "Flauta": ["Flauta", "flauta", "FLAUTA", "Flautas", "flauta "],
    "Pan de masa madre (700 g)": ["Pan de masa madre (700 g)", "Pan masa madre", "pan de masa madre", "MASA MADRE"],
    "Pan integral con semillas": ["Pan integral con semillas", "Pan integral", "pan integral c/semillas", "Integral"],
    "Felipes (docena)": ["Felipes (docena)", "Felipes", "felipe x docena", "FELIPES"],
    "Bizcochos surtidos (kilo)": ["Bizcochos surtidos (kilo)", "Bizcochos", "bizcocho surtido", "Bizcochos x kg"],
    "Medialunas (docena)": ["Medialunas (docena)", "Medialunas", "medialuna x docena", "MEDIALUNAS (DOCENA)", "Medialunass"],
    "Alfajor de maicena": ["Alfajor de maicena", "Alfajor", "alfajores de maicena", "ALFAJOR MAICENA"],
    "Pasta frola (porción)": ["Pasta frola (porción)", "Pasta frola", "pastafrola", "Pasta Frola porcion"],
    "Torta de cumpleaños (encargo)": ["Torta de cumpleaños (encargo)", "Torta cumpleaños", "TORTA (ENCARGO)"],
}
PAGOS = {"Efectivo": ["Efectivo", "EFECTIVO", "efvo", "Efectivo "], "Débito": ["Débito", "debito", "Tarjeta débito", "DEBITO"],
         "Crédito": ["Crédito", "credito", "Tarjeta crédito"], "Transferencia": ["Transferencia", "transf.", "Transf", "Mercado Pago"]}

# Qué tan seguido se vende cada producto y cuántas unidades por compra.
PESO = {"Flauta": 30, "Pan de masa madre (700 g)": 7, "Pan integral con semillas": 6, "Felipes (docena)": 8,
        "Bizcochos surtidos (kilo)": 14, "Medialunas (docena)": 14, "Alfajor de maicena": 9, "Pasta frola (porción)": 8,
        "Torta de cumpleaños (encargo)": 0.4}
CANTIDAD = {"Flauta": [1, 1, 2, 2, 3, 4], "Bizcochos surtidos (kilo)": [0.25, 0.5, 0.5, 0.5, 1],
            "Medialunas (docena)": [0.5, 0.5, 1, 1, 2], "Felipes (docena)": [0.5, 1, 1],
            "Alfajor de maicena": [1, 1, 2, 3], "Pasta frola (porción)": [1, 1, 2]}
# Horario de mayor movimiento: mañana temprano y la merienda.
HORAS = {7: 9, 8: 12, 9: 10, 10: 7, 11: 5, 12: 5, 13: 4, 14: 2, 15: 3, 16: 6, 17: 10, 18: 11, 19: 8, 20: 3}
CRECIMIENTO = {8: 1.00, 9: 1.04, 10: 1.13}  # la primavera trae más clientes


def ventas_del_mes(anio, mes):
    filas, ticket = [], 1000 * mes
    for dia in range(1, calendar.monthrange(anio, mes)[1] + 1):
        fecha = date(anio, mes, dia)
        domingo = fecha.weekday() == 6
        base = {5: 95, 6: 70}.get(fecha.weekday(), 62)  # sábado y domingo se vende más
        horas = [h for h in HORAS if (h < 13 if domingo else h <= 20)]
        clientes = round(base * CRECIMIENTO[mes] * azar.uniform(0.85, 1.15))
        momentos = sorted(time(h, azar.randrange(0, 60)) for h in azar.choices(horas, [HORAS[h] for h in horas], k=clientes))
        for momento in momentos:  # los tickets van en orden de hora, como en una caja real
            pago = azar.choices(list(PAGOS), [46, 30, 6, 18])[0]
            ticket += 1
            productos = list(PESO)
            for producto in set(azar.choices(productos, [PESO[p] for p in productos], k=azar.choice([1, 1, 2, 2, 3]))):
                cantidad = 1 if "Torta" in producto else azar.choice(CANTIDAD.get(producto, [1, 1, 2]))
                filas.append({"fecha": fecha, "hora": momento, "ticket": ticket, "producto": producto,
                              "cantidad": cantidad, "precio": PRODUCTOS[producto]["precio"], "pago": pago})
    return filas


def ensuciar(filas):
    """Agrega los errores típicos de una caja real."""
    sucias = []
    for f in filas:
        f = dict(f)
        f["producto_txt"] = azar.choices(VARIANTES[f["producto"]], [70] + [30 / (len(VARIANTES[f["producto"]]) - 1)] * (len(VARIANTES[f["producto"]]) - 1))[0]
        f["pago_txt"] = azar.choices(PAGOS[f["pago"]], [70] + [30 / (len(PAGOS[f["pago"]]) - 1)] * (len(PAGOS[f["pago"]]) - 1))[0]
        f["total"] = round(f["cantidad"] * f["precio"])
        if azar.random() < 0.012:
            f["total"] = None                      # importe sin cargar
        sucias.append(f)
        if azar.random() < 0.006:
            sucias.append(dict(f))                 # venta registrada dos veces
        if azar.random() < 0.004:                  # devolución
            d = dict(f); d["cantidad"] = -f["cantidad"]; d["total"] = -round(f["cantidad"] * f["precio"]); sucias.append(d)
        if azar.random() < 0.003:
            sucias.append(None)                    # fila vacía
    # Un par de errores que sí necesitan que alguien los mire.
    muestra = azar.choice(filas)
    sucias.insert(len(sucias) // 3, {**muestra, "producto_txt": "Prueba sistema", "pago_txt": "Efectivo", "total": 1, "cantidad": 1})
    sucias.insert(len(sucias) // 2, {**muestra, "producto_txt": "Pan dulce", "pago_txt": "Débito", "total": 480, "cantidad": 1})
    return sucias


def importe_texto(valor, estilo):
    if valor is None:
        return ""
    if estilo == "pesos":
        return "$ " + f"{valor:,.0f}".replace(",", ".")
    return str(valor)


def agosto():
    filas = ensuciar(ventas_del_mes(2026, 8))
    with open(CARPETA / "ventas-agosto-2026.csv", "w", newline="", encoding="utf-8-sig") as archivo:
        w = csv.writer(archivo, delimiter=";")
        w.writerow(["Fecha", "Hora", "Ticket", "Producto", "Cantidad", "Precio unitario", "Total", "Medio de pago"])
        for f in filas:
            if f is None:
                w.writerow([""] * 8); continue
            w.writerow([f["fecha"].strftime("%d/%m/%Y"), f["hora"].strftime("%H:%M"), f["ticket"], f["producto_txt"],
                        str(f["cantidad"]).replace(".", ","), f["precio"], "" if f["total"] is None else f["total"], f["pago_txt"]])
    return len(filas)


def septiembre():
    """Otra versión del sistema de caja: Excel con títulos arriba y columnas con otros nombres."""
    filas = ensuciar(ventas_del_mes(2026, 9))
    libro = Workbook(); hoja = libro.active; hoja.title = "Ventas"
    hoja.append(["Caja Doña Ema - Reporte de ventas"])
    hoja.append(["Período: 01/09/2026 al 30/09/2026"])
    hoja.append([])
    hoja.append(["Fecha venta", "Hora", "Nº ticket", "Artículo", "Cant.", "Importe", "Forma de pago"])
    for f in filas:
        if f is None:
            hoja.append([]); continue
        hoja.append([datetime.combine(f["fecha"], time()), f["hora"].strftime("%H:%M"), f["ticket"], f["producto_txt"],
                     f["cantidad"], f["total"], f["pago_txt"]])
    for celda in hoja["A"][4:]:
        celda.number_format = "DD/MM/YYYY"
    libro.save(CARPETA / "ventas-septiembre-2026.xlsx")
    return len(filas)


def octubre():
    """Exportación con fechas mezcladas e importes como texto."""
    filas = ensuciar(ventas_del_mes(2026, 10))
    with open(CARPETA / "ventas-octubre-2026.csv", "w", newline="", encoding="utf-8") as archivo:
        w = csv.writer(archivo)
        w.writerow(["fecha", "hora", "ticket", "producto", "cantidad", "total", "pago"])
        for i, f in enumerate(filas):
            if f is None:
                w.writerow([""] * 7); continue
            fecha = f["fecha"].strftime("%Y-%m-%d") if i % 5 else f"{f['fecha'].day}/{f['fecha'].month}/{f['fecha'].strftime('%y')}"
            w.writerow([fecha, f["hora"].strftime("%H:%M"), f["ticket"], f["producto_txt"], f["cantidad"],
                        importe_texto(f["total"], "pesos" if i % 3 else "simple"), f["pago_txt"]])
    return len(filas)


if __name__ == "__main__":
    CARPETA.mkdir(exist_ok=True)
    print("Agosto:", agosto(), "filas")
    print("Septiembre:", septiembre(), "filas")
    print("Octubre:", octubre(), "filas")
    print("Listo: archivos en", CARPETA)
