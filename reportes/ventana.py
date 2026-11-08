"""La ventana del programa (customtkinter).

Pasos para el usuario: 1) elegir los archivos de ventas, 2) elegir dónde
guardar, 3) tocar «Generar reporte». El trabajo pesado corre en un hilo
aparte para que la ventana no se congele mientras tanto.

Conceptos de Python que aparecen acá:
- clases: la ventana es un objeto con sus partes (self.boton, self.lista…).
- threading + queue: un hilo trabaja y deja mensajes en una cola; la ventana
  los lee cada 100 ms con after(). (tkinter no permite tocar la ventana
  desde otro hilo, por eso se usa la cola.)
- lambda: funciones cortas de una línea, útiles para los botones.
"""
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from .generar import generar
from .leer import ErrorDeArchivo
from .negocio import NEGOCIO

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
EJEMPLOS = CARPETA_PROYECTO / "ejemplos"

# Colores (claro, oscuro)
CORTEZA = ("#6B3A1E", "#C98B5A")
CORTEZA_HOVER = ("#874B27", "#B07548")
MANTECA = "#F2B33D"
FONDO = ("#FBF4E9", "#1F1B18")
TARJETA = ("#FFFFFF", "#2B2622")
TEXTO2 = ("#6A5444", "#BBA894")


def corta(ruta, largo=46):
    """Acorta una ruta larga para mostrarla: '…\\Ventas\\Reportes'."""
    texto = str(ruta)
    if len(texto) <= largo:
        return texto
    partes = Path(ruta).parts
    resultado = partes[-1]
    for parte in reversed(partes[:-1]):
        if len(resultado) + len(parte) + 3 > largo:
            break
        resultado = str(Path(parte) / resultado)
    return "…" + os.sep + resultado


def abrir(ruta):
    """Abre un archivo o carpeta con el programa predeterminado del sistema."""
    if sys.platform.startswith("win"):
        os.startfile(ruta)  # noqa: S606 (solo existe en Windows)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(ruta)])


class Ventana(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(f"Reportes de ventas · {NEGOCIO}")
        self.geometry("980x640")
        self.minsize(860, 580)
        self.configure(fg_color=FONDO)

        self.archivos = []
        self.carpeta = None          # None = una carpeta «Reportes» junto a los archivos
        self.creados = {}
        self.mensajes = queue.Queue()

        self.grid_columnconfigure(0, weight=5, uniform="col")
        self.grid_columnconfigure(1, weight=6, uniform="col")
        self.grid_rowconfigure(1, weight=1)
        self._encabezado()
        self._panel_pasos()
        self._panel_informe()
        self._actualizar()

    # ------------------------------------------------------------ armado

    def _encabezado(self):
        barra = ctk.CTkFrame(self, fg_color=CORTEZA, corner_radius=0, height=74)
        barra.grid(row=0, column=0, columnspan=2, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(barra, text=f"🥐  {NEGOCIO}", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="white").grid(row=0, column=0, sticky="w", padx=24, pady=(14, 0))
        ctk.CTkLabel(barra, text="Reporte de ventas automático: Excel con gráficos y resumen en PDF",
                     font=ctk.CTkFont(size=13), text_color="#F3E3C7").grid(row=1, column=0, sticky="w", padx=26, pady=(0, 14))
        self.modo = ctk.CTkSwitch(barra, text="Modo oscuro", text_color="white", progress_color=MANTECA,
                                  command=lambda: ctk.set_appearance_mode("dark" if self.modo.get() else "light"))
        self.modo.grid(row=0, column=1, rowspan=2, padx=24)

    def _tarjeta(self, columna, fila_peso=False):
        marco = ctk.CTkFrame(self, fg_color=TARJETA, corner_radius=14)
        marco.grid(row=1, column=columna, sticky="nsew", padx=(20, 10) if columna == 0 else (10, 20), pady=20)
        marco.grid_columnconfigure(0, weight=1)
        return marco

    def _titulo_paso(self, padre, fila, numero, texto):
        fila_marco = ctk.CTkFrame(padre, fg_color="transparent")
        fila_marco.grid(row=fila, column=0, sticky="ew", padx=20, pady=(18, 6))
        ctk.CTkLabel(fila_marco, text=numero, width=26, height=26, corner_radius=13, fg_color=MANTECA,
                     text_color="#2F2118", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkLabel(fila_marco, text=texto, font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=10)

    def _panel_pasos(self):
        panel = self._tarjeta(0)
        panel.grid_rowconfigure(2, weight=1)

        # Paso 1: archivos
        self._titulo_paso(panel, 0, "1", "Archivos de ventas (CSV o Excel)")
        botones = ctk.CTkFrame(panel, fg_color="transparent")
        botones.grid(row=1, column=0, sticky="ew", padx=20)
        ctk.CTkButton(botones, text="Elegir archivos…", fg_color=CORTEZA, hover_color=CORTEZA_HOVER,
                      command=self.elegir_archivos).pack(side="left")
        ctk.CTkButton(botones, text="Probar con ejemplos", fg_color="transparent", border_width=2,
                      border_color=CORTEZA, text_color=CORTEZA, hover_color=("#F3E3C7", "#3A322C"),
                      command=self.usar_ejemplos).pack(side="left", padx=8)
        self.lista = ctk.CTkScrollableFrame(panel, fg_color=FONDO, corner_radius=10, height=110)
        self.lista.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 0))
        self.lista.grid_columnconfigure(0, weight=1)

        # Paso 2: carpeta
        self._titulo_paso(panel, 3, "2", "Guardar el reporte en")
        carpeta = ctk.CTkFrame(panel, fg_color="transparent")
        carpeta.grid(row=4, column=0, sticky="ew", padx=20)
        carpeta.grid_columnconfigure(0, weight=1)
        self.etiqueta_carpeta = ctk.CTkLabel(carpeta, text="", anchor="w", text_color=TEXTO2, wraplength=290, justify="left")
        self.etiqueta_carpeta.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(carpeta, text="Cambiar…", width=90, fg_color="transparent", border_width=2,
                      border_color=CORTEZA, text_color=CORTEZA, hover_color=("#F3E3C7", "#3A322C"),
                      command=self.elegir_carpeta).grid(row=0, column=1, padx=(8, 0))

        # Paso 3: generar
        self._titulo_paso(panel, 5, "3", "Generar")
        opciones = ctk.CTkFrame(panel, fg_color="transparent")
        opciones.grid(row=6, column=0, sticky="ew", padx=20)
        self.con_excel = ctk.CTkCheckBox(opciones, text="Excel con gráficos", fg_color=CORTEZA, hover_color=CORTEZA_HOVER)
        self.con_pdf = ctk.CTkCheckBox(opciones, text="Resumen en PDF", fg_color=CORTEZA, hover_color=CORTEZA_HOVER)
        for casilla in (self.con_excel, self.con_pdf):
            casilla.select()
            casilla.configure(command=self._actualizar)
            casilla.pack(side="left", padx=(0, 18))
        self.boton = ctk.CTkButton(panel, text="Generar reporte", height=46, corner_radius=12, fg_color=MANTECA,
                                   hover_color="#E0A12C", text_color="#2F2118", font=ctk.CTkFont(size=16, weight="bold"),
                                   command=self.generar)
        self.boton.grid(row=7, column=0, sticky="ew", padx=20, pady=(16, 8))
        self.progreso = ctk.CTkProgressBar(panel, progress_color=CORTEZA, height=8)
        self.progreso.set(0)
        self.progreso.grid(row=8, column=0, sticky="ew", padx=20)
        self.estado = ctk.CTkLabel(panel, text="", text_color=TEXTO2, anchor="w")
        self.estado.grid(row=9, column=0, sticky="ew", padx=20, pady=(4, 16))

    def _panel_informe(self):
        panel = self._tarjeta(1)
        panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(panel, text="Informe", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 6))
        self.informe = ctk.CTkTextbox(panel, fg_color=FONDO, corner_radius=10, wrap="word",
                                      font=ctk.CTkFont(size=13), spacing1=3, spacing3=3)
        self.informe.grid(row=1, column=0, sticky="nsew", padx=20)
        self._escribir("Elegí los archivos de ventas del mes (o varios meses juntos) y tocá «Generar reporte».\n\n"
                       "El programa corrige solo los nombres mal escritos, las fechas e importes con formatos "
                       "distintos, las filas vacías y las ventas repetidas, y te cuenta qué arregló.", limpiar=True)

        resultados = ctk.CTkFrame(panel, fg_color="transparent")
        resultados.grid(row=2, column=0, sticky="ew", padx=20, pady=16)
        self.abrir_excel = ctk.CTkButton(resultados, text="📊  Abrir Excel", fg_color=CORTEZA, hover_color=CORTEZA_HOVER,
                                         command=lambda: abrir(self.creados["excel"]))
        self.abrir_pdf = ctk.CTkButton(resultados, text="📄  Abrir PDF", fg_color=CORTEZA, hover_color=CORTEZA_HOVER,
                                       command=lambda: abrir(self.creados["pdf"]))
        self.abrir_carpeta = ctk.CTkButton(resultados, text="📁  Abrir carpeta", fg_color="transparent", border_width=2,
                                           border_color=CORTEZA, text_color=CORTEZA, hover_color=("#F3E3C7", "#3A322C"),
                                           command=lambda: abrir(self._carpeta_destino()))
        for i, boton in enumerate((self.abrir_excel, self.abrir_pdf, self.abrir_carpeta)):
            resultados.grid_columnconfigure(i, weight=1)
            boton.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))

    # ------------------------------------------------------------ acciones

    def elegir_archivos(self):
        rutas = filedialog.askopenfilenames(title="Elegí los archivos de ventas",
                                            filetypes=[("Ventas (CSV o Excel)", "*.csv *.xlsx *.xls"), ("Todos", "*.*")])
        for ruta in rutas:
            if Path(ruta) not in self.archivos:
                self.archivos.append(Path(ruta))
        self._actualizar()

    def usar_ejemplos(self):
        self.archivos = sorted(EJEMPLOS.glob("ventas-*"))
        self._actualizar()

    def quitar(self, ruta):
        self.archivos.remove(ruta)
        self._actualizar()

    def elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="¿Dónde guardo el reporte?")
        if carpeta:
            self.carpeta = Path(carpeta)
            self._actualizar()

    def _carpeta_destino(self):
        if self.carpeta:
            return self.carpeta
        return self.archivos[0].parent / "Reportes" if self.archivos else None

    def _actualizar(self):
        """Redibuja la lista de archivos y habilita o no los botones."""
        for hijo in self.lista.winfo_children():
            hijo.destroy()
        if not self.archivos:
            ctk.CTkLabel(self.lista, text="Todavía no elegiste archivos.", text_color=TEXTO2).grid(row=0, column=0, pady=12)
        for i, ruta in enumerate(self.archivos):
            ctk.CTkLabel(self.lista, text=("📗 " if ruta.suffix.lower().startswith(".xls") else "📄 ") + ruta.name,
                         anchor="w").grid(row=i, column=0, sticky="ew", padx=6, pady=2)
            ctk.CTkButton(self.lista, text="✕", width=28, height=24, fg_color="transparent", text_color=TEXTO2,
                          hover_color=("#F3E3C7", "#3A322C"), command=lambda r=ruta: self.quitar(r)).grid(row=i, column=1)
        destino = self._carpeta_destino()
        self.etiqueta_carpeta.configure(text=corta(destino, 38) if destino else "Una carpeta «Reportes» junto a los archivos de ventas")
        listo = bool(self.archivos) and (self.con_excel.get() or self.con_pdf.get())
        self.boton.configure(state="normal" if listo else "disabled")
        self.abrir_excel.configure(state="normal" if "excel" in self.creados else "disabled")
        self.abrir_pdf.configure(state="normal" if "pdf" in self.creados else "disabled")
        self.abrir_carpeta.configure(state="normal" if self.creados else "disabled")

    def _escribir(self, texto, limpiar=False):
        self.informe.configure(state="normal")
        if limpiar:
            self.informe.delete("1.0", "end")
        self.informe.insert("end", texto + "\n")
        self.informe.see("end")
        self.informe.configure(state="disabled")

    # ------------------------------------------------------------ generar (en otro hilo)

    def generar(self):
        self.creados = {}
        self.boton.configure(state="disabled", text="Generando…")
        self._escribir("", limpiar=True)
        self.progreso.set(0)
        datos = (list(self.archivos), self._carpeta_destino(), bool(self.con_excel.get()), bool(self.con_pdf.get()))
        threading.Thread(target=self._trabajar, args=datos, daemon=True).start()
        self.after(100, self._leer_mensajes)

    def _trabajar(self, archivos, carpeta, excel, pdf):
        try:
            creados, _, _ = generar(archivos, carpeta, excel, pdf,
                                    avisar=lambda texto, avance: self.mensajes.put(("aviso", texto, avance)))
            self.mensajes.put(("fin", creados, None))
        except (ErrorDeArchivo, PermissionError, ValueError) as error:
            self.mensajes.put(("error", str(error), None))
        except Exception as error:  # noqa: BLE001 (cualquier otro problema se muestra, no se cierra el programa)
            self.mensajes.put(("error", f"Ocurrió un error inesperado: {error}", None))

    def _leer_mensajes(self):
        try:
            while True:
                tipo, dato, avance = self.mensajes.get_nowait()
                if tipo == "aviso":
                    self.progreso.set(avance)
                    if dato.startswith(("📄", "✓")):
                        self._escribir(dato)
                    self.estado.configure(text=dato.lstrip("📄✓ "))
                elif tipo == "fin":
                    self.creados = dato
                    self._escribir("\nReporte guardado en:")
                    for ruta in dato.values():
                        self._escribir(f"   {Path(ruta).name}")
                    self._escribir(f"   en {corta(self._carpeta_destino(), 60)}")
                    self._terminar("✔ Listo. Abrí el Excel o el PDF con los botones de abajo.")
                    return
                elif tipo == "error":
                    self._escribir("\n⚠ " + dato)
                    self.progreso.set(0)
                    self._terminar("No se pudo generar el reporte.")
                    return
        except queue.Empty:
            pass
        self.after(100, self._leer_mensajes)

    def _terminar(self, texto):
        self.estado.configure(text=texto)
        self.boton.configure(text="Generar reporte")
        self._actualizar()


def iniciar():
    Ventana().mainloop()
