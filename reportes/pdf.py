"""Paso 5: el resumen en PDF (2 páginas), listo para imprimir o mandar por WhatsApp.

Los gráficos se dibujan con matplotlib y se pegan como imágenes; el PDF se
arma con fpdf2. La tipografía es DejaVu Sans, que viene incluida con
matplotlib: así las tildes, la ñ y los símbolos ▲▼ se ven bien en cualquier PC.

Conceptos de Python que aparecen acá:
- clases y herencia: class Documento(FPDF) agrega encabezado y pie a cada página.
- io.BytesIO: un "archivo" en memoria, para pasar la imagen sin guardarla en disco.
- with: abre algo y lo cierra solo al terminar.
"""
import io
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")   # dibujar sin abrir ventanas
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from fpdf import FPDF  # noqa: E402

from .negocio import COLORES, NEGOCIO, PALETA, pesos  # noqa: E402

FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
_rgb = lambda hexa: tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))  # noqa: E731
CORTEZA, MANTECA, HARINA, TEXTO, TEXTO2 = (_rgb(COLORES[c]) for c in ("corteza", "manteca", "harina", "texto", "texto2"))

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#C9B79C", "axes.titleweight": "bold",
                     "axes.titlesize": 11, "axes.titlecolor": "#" + COLORES["corteza"], "axes.titlelocation": "left"})


def _miles(valor, _=None):
    return pesos(valor)


def _imagen(figura):
    memoria = io.BytesIO()
    figura.savefig(memoria, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(figura)
    memoria.seek(0)
    return memoria


# ---------------------------------------------------------------- gráficos

def _grafico_meses(meses):
    figura, eje = plt.subplots(figsize=(6.4, 2.6))
    barras = eje.bar(meses["Mes"], meses["Ventas"], color=PALETA[0], width=0.55)
    for barra, valor, variacion in zip(barras, meses["Ventas"], meses["Variación"]):
        texto = pesos(valor)
        if not np.isnan(variacion):
            texto += f"\n{'▲' if variacion >= 0 else '▼'} {abs(variacion):.1%}".replace(".", ",")
        eje.annotate(texto, (barra.get_x() + barra.get_width() / 2, barra.get_height()), ha="center", va="bottom",
                     xytext=(0, 3), textcoords="offset points", fontsize=8.5, fontweight="bold", color="#" + COLORES["texto"])
    eje.yaxis.set_major_formatter(_miles)
    eje.set_ylim(0, meses["Ventas"].max() * 1.3)
    eje.set_title("Ventas por mes")
    return _imagen(figura)


def _grafico_productos(productos):
    datos = productos.head(9).iloc[::-1]
    figura, eje = plt.subplots(figsize=(6.4, 3.1))
    eje.barh(datos["Producto"], datos["Total"], color=PALETA[2], height=0.6)
    for y, (valor, parte) in enumerate(zip(datos["Total"], datos["% del total"])):
        eje.text(valor, y, f"  {pesos(valor)} · {parte:.0%}", va="center", fontsize=8, color="#" + COLORES["texto"])
    eje.xaxis.set_major_formatter(_miles)
    eje.set_xlim(0, datos["Total"].max() * 1.35)
    eje.set_title("Qué se vende más (todo el período)")
    return _imagen(figura)


def _grafico_calor(horas):
    figura, eje = plt.subplots(figsize=(6.6, 2.7))
    colores = matplotlib.colors.LinearSegmentedColormap.from_list("pan", ["#FFFFFF", "#" + COLORES["manteca"], "#B5652B", "#" + COLORES["corteza"]])
    imagen = eje.imshow(horas.values, aspect="auto", cmap=colores)
    eje.set_xticks(range(len(horas.columns)), [f"{h}h" for h in horas.columns])
    eje.set_yticks(range(len(horas.index)), horas.index)
    eje.tick_params(length=0)
    for lado in eje.spines.values():
        lado.set_visible(False)
    barra = figura.colorbar(imagen, ax=eje, fraction=0.03, pad=0.02, format=matplotlib.ticker.FuncFormatter(_miles))
    barra.outline.set_visible(False)
    eje.set_title("¿A qué hora se vende más? (venta promedio por hora)")
    return _imagen(figura)


def _grafico_dias(dias):
    figura, eje = plt.subplots(figsize=(3.4, 2.6))
    colores = [PALETA[0] if v == dias["Promedio por día"].max() else PALETA[1] for v in dias["Promedio por día"]]
    eje.bar([d[:3] for d in dias["Día"]], dias["Promedio por día"], color=colores, width=0.6)
    eje.yaxis.set_major_formatter(_miles)
    eje.set_title("Venta promedio por día")
    return _imagen(figura)


def _grafico_pagos(pagos):
    figura, eje = plt.subplots(figsize=(3.4, 2.6))
    _, _, porcentajes = eje.pie(pagos["Ventas"], labels=pagos["Medio de pago"], colors=PALETA[:len(pagos)], startangle=90,
                                counterclock=False, autopct=lambda p: f"{p:.0f}%", pctdistance=0.78,
                                wedgeprops={"width": 0.42, "edgecolor": "white"}, textprops={"fontsize": 8})
    for texto, color in zip(porcentajes, PALETA):
        if color in ("#6B3A1E", "#874B27"):   # sobre los colores oscuros, el número va en blanco
            texto.set_color("white")
    eje.set_title("Cómo pagan los clientes")
    return _imagen(figura)


# ---------------------------------------------------------------- documento

class Documento(FPDF):
    def __init__(self, periodo):
        super().__init__(format="A4")
        self.periodo = periodo
        self.add_font("DejaVu", "", str(FUENTES / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FUENTES / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", str(FUENTES / "DejaVuSans-Oblique.ttf"))
        self.set_auto_page_break(True, margin=16)
        self.set_margins(14, 14, 14)

    def header(self):
        self.set_fill_color(*CORTEZA)
        self.rect(0, 0, self.w, 24, "F")
        self.set_xy(14, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 15)
        self.cell(0, 7, NEGOCIO)
        self.set_xy(14, 13.5)
        self.set_font("DejaVu", "", 10)
        self.set_text_color(*_rgb("F3E3C7"))
        self.cell(0, 6, f"Reporte de ventas · {self.periodo}")
        self.set_y(30)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "I", 7.5)
        self.set_text_color(*TEXTO2)
        self.cell(0, 5, f"Generado automáticamente el {datetime.now():%d/%m/%Y %H:%M}", align="L")
        self.cell(0, 5, f"Página {self.page_no()} de {{nb}}", align="R")

    def titulo(self, texto):
        self.set_font("DejaVu", "B", 11.5)
        self.set_text_color(*CORTEZA)
        self.cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT")

    def tarjetas(self, datos):
        ancho = (self.w - self.l_margin - self.r_margin - 3 * 3) / 4
        y = self.get_y()
        for i, (etiqueta, valor, detalle, color) in enumerate(datos):
            x = self.l_margin + i * (ancho + 3)
            self.set_fill_color(*HARINA)
            self.rect(x, y, ancho, 24, "F")
            self.set_fill_color(*MANTECA)
            self.rect(x, y, ancho, 1.2, "F")
            self.set_xy(x, y + 3)
            self.set_font("DejaVu", "B", 7)
            self.set_text_color(*TEXTO2)
            self.cell(ancho, 4, etiqueta.upper(), align="C")
            self.set_xy(x, y + 8)
            self.set_font("DejaVu", "B", 14 if len(valor) <= 12 else 10)
            self.set_text_color(*CORTEZA)
            self.cell(ancho, 7, valor, align="C")
            self.set_xy(x, y + 16.5)
            self.set_font("DejaVu", "B", 7.5)
            self.set_text_color(*(color or TEXTO2))
            self.cell(ancho, 4, detalle, align="C")
        self.set_y(y + 28)


def crear_pdf(ruta, a_revisar, res, informe):
    doc = Documento(res.periodo)
    doc.set_title(f"{NEGOCIO} · Reporte de ventas · {res.periodo}")
    doc.set_author(NEGOCIO)
    ancho = doc.w - doc.l_margin - doc.r_margin

    # ---- Página 1: el mes y lo que más se vende
    doc.add_page()
    u = res.ultimo
    doc.titulo(f"{u['mes']}: el último mes")
    if not np.isnan(u["variacion"]):
        sube = u["variacion"] >= 0
        variacion = (f"{'▲' if sube else '▼'} {abs(u['variacion']):.1%} vs {u['mes_anterior'].split()[0].lower()}".replace(".", ","),
                     _rgb(COLORES["verde" if sube else "rojo"]))
    else:
        variacion = ("", None)
    doc.tarjetas([
        ("Ventas del mes", pesos(u["ventas"]), *variacion),
        ("Compras (tickets)", f"{u['tickets']:,}".replace(",", "."), f"{pesos(u['ticket_promedio'])} promedio", None),
        ("Producto estrella", u["estrella"], f"{pesos(u['estrella_ventas'])} en el mes", None),
        ("Mejor día", u["mejor_dia"], f"{pesos(u['mejor_dia_ventas'])} vendidos", None),
    ])
    doc.image(_grafico_meses(res.meses), w=ancho)
    doc.ln(3)
    doc.image(_grafico_productos(res.productos), w=ancho)

    # ---- Página 2: cuándo y cómo se vende + calidad de los datos
    doc.add_page()
    doc.image(_grafico_calor(res.horas), w=ancho)
    doc.ln(2)
    y = doc.get_y()
    mitad = (ancho - 4) / 2
    doc.image(_grafico_dias(res.dias), x=doc.l_margin, y=y, w=mitad)
    doc.image(_grafico_pagos(res.pagos), x=doc.l_margin + mitad + 4, y=y, w=mitad)
    doc.set_y(y + mitad * 2.6 / 3.4 + 4)

    doc.titulo("Limpieza de los datos")
    doc.set_font("DejaVu", "", 8.5)
    doc.set_text_color(*TEXTO)
    for linea in informe.lineas():
        doc.cell(0, 4.6, "✓  " + linea, new_x="LMARGIN", new_y="NEXT")
    if len(a_revisar):
        doc.ln(1)
        doc.set_font("DejaVu", "I", 8)
        doc.set_text_color(*TEXTO2)
        doc.multi_cell(0, 4.2, "Las filas apartadas (por ejemplo, productos que no están en el catálogo) se detallan "
                               "en la hoja «A revisar» del Excel y no se sumaron a este reporte.")
    doc.output(str(ruta))
    return ruta
