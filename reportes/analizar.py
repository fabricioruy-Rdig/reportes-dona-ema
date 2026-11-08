"""Paso 3: sacar los números del reporte a partir de las ventas limpias.

Conceptos de Python que aparecen acá:
- groupby: agrupar filas (por mes, por producto...) y sumar, como una tabla dinámica.
- pivot_table: tabla de doble entrada (día de la semana × hora).
- dataclass: devolver todos los resultados juntos y con nombre.
"""
from dataclasses import dataclass

import pandas as pd

from .negocio import DIAS, MEDIOS_DE_PAGO, nombre_mes


@dataclass
class Resultados:
    periodo: str               # "Agosto a octubre 2026"
    meses: pd.DataFrame        # una fila por mes: ventas, tickets, ticket promedio, variación
    ultimo: dict               # números del último mes (para las tarjetas del resumen)
    productos: pd.DataFrame    # ventas por producto y por mes
    dias: pd.DataFrame         # promedio vendido por día de la semana
    horas: pd.DataFrame        # promedio por día de la semana y hora (mapa de calor)
    pagos: pd.DataFrame        # ventas por medio de pago


def _tickets(tabla):
    """Cantidad de compras: tickets distintos (o filas, si el archivo no traía ticket)."""
    con_ticket = tabla[tabla["Ticket"] != ""]
    return con_ticket.groupby(["Fecha", "Ticket"]).ngroups + (tabla["Ticket"] == "").sum()


def _periodo(meses):
    primero, ultimo = meses[0], meses[-1]
    if primero == ultimo:
        return nombre_mes(primero)
    if primero.year == ultimo.year:
        return f"{nombre_mes(primero, False)} a {nombre_mes(ultimo, False).lower()} {ultimo.year}"
    return f"{nombre_mes(primero)} a {nombre_mes(ultimo).lower()}"


def analizar(ventas):
    ventas = ventas.copy()
    ventas["Mes"] = ventas["Fecha"].dt.to_period("M")
    solo_ventas = ventas[ventas["Tipo"] == "Venta"]

    # --- Por mes ---
    filas = []
    for mes, grupo in ventas.groupby("Mes"):
        tickets = _tickets(grupo[grupo["Tipo"] == "Venta"])
        total = grupo["Importe"].sum()
        filas.append({"Mes": nombre_mes(mes.to_timestamp()), "periodo": mes, "Ventas": total, "Tickets": tickets,
                      "Ticket promedio": total / tickets if tickets else 0,
                      "Días con ventas": grupo["Fecha"].nunique(),
                      "Devoluciones": -grupo.loc[grupo["Tipo"] == "Devolución", "Importe"].sum()})
    meses = pd.DataFrame(filas)
    meses["Variación"] = meses["Ventas"].pct_change()

    # --- Último mes: las tarjetas del resumen ---
    ultimo_mes = meses.iloc[-1]
    del_mes = solo_ventas[solo_ventas["Mes"] == ultimo_mes["periodo"]]
    por_dia = del_mes.groupby("Fecha")["Importe"].sum()
    mejor_fecha = por_dia.idxmax()
    estrella = del_mes.groupby("Producto")["Importe"].sum().sort_values(ascending=False)
    ultimo = {
        "mes": ultimo_mes["Mes"],
        "ventas": ultimo_mes["Ventas"],
        "tickets": int(ultimo_mes["Tickets"]),
        "ticket_promedio": ultimo_mes["Ticket promedio"],
        "variacion": ultimo_mes["Variación"],
        "mes_anterior": meses.iloc[-2]["Mes"] if len(meses) > 1 else None,
        "estrella": estrella.index[0],
        "estrella_ventas": estrella.iloc[0],
        "mejor_dia": f"{DIAS[mejor_fecha.weekday()]} {mejor_fecha.day}",
        "mejor_dia_ventas": por_dia.max(),
    }

    # --- Por producto (columnas por mes + total) ---
    productos = ventas.pivot_table(index="Producto", columns="Mes", values="Importe", aggfunc="sum", fill_value=0)
    productos.columns = [nombre_mes(m.to_timestamp(), False) for m in productos.columns]
    productos["Unidades"] = ventas.groupby("Producto")["Cantidad"].sum()
    productos["Total"] = productos[[c for c in productos.columns if c != "Unidades"]].sum(axis=1)
    productos["% del total"] = productos["Total"] / productos["Total"].sum()
    productos = productos.sort_values("Total", ascending=False).reset_index()

    # --- Por día de la semana: promedio de lo vendido en un día ---
    diario = solo_ventas.groupby("Fecha")["Importe"].sum().to_frame()
    diario["Día"] = [DIAS[f.weekday()] for f in diario.index]
    dias = diario.groupby("Día")["Importe"].agg(["mean", "count"]).reindex(DIAS)
    dias = dias.rename(columns={"mean": "Promedio por día", "count": "Días"}).reset_index()

    # --- Mapa de calor: promedio por día de la semana y hora ---
    con_hora = solo_ventas.dropna(subset=["hora_num"]).copy()
    con_hora["Día"] = [DIAS[f.weekday()] for f in con_hora["Fecha"]]
    con_hora["Hora"] = con_hora["hora_num"].astype(int)
    cantidad_de_dias = diario.groupby("Día").size()
    horas = con_hora.pivot_table(index="Día", columns="Hora", values="Importe", aggfunc="sum", fill_value=0)
    horas = horas.div(cantidad_de_dias.reindex(horas.index), axis=0).reindex(DIAS).fillna(0)

    # --- Medios de pago ---
    pagos = solo_ventas.groupby("Medio de pago")["Importe"].agg(["sum", "count"])
    orden = [m for m in MEDIOS_DE_PAGO if m in pagos.index] + [m for m in pagos.index if m not in MEDIOS_DE_PAGO]
    pagos = pagos.reindex(orden).rename(columns={"sum": "Ventas", "count": "Operaciones"})
    pagos["% del total"] = pagos["Ventas"] / pagos["Ventas"].sum()
    pagos = pagos.reset_index()

    return Resultados(_periodo([m.to_timestamp() for m in meses["periodo"]]), meses.drop(columns="periodo"),
                      ultimo, productos, dias, horas, pagos)
