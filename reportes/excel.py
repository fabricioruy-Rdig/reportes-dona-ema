"""Paso 4: armar el Excel con formato, tablas y gráficos.

Se usa openpyxl para controlar cada detalle: colores, anchos, formatos de
pesos y porcentajes, y gráficos propios de Excel (el cliente los puede tocar).

Conceptos de Python que aparecen acá:
- funciones auxiliares reutilizables (_tabla, _titulo) para no repetir código.
- argumentos con nombre y valores por defecto: def _tabla(..., formatos=None).
"""
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from .negocio import COLORES, NEGOCIO, PALETA

PESOS = '"$" #,##0'
PORCENTAJE = "0.0%"
NUMERO = "#,##0.##"

_relleno = lambda color: PatternFill("solid", start_color=color, end_color=color)  # noqa: E731
_linea = Side(style="thin", color="E2D3BC")


def _titulo(hoja, texto, subtitulo, ancho=12):
    hoja.sheet_view.showGridLines = False
    hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ancho)
    celda = hoja.cell(1, 1, texto)
    celda.font = Font(size=18, bold=True, color="FFFFFF")
    celda.fill = _relleno(COLORES["corteza"])
    celda.alignment = Alignment(vertical="center", indent=1)
    hoja.row_dimensions[1].height = 36
    for col in range(1, ancho + 1):
        hoja.cell(1, col).fill = _relleno(COLORES["corteza"])
    sub = hoja.cell(2, 1, subtitulo)
    sub.font = Font(size=11, italic=True, color=COLORES["texto2"])
    sub.alignment = Alignment(indent=1)
    hoja.row_dimensions[2].height = 22


def _subtitulo(hoja, fila, columna, texto):
    celda = hoja.cell(fila, columna, texto)
    celda.font = Font(size=13, bold=True, color=COLORES["corteza"])
    return celda


def _tabla(hoja, tabla, fila, columna, formatos=None, total=None):
    """Escribe un DataFrame con encabezado marrón y filas alternadas. Devuelve la última fila."""
    formatos = formatos or {}
    for j, nombre in enumerate(tabla.columns):
        c = hoja.cell(fila, columna + j, str(nombre))
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = _relleno(COLORES["corteza"])
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    hoja.row_dimensions[fila].height = 22
    for i, registro in enumerate(tabla.itertuples(index=False), start=1):
        for j, valor in enumerate(registro):
            if isinstance(valor, float) and pd.isna(valor):
                valor = None
            c = hoja.cell(fila + i, columna + j, valor)
            c.border = Border(bottom=_linea)
            if i % 2 == 0:
                c.fill = _relleno(COLORES["harina"])
            formato = formatos.get(tabla.columns[j])
            if formato:
                c.number_format = formato
    ultima = fila + len(tabla)
    if total:   # fila de total al pie: {"Producto": "Total", "Ventas": "sum"}
        ultima += 1
        for j, nombre in enumerate(tabla.columns):
            c = hoja.cell(ultima, columna + j)
            regla = total.get(nombre)
            if regla == "sum":
                letra = get_column_letter(columna + j)
                c.value = f"=SUM({letra}{fila + 1}:{letra}{ultima - 1})"
            elif regla:
                c.value = regla
            c.font = Font(bold=True, color=COLORES["corteza"])
            c.fill = _relleno(COLORES["masa"])
            c.border = Border(top=Side(style="medium", color=COLORES["corteza"]))
            if formatos.get(nombre):
                c.number_format = formatos[nombre]
    return ultima


def _anchos(hoja, anchos):
    for letra, ancho in anchos.items():
        hoja.column_dimensions[letra].width = ancho


def _tarjeta(hoja, fila, columna, etiqueta, valor, detalle="", formato=None, color_detalle=None):
    """Recuadro de 2 columnas con un número grande (como las tarjetas de un tablero)."""
    for r, (texto, fuente, alto) in enumerate([
        (etiqueta, Font(size=10, bold=True, color=COLORES["texto2"]), 20),
        (valor, Font(size=20, bold=True, color=COLORES["corteza"]), 34),
        (detalle, Font(size=10, bold=True, color=color_detalle or COLORES["texto2"]), 20),
    ]):
        hoja.merge_cells(start_row=fila + r, start_column=columna, end_row=fila + r, end_column=columna + 1)
        c = hoja.cell(fila + r, columna, texto)
        c.font = fuente
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if r == 1 and formato:
            c.number_format = formato
        for col in (columna, columna + 1):
            celda = hoja.cell(fila + r, col)
            celda.fill = _relleno(COLORES["harina"])
            separador = Side(style="thick", color="FFFFFF")   # espacio blanco entre tarjetas
            celda.border = Border(top=Side(style="thick", color=COLORES["manteca"]) if r == 0 else None,
                                  left=separador if col == columna else None, right=separador if col == columna + 1 else None)
        hoja.row_dimensions[fila + r].height = max(hoja.row_dimensions[fila + r].height or 15, alto)


def _etiquetas(porcentaje=False):
    """Etiquetas de datos limpias: solo el valor (o el porcentaje), sin nombre de serie ni categoría."""
    etiquetas = DataLabelList()
    etiquetas.showVal = not porcentaje
    etiquetas.showPercent = porcentaje
    etiquetas.showSerName = etiquetas.showCatName = etiquetas.showLegendKey = False
    if not porcentaje:
        etiquetas.numFmt = PESOS
    return etiquetas


def _grafico_barras(titulo, datos, categorias, color, horizontal=False, ancho=16, alto=8):
    grafico = BarChart()
    grafico.type = "bar" if horizontal else "col"
    grafico.title = titulo
    grafico.style = 10
    grafico.add_data(datos, titles_from_data=True)
    grafico.set_categories(categorias)
    grafico.legend = None
    grafico.width, grafico.height = ancho, alto
    serie = grafico.series[0]
    serie.graphicalProperties.solidFill = color
    serie.graphicalProperties.line.solidFill = color
    grafico.y_axis.numFmt = PESOS
    grafico.y_axis.majorGridlines = None
    grafico.y_axis.delete = False
    grafico.x_axis.delete = False
    if horizontal:
        grafico.x_axis.scaling.orientation = "maxMin"   # el más vendido arriba
    grafico.gapWidth = 60
    return grafico


# ---------------------------------------------------------------- hojas

def _hoja_resumen(libro, res, informe):
    hoja = libro.active
    hoja.title = "Resumen"
    _titulo(hoja, f"{NEGOCIO} · Reporte de ventas", f"{res.periodo} · generado el {datetime.now():%d/%m/%Y}")
    _anchos(hoja, {"A": 2} | {get_column_letter(c): 16 for c in range(2, 14)})

    u = res.ultimo
    _subtitulo(hoja, 4, 2, f"{u['mes']} (último mes)")
    if pd.notna(u["variacion"]):
        sube = u["variacion"] >= 0
        detalle = f"{'▲' if sube else '▼'} {abs(u['variacion']):.1%} vs {u['mes_anterior'].split()[0].lower()}".replace(".", ",")
        color = COLORES["verde"] if sube else COLORES["rojo"]
    else:
        detalle, color = "", None
    _tarjeta(hoja, 5, 2, "VENTAS DEL MES", u["ventas"], detalle, PESOS, color)
    _tarjeta(hoja, 5, 4, "COMPRAS (TICKETS)", u["tickets"], f"$ {u['ticket_promedio']:,.0f} promedio por compra".replace(",", "."), "#,##0")
    _tarjeta(hoja, 5, 6, "PRODUCTO ESTRELLA", u["estrella"], f"$ {u['estrella_ventas']:,.0f} en el mes".replace(",", "."))
    _tarjeta(hoja, 5, 8, "MEJOR DÍA", u["mejor_dia"], f"$ {u['mejor_dia_ventas']:,.0f} vendidos".replace(",", "."))
    hoja.cell(6, 6).font = Font(size=13, bold=True, color=COLORES["corteza"])  # el nombre del producto es largo

    _subtitulo(hoja, 10, 2, "Ventas por mes")
    meses = res.meses[["Mes", "Ventas", "Tickets", "Ticket promedio", "Devoluciones", "Variación"]]
    ultima = _tabla(hoja, meses, 11, 2, {"Ventas": PESOS, "Tickets": "#,##0", "Ticket promedio": PESOS,
                                          "Devoluciones": PESOS, "Variación": '+0.0%;[Red]-0.0%;0.0%'},
                    total={"Mes": "Total del período", "Ventas": "sum", "Tickets": "sum", "Devoluciones": "sum"})
    grafico = _grafico_barras("Ventas por mes", Reference(hoja, min_col=3, min_row=11, max_row=11 + len(meses)),
                              Reference(hoja, min_col=2, min_row=12, max_row=11 + len(meses)), COLORES["corteza"], ancho=13.5, alto=7.5)
    grafico.dataLabels = _etiquetas()
    hoja.add_chart(grafico, "B" + str(ultima + 3))

    fila = ultima + 3
    _subtitulo(hoja, fila, 7, "Limpieza de los datos")
    for i, linea in enumerate(informe.lineas(), start=1):
        c = hoja.cell(fila + i, 7, "✓ " + linea)
        c.font = Font(color=COLORES["texto"])
        hoja.merge_cells(start_row=fila + i, start_column=7, end_row=fila + i, end_column=11)
    hoja.cell(fila + len(informe.lineas()) + 2, 7,
              "Las filas apartadas están en la hoja «A revisar»." if informe.a_revisar else "No quedó nada pendiente de revisar."
              ).font = Font(italic=True, color=COLORES["texto2"])
    hoja.freeze_panes = "A3"


def _hoja_productos(libro, res):
    hoja = libro.create_sheet("Productos")
    _titulo(hoja, "Ventas por producto", f"{res.periodo} · ordenado de mayor a menor", ancho=10)
    tabla = res.productos
    meses = [c for c in tabla.columns if c not in ("Producto", "Unidades", "Total", "% del total")]
    tabla = tabla[["Producto", *meses, "Total", "% del total", "Unidades"]]
    formatos = {m: PESOS for m in meses} | {"Total": PESOS, "% del total": PORCENTAJE, "Unidades": NUMERO}
    ultima = _tabla(hoja, tabla, 4, 2, formatos,
                    total={"Producto": "Total", **{m: "sum" for m in meses}, "Total": "sum", "% del total": "sum"})
    _anchos(hoja, {"A": 2, "B": 32} | {get_column_letter(3 + i): 14 for i in range(len(meses) + 3)})
    col_total = 3 + len(meses)
    grafico = _grafico_barras("Total vendido por producto", Reference(hoja, min_col=col_total, min_row=4, max_row=4 + len(tabla)),
                              Reference(hoja, min_col=2, min_row=5, max_row=4 + len(tabla)), COLORES["manteca"],
                              horizontal=True, ancho=20, alto=9)
    hoja.add_chart(grafico, f"B{ultima + 3}")
    hoja.freeze_panes = "C5"


def _hoja_dias(libro, res):
    hoja = libro.create_sheet("Días y horarios")
    _titulo(hoja, "¿Cuándo se vende más?", "Promedio vendido en un día típico, por día de la semana y por hora", ancho=17)
    _subtitulo(hoja, 4, 2, "Promedio por día de la semana")
    ultima = _tabla(hoja, res.dias, 5, 2, {"Promedio por día": PESOS, "Días": "0"})
    grafico = _grafico_barras("Venta promedio según el día", Reference(hoja, min_col=3, min_row=5, max_row=5 + len(res.dias)),
                              Reference(hoja, min_col=2, min_row=6, max_row=5 + len(res.dias)), COLORES["corteza"], ancho=14, alto=7)
    hoja.add_chart(grafico, "F4")

    fila = max(ultima, 18) + 3
    _subtitulo(hoja, fila, 2, "Mapa de calor: venta promedio por hora (más oscuro = más ventas)")
    horas = res.horas.copy()
    horas.columns = [f"{h}:00" for h in horas.columns]
    horas = horas.reset_index()
    fin = _tabla(hoja, horas, fila + 1, 2, {c: '"$" #,##0;;"–"' for c in horas.columns[1:]})
    rango = f"C{fila + 2}:{get_column_letter(2 + len(horas.columns) - 1)}{fin}"
    hoja.conditional_formatting.add(rango, ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                                                          mid_type="percentile", mid_value=50, mid_color=COLORES["manteca"],
                                                          end_type="max", end_color="B5652B"))
    for col in range(3, 3 + len(horas.columns) - 1):
        hoja.column_dimensions[get_column_letter(col)].width = 9
    _anchos(hoja, {"A": 2, "B": 14, "C": 17})
    hoja.cell(fin + 2, 2, "Tip: los horarios más oscuros son los que necesitan más producción y más gente en el mostrador."
              ).font = Font(italic=True, color=COLORES["texto2"])


def _hoja_pagos(libro, res):
    hoja = libro.create_sheet("Medios de pago")
    _titulo(hoja, "Medios de pago", res.periodo, ancho=10)
    ultima = _tabla(hoja, res.pagos, 4, 2, {"Ventas": PESOS, "Operaciones": "#,##0", "% del total": PORCENTAJE},
                    total={"Medio de pago": "Total", "Ventas": "sum", "Operaciones": "sum", "% del total": "sum"})
    _anchos(hoja, {"A": 2, "B": 20, "C": 16, "D": 14, "E": 14})
    torta = PieChart()
    torta.title = "¿Cómo pagan los clientes?"
    torta.add_data(Reference(hoja, min_col=3, min_row=4, max_row=4 + len(res.pagos)), titles_from_data=True)
    torta.set_categories(Reference(hoja, min_col=2, min_row=5, max_row=4 + len(res.pagos)))
    for i in range(len(res.pagos)):
        punto = DataPoint(idx=i)
        punto.graphicalProperties.solidFill = PALETA[i].lstrip("#")
        torta.series[0].dPt.append(punto)
    torta.dataLabels = _etiquetas(porcentaje=True)
    torta.width, torta.height = 12, 8
    hoja.add_chart(torta, f"B{ultima + 3}")


def _hoja_datos(libro, ventas):
    hoja = libro.create_sheet("Ventas limpias")
    columnas = ["Fecha", "Hora", "Ticket", "Producto", "Categoría", "Cantidad", "Importe", "Medio de pago", "Tipo", "Archivo"]
    hoja.append(columnas)
    for fila in ventas[columnas].itertuples(index=False):
        hoja.append([fila[0].to_pydatetime(), *fila[1:]])
    fin = len(ventas) + 1
    for c in hoja["A"][1:]:
        c.number_format = "DD/MM/YYYY"
    for c in hoja["G"][1:]:
        c.number_format = PESOS
    tabla = Table(displayName="Ventas", ref=f"A1:J{fin}")
    tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium3", showRowStripes=True)
    hoja.add_table(tabla)   # trae filtros en cada columna
    hoja.freeze_panes = "A2"
    _anchos(hoja, {"A": 12, "B": 8, "C": 10, "D": 30, "E": 20, "F": 10, "G": 12, "H": 15, "I": 12, "J": 28})


def _hoja_revisar(libro, a_revisar):
    hoja = libro.create_sheet("A revisar")
    _titulo(hoja, "Filas para revisar a mano", "El programa no pudo decidir qué hacer con estas filas: no se sumaron al reporte.", ancho=8)
    tabla = a_revisar[["archivo", "fila_original", "motivo", "fecha", "producto", "cantidad", "total", "pago"]].copy()
    tabla.columns = ["Archivo", "Fila", "Motivo", "Fecha", "Producto", "Cantidad", "Importe", "Pago"]
    tabla = tabla.astype(object).where(tabla.notna(), None)
    tabla["Fecha"] = [f.strftime("%d/%m/%Y") if isinstance(f, (datetime, pd.Timestamp)) else f for f in tabla["Fecha"]]
    _tabla(hoja, tabla, 4, 2)
    _anchos(hoja, {"A": 2, "B": 28, "C": 8, "D": 52, "E": 12, "F": 22, "G": 10, "H": 10, "I": 14})


def crear_excel(ruta, ventas, a_revisar, res, informe):
    libro = Workbook()
    _hoja_resumen(libro, res, informe)
    _hoja_productos(libro, res)
    _hoja_dias(libro, res)
    _hoja_pagos(libro, res)
    _hoja_datos(libro, ventas)
    if len(a_revisar):
        _hoja_revisar(libro, a_revisar)
    for hoja in libro.worksheets:
        hoja.sheet_properties.tabColor = COLORES["manteca"] if hoja.title == "Resumen" else COLORES["corteza"]
        # Lista para imprimir: horizontal y ajustada al ancho de la hoja.
        hoja.page_setup.orientation = "landscape"
        hoja.page_setup.paperSize = hoja.PAPERSIZE_A4
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.fitToWidth, hoja.page_setup.fitToHeight = 1, 0
    libro.save(ruta)
    return ruta
