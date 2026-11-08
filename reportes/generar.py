"""Une los pasos: leer → limpiar → analizar → Excel → PDF.

La ventana usa esta función, pero también se puede usar desde la consola,
sin ventana (útil para automatizarlo todos los meses):

    python -m reportes.generar ejemplos/ventas-agosto-2026.csv ejemplos/ventas-septiembre-2026.xlsx

Conceptos de Python que aparecen acá:
- callback: la función recibe otra función (avisar) para ir contando cómo va.
- if __name__ == "__main__": código que corre solo cuando el archivo se ejecuta directo.
"""
import sys
from pathlib import Path

from .analizar import analizar
from .excel import crear_excel
from .leer import leer_archivos
from .limpiar import limpiar


def _nombre_seguro(texto):
    return "".join(c for c in texto if c not in '<>:"/\\|?*')


def generar(rutas, carpeta, excel=True, pdf=True, avisar=print):
    """Genera el reporte. avisar(texto, progreso) recibe mensajes y un número de 0 a 1."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    avisar("Leyendo archivos…", 0.05)
    tabla, avisos = leer_archivos(rutas)
    for aviso in avisos:
        avisar("📄 " + aviso, 0.15)

    avisar("Limpiando datos…", 0.25)
    ventas, a_revisar, informe = limpiar(tabla)
    for linea in informe.lineas():
        avisar("✓ " + linea, 0.4)
    if ventas.empty:
        raise ValueError("No quedó ninguna venta válida para armar el reporte.")

    avisar("Calculando resultados…", 0.5)
    resultados = analizar(ventas)

    base = carpeta / _nombre_seguro(f"Reporte de ventas - {resultados.periodo}")
    creados = {}
    try:
        if excel:
            avisar("Armando el Excel…", 0.6)
            creados["excel"] = crear_excel(base.with_suffix(".xlsx"), ventas, a_revisar, resultados, informe)
        if pdf:
            avisar("Armando el PDF…", 0.85)
            from .pdf import crear_pdf   # se importa acá porque matplotlib tarda un poco en cargar
            creados["pdf"] = crear_pdf(base.with_suffix(".pdf"), a_revisar, resultados, informe)
    except PermissionError as error:
        raise PermissionError(f"No se pudo guardar «{Path(error.filename).name}». "
                              "¿Está abierto en Excel o en otro programa? Cerralo y probá de nuevo.") from error

    avisar("Listo ✔", 1.0)
    return creados, informe, resultados


if __name__ == "__main__":
    archivos = sys.argv[1:]
    if not archivos:
        sys.exit("Uso: python -m reportes.generar archivo1.csv archivo2.xlsx …")
    resultado, _, _ = generar(archivos, Path(archivos[0]).parent / "Reportes",
                              avisar=lambda texto, progreso: print(texto))
    for tipo, ruta in resultado.items():
        print(f"{tipo.upper()}: {ruta}")
