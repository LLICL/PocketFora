import sys
import os
import ctypes
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import (inicializar, insertar_transaccion, insertar_producto,
                                  listar_transacciones, listar_categorias,
                                  actualizar_categoria_transaccion, actualizar_transaccion,
                                  eliminar_transaccion,
                                  calcular_gastos_mensuales, calcular_resumen_mensual,
                                  obtener_transaccion, conectar)
from parser.invoice_parser import InvoiceParser
from scanner.qr_scanner import QRScanner
from analysis.reporter import Reporter

# ── Colores del diseño ──
C_INK          = "#1a0a2e"
C_INK2         = "#3a2560"
C_INK3         = "#7c5c9a"
C_SURFACE      = "#f5f4f0"
C_SURFACE2     = "#ede9e1"
C_SURFACE3     = "#ffffff"
C_ACCENT       = "#7c3aed"
C_ACCENT_LIGHT = "#ede9fe"
C_DANGER       = "#dc2626"
C_DANGER_LIGHT = "#fee2e2"
C_SUCCESS      = "#16a34a"
C_SUCCESS_LIGHT= "#dcfce7"
C_WARNING      = "#d97706"
C_WARNING_LIGHT= "#fef3c7"
C_BORDER       = "#2e1a4a"
C_BORDER_TK    = "#e0dfdb"
C_AMOUNT_RED   = "#dc2626"
C_AMOUNT_YELLOW= "#d97706"
C_AMOUNT_GREEN = "#16a34a"
C_AMOUNT_BLUE  = "#2563eb"


def color_por_monto(valor):
    if valor > 100000:
        return C_AMOUNT_RED
    elif valor > 50000:
        return C_AMOUNT_YELLOW
    elif valor > 20000:
        return C_AMOUNT_GREEN
    else:
        return C_AMOUNT_BLUE


FONT_HEAD = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 10)

FONT_TITLE_FAMILY = "Honfleur Heavy"
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Honfleur-Heavy.otf")


def _registrar_fuente():
    if not os.path.exists(FONT_PATH):
        return False
    try:
        ctypes.windll.gdi32.AddFontResourceExW(FONT_PATH, 0x10, 0)
        return True
    except Exception:
        return False


_registrar_fuente()


class PocketForaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PocketFora - Gestión de Gastos")
        self.root.geometry("1100x700")
        self.root.minsize(800, 500)
        self.parser = InvoiceParser()
        self.ultimo_qr = ""
        self.ultimo_parseo = None
        self.ultimo_trans_id = None
        self.imagen_cargada = None
        self.current_page = None

        inicializar()
        self._crear_interfaz()
        self.cargar_resumen()

    # ──────────────────────────────────────────────
    #  LAYOUT PRINCIPAL
    # ──────────────────────────────────────────────

    def _crear_interfaz(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.Frame(self.root, bg=C_INK, width=220)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.content_area = tk.Frame(self.root, bg=C_SURFACE)
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(1, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self._crear_sidebar()
        self._crear_topbar()
        self._crear_paginas()

        self._mostrar_pagina("inicio")

    # ──────────────────────────────────────────────
    #  SIDEBAR
    # ──────────────────────────────────────────────

    def _crear_sidebar(self):
        logo_frame = tk.Frame(self.sidebar, bg=C_INK)
        logo_frame.pack(fill="x", padx=16, pady=(20, 16))

        logo_path = os.path.join(os.path.dirname(__file__), "logo_pocketfora.png")
        if os.path.exists(logo_path):
            img_pil = Image.open(logo_path).resize((56, 56), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img_pil)
            lbl_logo = tk.Label(logo_frame, image=self.logo_img, bg=C_INK)
            lbl_logo.pack(side="left", padx=(0, 12))
        else:
            icon_frame = tk.Frame(logo_frame, bg=C_ACCENT, width=56, height=56)
            icon_frame.pack(side="left", padx=(0, 12))
            icon_frame.pack_propagate(False)
            lbl_icon = tk.Label(icon_frame, text="🏪", bg=C_ACCENT, fg="white", font=("Segoe UI", 24))
            lbl_icon.place(relx=0.5, rely=0.5, anchor="center")

        logo_text_frame = tk.Frame(logo_frame, bg=C_INK)
        logo_text_frame.pack(anchor="w")
        tk.Label(logo_text_frame, text="Pocket", bg=C_INK, fg="white",
                 font=(FONT_TITLE_FAMILY, 18)).pack(side="left")
        tk.Label(logo_text_frame, text="FORA", bg=C_INK, fg=C_ACCENT,
                 font=(FONT_TITLE_FAMILY, 18)).pack(side="left")
        tk.Label(logo_frame, text="Gestión de gastos", bg=C_INK,
                 fg="#71717d", font=("Segoe UI", 9)).pack(anchor="w")

        nav_frame = tk.Frame(self.sidebar, bg=C_INK)
        nav_frame.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        base = os.path.dirname(os.path.abspath(__file__))
        icon_map = {
            "inicio":    "inicio_logo.png",
            "escaner":   "escaneo_logo.png",
            "historial": "historial_logo.png",
            "reporte":   "reporte_logo.png",
        }
        self.nav_icons = {}
        for k, fn in icon_map.items():
            path = os.path.join(base, fn)
            if os.path.exists(path):
                img = Image.open(path).resize((24, 24), Image.LANCZOS)
                self.nav_icons[k] = ImageTk.PhotoImage(img)
            else:
                self.nav_icons[k] = None



        titulos = [
            ("PRINCIPAL", [
                ("inicio",    "Inicio"),
                ("escaner",   "Escanear"),
                ("historial", "Historial"),
            ]),
            ("ANÁLISIS", [
                ("reporte",   "Reporte"),
            ]),
        ]

        self.nav_labels = {}

        for seccion, items in titulos:
            tk.Label(nav_frame, text=seccion, bg=C_INK,
                     fg="#5a5a68", font=(FONT_TITLE_FAMILY, 10),
                     anchor="w", padx=8).pack(fill="x", pady=(14, 4))
            for key, texto in items:
                item_frame = tk.Frame(nav_frame, bg=C_INK, cursor="hand2")
                item_frame.pack(fill="x", padx=4, pady=2)
                item_frame.bind("<Enter>", lambda e, f=item_frame, k=key: f.config(bg="#2e1a50") if k != self.current_page else None)
                item_frame.bind("<Leave>", lambda e, f=item_frame, k=key: f.config(bg=C_INK) if k != self.current_page else None)
                item_frame.bind("<Button-1>", lambda e, k=key: self._navegar(k))

                icon_bg = tk.Frame(item_frame, bg=C_ACCENT, width=28, height=28)
                icon_bg.pack(side="left", padx=(8, 10), pady=4)
                icon_bg.pack_propagate(False)
                icon_bg.bind("<Button-1>", lambda e, k=key: self._navegar(k))
                icon_bg.bind("<Enter>", lambda e, f=item_frame: f.config(bg="#2e1a50"))
                icon_bg.bind("<Leave>", lambda e, f=item_frame: f.config(bg=C_INK))

                if self.nav_icons.get(key):
                    icon_lbl = tk.Label(icon_bg, image=self.nav_icons[key], bg=C_ACCENT)
                    icon_lbl.place(relx=0.5, rely=0.5, anchor="center")
                    icon_lbl.bind("<Button-1>", lambda e, k=key: self._navegar(k))
                    icon_lbl.bind("<Enter>", lambda e, f=item_frame: f.config(bg="#2e1a50"))
                    icon_lbl.bind("<Leave>", lambda e, f=item_frame: f.config(bg=C_INK))
                else:
                    tk.Label(icon_bg, text="◈", bg=C_ACCENT, fg="white",
                             font=("Segoe UI", 12)).place(relx=0.5, rely=0.5, anchor="center")

                lbl = tk.Label(item_frame, text=texto, bg=C_INK,
                               fg="#91919a",
                               font=("Segoe UI", 10), anchor="w", cursor="hand2")
                lbl.pack(side="left", fill="x", expand=True)
                lbl.bind("<Button-1>", lambda e, k=key: self._navegar(k))
                lbl.bind("<Enter>", lambda e, f=item_frame, k=key: f.config(bg="#2e1a50") if k != self.current_page else None)
                lbl.bind("<Leave>", lambda e, f=item_frame, k=key: f.config(bg=C_INK) if k != self.current_page else None)

                self.nav_labels[key] = (item_frame, lbl)

        # spacer to push nav up
        tk.Frame(self.sidebar, bg=C_INK).pack(fill="both", expand=True)

    # ──────────────────────────────────────────────
    #  TOPBAR
    # ──────────────────────────────────────────────

    def _crear_topbar(self):
        self.topbar = tk.Frame(self.content_area, bg=C_SURFACE3, bd=0, highlightthickness=0)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.topbar.grid_columnconfigure(1, weight=1)

        self.topbar_title = tk.Label(self.topbar, text="Resumen del Mes",
                                      bg=C_SURFACE3, fg=C_INK,
                                      font=(FONT_TITLE_FAMILY, 20), anchor="w")
        self.topbar_title.grid(row=0, column=0, padx=(22, 0), pady=(14, 2), sticky="w")

        self.topbar_sub = tk.Label(self.topbar, text="Cargando...",
                                    bg=C_SURFACE3, fg=C_INK3,
                                    font=("Segoe UI", 10), anchor="w")
        self.topbar_sub.grid(row=1, column=0, padx=(22, 0), pady=(0, 12), sticky="w")

        sep = tk.Frame(self.topbar, bg=C_BORDER_TK, height=1)
        sep.grid(row=2, column=0, columnspan=2, sticky="ew")

    # ──────────────────────────────────────────────
    #  PÁGINAS
    # ──────────────────────────────────────────────

    def _crear_paginas(self):
        self.paginas = {}

        pages = ["inicio", "escaner", "historial", "reporte"]
        for name in pages:
            f = tk.Frame(self.content_area, bg=C_SURFACE)
            f.grid(row=1, column=0, sticky="nsew")
            f.grid_rowconfigure(0, weight=1)
            f.grid_columnconfigure(0, weight=1)
            self.paginas[name] = f
            # hide by default
            f.grid_remove()

        self._crear_pagina_inicio()
        self._crear_pagina_escaner()
        self._crear_pagina_historial()
        self._crear_pagina_reporte()

    def _mostrar_pagina(self, nombre):
        if self.current_page:
            self.paginas[self.current_page].grid_remove()
            # reset nav style
            old = self.nav_labels.get(self.current_page)
            if old:
                old[0].config(bg=C_INK)
                old[1].config(fg="#91919a")
        self.current_page = nombre
        self.paginas[nombre].grid()
        new = self.nav_labels.get(nombre)
        if new:
            new[0].config(bg="#2e1a50")
            new[1].config(fg="white")
        # update topbar
        titulos = {
            "inicio": ("Resumen del Mes", "Tus gastos del mes actual"),
            "escaner": ("Escanear QR", "Carga una imagen o pega un código QR"),
            "historial": ("Historial", "Todas tus transacciones registradas"),
            "reporte": ("Reporte", "Análisis detallado de gastos"),
        }
        t, s = titulos.get(nombre, ("", ""))
        self.topbar_title.config(text=t)
        self.topbar_sub.config(text=s)

    def _navegar(self, nombre):
        self._mostrar_pagina(nombre)
        if nombre == "historial":
            self.cargar_historial()
        elif nombre == "reporte":
            self.cargar_reporte()
        elif nombre == "inicio":
            self.cargar_resumen()

    # ──────────────────────────────────────────────
    #  PÁGINA INICIO (Dashboard)
    # ──────────────────────────────────────────────

    def _crear_pagina_inicio(self):
        padre = self.paginas["inicio"]

        canvas = tk.Canvas(padre, bg=C_SURFACE, bd=0, highlightthickness=0)
        scroll = ttk.Scrollbar(padre, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=C_SURFACE)

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        def _conf_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _conf_canvas)
        def _conf_frame(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scroll_frame.bind("<Configure>", _conf_frame)
        canvas.configure(yscrollcommand=scroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # wrap in a frame with padding
        container = tk.Frame(scroll_frame, bg=C_SURFACE)
        container.pack(fill="both", expand=True, padx=22, pady=16)

        # ── Banner registro manual ──
        banner = tk.Frame(container, bg=C_ACCENT_LIGHT, bd=0, highlightbackground="#1c2853", highlightthickness=1)
        banner.pack(fill="x", pady=(0, 18))

        inner = tk.Frame(banner, bg=C_ACCENT_LIGHT)
        inner.pack(fill="both", padx=14, pady=12)

        icon_b = tk.Frame(inner, bg=C_ACCENT, width=36, height=36)
        icon_b.pack(side="left", padx=(0, 12))
        icon_b.pack_propagate(False)
        tk.Label(icon_b, text="✎", bg=C_ACCENT, fg="white",
                 font=("Segoe UI", 16)).place(relx=0.5, rely=0.5, anchor="center")

        txt_f = tk.Frame(inner, bg=C_ACCENT_LIGHT)
        txt_f.pack(side="left", fill="x", expand=True)
        tk.Label(txt_f, text="¿Tienes una factura sin QR?", bg=C_ACCENT_LIGHT,
                 fg=C_INK, font=(FONT_TITLE_FAMILY, 13), anchor="w").pack(fill="x")
        tk.Label(txt_f, text="Regístrala manualmente llenando todos los datos.",
                 bg=C_ACCENT_LIGHT, fg=C_INK2, font=("Segoe UI", 9), anchor="w").pack(fill="x")

        tk.Button(inner, text="Registro manual", bg="white", fg=C_ACCENT,
                  bd=1, relief="solid", highlightbackground="#2a4a8a",
                  padx=10, pady=4, font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#f0f6ff",
                  command=self._abrir_registro_manual).pack(side="right")

        # ── Stats cards ──
        stats = tk.Frame(container, bg=C_SURFACE)
        stats.pack(fill="x", pady=(0, 16))
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform="stats")

        card_data = [
            ("Gasto total",   "danger",  "◆"),
            ("Transacciones", "purple",    "◆"),
            ("Promedio diario","green",  "◆"),
        ]

        self.stat_widgets = {}
        for i, (label, color, icon) in enumerate(card_data):
            border_color = {"danger": C_DANGER, "purple": C_ACCENT, "green": C_SUCCESS}[color]
            card = tk.Frame(stats, bg=C_SURFACE3, bd=0, highlightbackground=C_BORDER_TK, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=4)

            # left color bar
            bar = tk.Frame(card, bg=border_color, width=3)
            bar.pack(side="left", fill="y")

            body = tk.Frame(card, bg=C_SURFACE3)
            body.pack(side="left", fill="both", expand=True, padx=14, pady=12)

            tk.Label(body, text=f"{icon}  {label.upper()}", bg=C_SURFACE3,
                     fg=C_INK3, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x")

            val = tk.Label(body, text="$ 0", bg=C_SURFACE3, fg=C_INK,
                           font=("Segoe UI", 22, "bold"), anchor="w")
            val.pack(fill="x")

            delta = tk.Label(body, text="vs mes anterior", bg=C_SURFACE3,
                             fg=C_INK3, font=("Segoe UI", 9), anchor="w")
            delta.pack(fill="x")

            self.stat_widgets[label] = {"val": val, "delta": delta}

        # ── Grid 2 columnas ──
        grid2 = tk.Frame(container, bg=C_SURFACE)
        grid2.pack(fill="both", expand=True)
        grid2.grid_columnconfigure((0, 1), weight=1, uniform="g2")
        grid2.grid_rowconfigure(0, weight=1)

        # ── Card: Últimas transacciones ──
        tx_card = tk.Frame(grid2, bg=C_SURFACE3, bd=0, highlightbackground=C_BORDER_TK, highlightthickness=1)
        tx_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        tx_head = tk.Frame(tx_card, bg=C_SURFACE3, bd=0, highlightbackground=C_BORDER_TK, highlightthickness=0)
        tx_head.pack(fill="x", padx=16, pady=(12, 8))
        tk.Label(tx_head, text="◆  Últimas transacciones", bg=C_SURFACE3,
                 fg=C_INK, font=(FONT_TITLE_FAMILY, 13), anchor="w").pack(side="left")

        self.tx_container = tk.Frame(tx_card, bg=C_SURFACE3)
        self.tx_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Single row placeholder
        self.tx_placeholder = tk.Label(self.tx_container, text="Aún no hay transacciones",
                                        bg=C_SURFACE3, fg=C_INK3,
                                        font=("Segoe UI", 10), pady=20)
        self.tx_placeholder.pack(fill="x")

        # ── Card: Evolución mensual + categorías ──
        chart_card = tk.Frame(grid2, bg=C_SURFACE3, bd=0, highlightbackground=C_BORDER_TK, highlightthickness=1)
        chart_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        chart_head = tk.Frame(chart_card, bg=C_SURFACE3, bd=0, highlightbackground=C_BORDER_TK, highlightthickness=0)
        chart_head.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(chart_head, text="◆  Evolución mensual", bg=C_SURFACE3,
                 fg=C_INK, font=(FONT_TITLE_FAMILY, 13), anchor="w").pack(side="left")

        # bar chart canvas
        self.bar_canvas = tk.Canvas(chart_card, bg=C_SURFACE3, height=130,
                                     bd=0, highlightthickness=0)
        self.bar_canvas.pack(fill="x", padx=16, pady=(4, 2))
        self.bar_canvas.bind("<Configure>", lambda e: self._actualizar_grafico())

        # legend
        leg = tk.Frame(chart_card, bg=C_SURFACE3)
        leg.pack(fill="x", padx=16, pady=(0, 6))
        for color, text in [(C_AMOUNT_RED, "> $100k"), (C_AMOUNT_YELLOW, "$50k-$100k"), (C_AMOUNT_GREEN, "$20k-$50k"), (C_AMOUNT_BLUE, "< $20k")]:
            f = tk.Frame(leg, bg=C_SURFACE3)
            f.pack(side="left", padx=(0, 12))
            tk.Frame(f, bg=color, width=8, height=8, bd=0).pack(side="left", padx=(0, 4))
            tk.Label(f, text=text, bg=C_SURFACE3, fg=C_INK3,
                     font=("Segoe UI", 9)).pack(side="left")

        # separador
        sep_line = tk.Frame(chart_card, bg=C_BORDER_TK, height=1)
        sep_line.pack(fill="x", padx=16, pady=4)

        # categorías
        cat_head = tk.Frame(chart_card, bg=C_SURFACE3)
        cat_head.pack(fill="x", padx=16, pady=(6, 4))
        tk.Label(cat_head, text="◆  Gasto por categoría", bg=C_SURFACE3,
                 fg=C_INK, font=(FONT_TITLE_FAMILY, 13), anchor="w").pack(side="left")

        self.cat_container = tk.Frame(chart_card, bg=C_SURFACE3)
        self.cat_container.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    # ──────────────────────────────────────────────
    #  PÁGINA ESCANER
    # ──────────────────────────────────────────────

    def _crear_pagina_escaner(self):
        padre = self.paginas["escaner"]

        self.escaner_outer = tk.Frame(padre, bg=C_SURFACE)
        self.escaner_outer.pack(fill="both", expand=True, padx=22, pady=16)

        # --- Scanner section ---
        self.scanner_section = tk.Frame(self.escaner_outer, bg=C_SURFACE)
        self.scanner_section.pack(fill="both", expand=True)

        control_frame = tk.Frame(self.scanner_section, bg=C_SURFACE)
        control_frame.pack(fill="x", pady=(0, 8))

        btn_style = {"bg": C_SURFACE3, "fg": C_INK2, "bd": 1, "relief": "solid",
                     "font": ("Segoe UI", 9), "padx": 12, "pady": 5, "cursor": "hand2",
                     "activebackground": C_SURFACE2}

        self.btn_cargar = tk.Button(control_frame, text="📁  Cargar Imagen", command=self.cargar_imagen, **btn_style)
        self.btn_cargar.pack(side="left", padx=3)

        self.btn_escanear = tk.Button(control_frame, text="🔍  Escanear QR", command=self.escanear_imagen,
                                       state="disabled", **btn_style)
        self.btn_escanear.pack(side="left", padx=3)

        tk.Button(control_frame, text="📄  Pegar texto QR", command=self.abrir_pegado, **btn_style).pack(side="left", padx=3)

        self.lbl_estado = tk.Label(control_frame, text="Carga una imagen primero",
                                    bg=C_SURFACE, fg=C_INK3, font=("Segoe UI", 9))
        self.lbl_estado.pack(side="right", padx=5)

        self.video_frame = tk.Frame(self.scanner_section, bg="white",
                                     bd=1, relief="solid", highlightbackground=C_BORDER_TK)
        self.video_frame.pack(fill="both", expand=True)

        self.video_label = tk.Label(self.video_frame,
                                     text="Carga una imagen de factura con código QR\nluego presiona 'Escanear QR'",
                                     bg="white", fg=C_INK3, font=("Segoe UI", 12))
        self.video_label.pack(expand=True)

        # --- Confirm section (hidden until scan) ---
        self.confirm_section = tk.LabelFrame(self.escaner_outer, text="Datos de la Transacción",
                                              bg=C_SURFACE3, fg=C_INK,
                                              font=(FONT_TITLE_FAMILY, 12),
                                              bd=1, relief="solid", highlightbackground=C_BORDER_TK,
                                              padx=16, pady=12)

        self.campos_frame = tk.Frame(self.confirm_section, bg=C_SURFACE3)
        self.campos_frame.pack(fill="both", expand=True)

        labels = ["Comercio:", "Fecha:", "Total:", "RUC:", "Tipo Doc.:", "Serie:", "Categoría:"]
        self.entries = {}
        for i, l in enumerate(labels):
            tk.Label(self.campos_frame, text=l, bg=C_SURFACE3, fg=C_INK,
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if l == "Categoría:":
                self.cat_var = tk.StringVar()
                cats = listar_categorias()
                self.cat_combo = ttk.Combobox(self.campos_frame, textvariable=self.cat_var, state="readonly",
                                               width=40, font=("Segoe UI", 10))
                self.cat_combo["values"] = [f"{c['icono']} {c['nombre']}" for c in cats]
                if cats:
                    self.cat_combo.current(len(cats)-1)
                self.cat_combo.grid(row=i, column=1, sticky="ew", pady=4)
            else:
                var = tk.StringVar()
                state = "normal" if l in ("Comercio:", "Total:") else "readonly"
                entry = tk.Entry(self.campos_frame, textvariable=var, width=40,
                                  font=("Segoe UI", 10), state=state,
                                  bd=1, relief="solid", highlightbackground=C_BORDER_TK)
                entry.grid(row=i, column=1, sticky="ew", pady=4)
                self.entries[l] = var

        tk.Label(self.campos_frame, text="Detalle:", bg=C_SURFACE3, fg=C_INK,
                 font=("Segoe UI", 10)).grid(row=len(labels), column=0, sticky="nw", pady=4)
        self.detalle_text = scrolledtext.ScrolledText(self.campos_frame, width=40, height=4,
                                                       font=("Segoe UI", 9), state="disabled",
                                                       bd=1, relief="solid")
        self.detalle_text.grid(row=len(labels), column=1, sticky="ew", pady=4)

        confirm_btn_frame = tk.Frame(self.confirm_section, bg=C_SURFACE3)
        confirm_btn_frame.pack(pady=10)
        tk.Button(confirm_btn_frame, text="✅  Guardar", command=self.guardar_transaccion,
                  bg=C_ACCENT, fg="white", bd=0, padx=16, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                   activebackground="#6d28d9").pack(side="left", padx=5)
        tk.Button(confirm_btn_frame, text="🗑️  Descartar", command=self.descartar_transaccion,
                  bg=C_SURFACE3, fg=C_INK2, bd=1, relief="solid", padx=14, pady=5,
                  font=("Segoe UI", 9), cursor="hand2",
                  activebackground=C_SURFACE2).pack(side="left", padx=5)

    # ──────────────────────────────────────────────
    #  PÁGINA HISTORIAL
    # ──────────────────────────────────────────────

    def _crear_pagina_historial(self):
        padre = self.paginas["historial"]

        container = tk.Frame(padre, bg=C_SURFACE)
        container.pack(fill="both", expand=True, padx=22, pady=16)

        btn_frame = tk.Frame(container, bg=C_SURFACE)
        btn_frame.pack(fill="x", pady=(0, 8))

        btn_st = {"bg": C_SURFACE3, "fg": C_INK2, "bd": 1, "relief": "solid",
                  "font": ("Segoe UI", 9), "padx": 12, "pady": 5, "cursor": "hand2",
                  "activebackground": C_SURFACE2}
        tk.Button(btn_frame, text="🔄  Actualizar", command=self.cargar_historial, **btn_st).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️  Editar seleccionada", command=self.editar_seleccionada, **btn_st).pack(side="left", padx=2)
        tk.Button(btn_frame, text="🗑️  Eliminar seleccionada", command=self.eliminar_seleccionada, **btn_st).pack(side="left", padx=2)

        columns = ("id", "fecha", "comercio", "categoria", "total")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=20)
        self.tree.heading("id", text="ID")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("comercio", text="Comercio")
        self.tree.heading("categoria", text="Categoría")
        self.tree.heading("total", text="Total")
        self.tree.column("id", width=40, minwidth=40, anchor="center", stretch=False)
        self.tree.column("fecha", width=90, minwidth=70, stretch=True)
        self.tree.column("comercio", width=230, minwidth=120, stretch=True)
        self.tree.column("categoria", width=130, minwidth=80, stretch=True)
        self.tree.column("total", width=90, minwidth=70, anchor="e", stretch=False)

        scroll = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ──────────────────────────────────────────────
    #  PÁGINA REPORTE
    # ──────────────────────────────────────────────

    def _crear_pagina_reporte(self):
        padre = self.paginas["reporte"]

        container = tk.Frame(padre, bg=C_SURFACE)
        container.pack(fill="both", expand=True, padx=22, pady=16)

        selector_frame = tk.Frame(container, bg=C_SURFACE)
        selector_frame.pack(fill="x", pady=(0, 8))

        ahora = datetime.now()
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]

        tk.Label(selector_frame, text="Mes:", bg=C_SURFACE, fg=C_INK2,
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        self.reporte_mes_var = tk.StringVar(value=meses[ahora.month-1])
        self.reporte_mes_combo = ttk.Combobox(selector_frame, textvariable=self.reporte_mes_var,
                                               values=meses, state="readonly", width=14, font=("Segoe UI", 9))
        self.reporte_mes_combo.pack(side="left", padx=(0, 12))

        tk.Label(selector_frame, text="Anio:", bg=C_SURFACE, fg=C_INK2,
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        self.reporte_anio_var = tk.StringVar(value=str(ahora.year))
        anios = [str(a) for a in range(ahora.year-5, ahora.year+1)]
        self.reporte_anio_combo = ttk.Combobox(selector_frame, textvariable=self.reporte_anio_var,
                                                values=anios, state="readonly", width=8, font=("Segoe UI", 9))
        self.reporte_anio_combo.pack(side="left", padx=(0, 16))

        btn_st = {"bg": C_SURFACE3, "fg": C_INK2, "bd": 1, "relief": "solid",
                  "font": ("Segoe UI", 9), "padx": 12, "pady": 5, "cursor": "hand2",
                  "activebackground": C_SURFACE2}
        tk.Button(selector_frame, text="🔄  Generar Reporte", command=self.cargar_reporte, **btn_st).pack(side="left", padx=2)
        tk.Button(selector_frame, text="📄  Descargar PDF", command=self.descargar_pdf, **btn_st).pack(side="left", padx=2)

        self.reporte_text = scrolledtext.ScrolledText(container, font=("Consolas", 10),
                                                       wrap="word", state="disabled",
                                                       bg="white", bd=1, relief="solid")
        self.reporte_text.pack(fill="both", expand=True)

    # ──────────────────────────────────────────────
    #  PÁGINAS CATEGORÍAS / AJUSTES (placeholder)
    # ──────────────────────────────────────────────

    # ──────────────────────────────────────────────
    #  LÓGICA DE NEGOCIO (sin cambios)
    # ──────────────────────────────────────────────

    def cargar_resumen(self):
        ahora = datetime.now()
        resumen = calcular_resumen_mensual(ahora.year, ahora.month)
        total = resumen['gasto_total']
        prom = resumen['promedio_por_transaccion']
        total_f = self._formatear_total(total)
        prom_f = self._formatear_total(prom)

        card_gasto = self.stat_widgets.get("Gasto total", {}).get("val")
        if card_gasto:
            card_gasto.config(text=f"$ {total_f}", fg=color_por_monto(total))
        card_tx = self.stat_widgets.get("Transacciones", {}).get("val")
        if card_tx:
            card_tx.config(text=str(resumen['total_transacciones']), fg=C_INK)
        card_prom = self.stat_widgets.get("Promedio diario", {}).get("val")
        if card_prom:
            card_prom.config(text=f"$ {prom_f}", fg=color_por_monto(prom))

        # update recent transactions
        self._actualizar_recientes()

        # update bar chart + categories
        self._actualizar_grafico()
        self._actualizar_categorias()

    def _actualizar_recientes(self):
        for w in self.tx_container.winfo_children():
            w.destroy()
        trans = listar_transacciones(limite=5)
        if not trans:
            lbl = tk.Label(self.tx_container, text="Aún no hay transacciones",
                            bg=C_SURFACE3, fg=C_INK3, font=("Segoe UI", 10), pady=16)
            lbl.pack(fill="x")
            return
        for t in trans:
            row = tk.Frame(self.tx_container, bg=C_SURFACE3, bd=0,
                           highlightbackground=C_BORDER_TK, highlightthickness=0)
            row.pack(fill="x", pady=3)

            emoji = t.get("categoria_icono", "📁") or "📁"
            cat_name = t.get("categoria_nombre", "Otros") or "Otros"

            # icon
            icon_f = tk.Frame(row, bg=C_DANGER_LIGHT, width=32, height=32)
            icon_f.pack(side="left", padx=(0, 10))
            icon_f.pack_propagate(False)
            tk.Label(icon_f, text=emoji, bg=C_DANGER_LIGHT,
                     font=("Segoe UI", 13)).place(relx=0.5, rely=0.5, anchor="center")

            # info
            info = tk.Frame(row, bg=C_SURFACE3)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=t["comercio"], bg=C_SURFACE3, fg=C_INK,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=t["fecha"], bg=C_SURFACE3, fg=C_INK3,
                     font=("Segoe UI", 8), anchor="w").pack(fill="x")

            # tag
            tag = tk.Label(row, text=cat_name, bg=C_ACCENT_LIGHT, fg=C_ACCENT,
                           font=("Segoe UI", 8, "bold"), padx=8, pady=2)
            tag.pack(side="right", padx=(4, 0))

            # amount
            monto = t['total']
            amt = tk.Label(row, text=f"$ {self._formatear_total(monto)}",
                            bg=C_SURFACE3, fg=color_por_monto(monto),
                            font=("Segoe UI", 11, "bold"))
            amt.pack(side="right")

    def _actualizar_grafico(self):
        self.bar_canvas.delete("all")
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun"]
        ahora = datetime.now()
        totals = []
        for i in range(5, -1, -1):
            m = ahora.month - i
            a = ahora.year
            while m < 1:
                m += 12
                a -= 1
            r = calcular_resumen_mensual(a, m)
            totals.append(r["gasto_total"])

        w = self.bar_canvas.winfo_width()
        if w < 50:
            self.bar_canvas.after_idle(self._actualizar_grafico)
            return
        h = self.bar_canvas.winfo_height() or 130
        bot_pad = 18
        top_pad = 14
        usable_h = h - bot_pad - top_pad
        bar_w = (w - 40) / len(meses)
        max_v = max(totals) if max(totals) > 0 else 1

        for i, (m, v) in enumerate(zip(meses, totals)):
            pct = v / max_v
            bh = max(pct * usable_h, 4)
            x0 = 20 + i * bar_w + 4
            x1 = x0 + bar_w - 8
            y0 = h - bot_pad - bh
            y1 = h - bot_pad

            bar_color = color_por_monto(v)
            self.bar_canvas.create_rectangle(x0, y0, x1, y1, fill=bar_color, outline="")
            lbl = f"${v:.0f}" if v == int(v) else f"${v:.1f}"
            self.bar_canvas.create_text((x0+x1)/2, y0-4, text=lbl,
                                         fill=bar_color, font=("Segoe UI", 7, "bold"))
            self.bar_canvas.create_text((x0+x1)/2, h-4, text=m,
                                         fill=C_INK3, font=("Segoe UI", 8))

    def _actualizar_categorias(self):
        for w in self.cat_container.winfo_children():
            w.destroy()
        ahora = datetime.now()
        cats = calcular_gastos_mensuales(ahora.year, ahora.month)
        total_global = sum(c["total_gastado"] for c in cats)
        if total_global == 0:
            tk.Label(self.cat_container, text="Sin gastos este mes",
                     bg=C_SURFACE3, fg=C_INK3, font=("Segoe UI", 9)).pack(fill="x")
            return
        colores = [C_DANGER, C_ACCENT, C_WARNING, "#7c3aed", C_SUCCESS, C_INK3]
        for idx, c in enumerate(cats):
            if c["total_gastado"] <= 0:
                continue
            pct = (c["total_gastado"] / total_global) * 100
            row = tk.Frame(self.cat_container, bg=C_SURFACE3)
            row.pack(fill="x", pady=4)

            top = tk.Frame(row, bg=C_SURFACE3)
            top.pack(fill="x")
            tk.Label(top, text=f"{c['icono']}  {c['nombre']}", bg=C_SURFACE3,
                     fg=C_INK2, font=("Segoe UI", 9)).pack(side="left")
            tk.Label(top, text=f"{pct:.1f}%", bg=C_SURFACE3,
                     fg=C_INK3, font=("Segoe UI", 8)).pack(side="left", padx=4)
            cat_monto = c['total_gastado']
            tk.Label(top, text=f"$ {self._formatear_total(cat_monto)}",
                     bg=C_SURFACE3, fg=color_por_monto(cat_monto),
                     font=("Segoe UI", 9, "bold")).pack(side="right")

            bar_bg = tk.Frame(row, bg=C_SURFACE2, height=5)
            bar_bg.pack(fill="x", pady=(2, 0))
            bar_bg.pack_propagate(False)

            fill_color = colores[idx % len(colores)]
            fill = tk.Frame(bar_bg, bg=fill_color, width=max(int(pct * 4), 4), height=5)
            fill.pack(side="left")

    def cargar_imagen(self):
        from tkinter import filedialog
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen con QR",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff"), ("Todos", "*.*")]
        )
        if not ruta:
            return
        self.lbl_estado.config(text="Leyendo imagen...", fg=C_ACCENT)
        self.root.update()
        self.imagen_cargada = self._leer_imagen(ruta)
        if self.imagen_cargada is None:
            messagebox.showerror("Error",
                f"No se pudo leer la imagen.\nRuta: {ruta}\n\nPrueba:\n"
                "• Copia la imagen a la carpeta del proyecto\n"
                "• Renómbrala sin tildes (ej: qr.jpg)\n"
                "• Ábrela con Paint y guarda como PNG")
            self.lbl_estado.config(text="Error al leer imagen", fg="red")
            return
        self.mostrar_imagen_en_frame(self.imagen_cargada)
        self.btn_escanear.config(state="normal")
        self.lbl_estado.config(text="Imagen cargada. Presiona 'Escanear QR'", fg="green")

    def escanear_imagen(self):
        if self.imagen_cargada is None:
            messagebox.showwarning("Sin imagen", "Primero carga una imagen")
            return
        self.lbl_estado.config(text="Escaneando QR...", fg=C_ACCENT)
        self.root.update()
        try:
            scanner = QRScanner()
            frame_procesado, codigos = scanner.escanear_frame(self.imagen_cargada.copy())
            if codigos:
                self.ultimo_qr = codigos[0]["datos"]
                self.lbl_estado.config(text="✅ QR Detectado!", fg="green")
                self._procesar_texto(self.ultimo_qr)
            else:
                self.lbl_estado.config(text="❌ No se encontró QR", fg="red")
                messagebox.showwarning("Sin QR",
                    "No se detectó ningún código QR en la imagen.\n\n"
                    "Posibles causas:\n"
                    "• La imagen no tiene un código QR\n"
                    "• El QR está muy pequeño o borroso\n"
                    "• El QR está dañado\n\n"
                    "Prueba pegando el texto manualmente con 'Pegar texto QR'.")
        except Exception as e:
            self.lbl_estado.config(text=f"Error: {e}", fg="red")
            messagebox.showerror("Error", f"Error al escanear:\n{type(e).__name__}: {e}")

    def _leer_imagen(self, ruta):
        for intento, metodo in enumerate([
            self._leer_con_imdecode,
            self._leer_con_pil
        ], 1):
            try:
                img = metodo(ruta)
                if img is not None and img.size > 0:
                    return img
            except Exception:
                pass
        return None

    def _leer_con_imdecode(self, ruta):
        with open(ruta, "rb") as f:
            data = f.read()
        if len(data) == 0:
            return None
        buf = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    def _leer_con_pil(self, ruta):
        from PIL import Image as PILImage
        pil_img = PILImage.open(ruta)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def mostrar_imagen_en_frame(self, frame):
        self._imagen_original = frame
        self._redibujar_imagen()
        self.video_frame.bind("<Configure>", self._redibujar_imagen)

    def _redibujar_imagen(self, event=None):
        frame = getattr(self, "_imagen_original", None)
        if frame is None:
            return
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]
        cw = self.video_frame.winfo_width() or 640
        ch = self.video_frame.winfo_height() or 480
        escala = min(cw / w, ch / h, 1.0)
        nuevo_w, nuevo_h = int(w * escala), int(h * escala)
        frame_resized = cv2.resize(frame_rgb, (nuevo_w, nuevo_h))
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.pack_forget()
        if hasattr(self, "video_canvas"):
            self.video_canvas.pack_forget()
        self.video_canvas = tk.Canvas(self.video_frame, bg="black", bd=0, highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True)
        self.video_canvas.create_image(nuevo_w // 2, nuevo_h // 2, image=imgtk)
        self.video_canvas.image = imgtk

    def abrir_pegado(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Pegar texto QR")
        ventana.geometry("500x300")
        ventana.transient(self.root)
        tk.Label(ventana, text="Pega el texto del código QR:",
                 font=("Segoe UI", 11)).pack(pady=10)
        text_area = scrolledtext.ScrolledText(ventana, height=8, font=("Consolas", 10))
        text_area.pack(fill="both", expand=True, padx=10, pady=5)
        tk.Button(ventana, text="Procesar",
                  command=lambda: self._procesar_pegado(text_area, ventana)).pack(pady=5)

    def _procesar_pegado(self, text_area, ventana):
        texto = text_area.get("1.0", "end-1c").strip()
        if texto:
            ventana.destroy()
            self._procesar_texto(texto)

    def _limpiar_escaner(self):
        self.imagen_cargada = None
        self._imagen_original = None
        self.video_frame.unbind("<Configure>")
        if hasattr(self, "video_canvas"):
            self.video_canvas.pack_forget()
        self.video_label.pack(expand=True)
        self.btn_escanear.config(state="disabled")
        self.lbl_estado.config(text="Carga una imagen primero", fg=C_INK3)

    def _procesar_texto(self, texto):
        datos = self.parser.parsear(texto)
        self.ultimo_parseo = datos
        trans_id = insertar_transaccion(
            comercio=datos.comercio, fecha=datos.fecha, total=datos.total,
            detalle=datos.detalle, tipo_documento=datos.tipo_documento,
            serie_numero=datos.serie_numero, ruc=datos.ruc, qr_raw=texto,
            moneda=datos.moneda,
        )
        for p in datos.productos:
            insertar_producto(trans_id, p["descripcion"], p["cantidad"], p["precio_unitario"], p.get("subtotal", 0))
        self.ultimo_trans_id = trans_id
        self._mostrar_confirmacion(datos)
        self._limpiar_escaner()
        self.scanner_section.pack_forget()
        self.confirm_section.pack(fill="both", expand=True)

    def _formatear_total(self, valor):
        s = f"{valor:,.2f}"
        if s.endswith(".00"):
            s = s[:-3]
        return s

    def _mostrar_confirmacion(self, datos):
        self.entries["Comercio:"].set(datos.comercio)
        self.entries["Fecha:"].set(datos.fecha)
        self.entries["Total:"].set(self._formatear_total(datos.total))
        self.entries["RUC:"].set(datos.ruc)
        self.entries["Tipo Doc.:"].set(datos.tipo_documento)
        self.entries["Serie:"].set(datos.serie_numero)
        self.detalle_text.config(state="normal")
        self.detalle_text.delete("1.0", "end")
        self.detalle_text.insert("1.0", datos.detalle)
        self.detalle_text.config(state="disabled")

    def _volver_a_escaner(self):
        self.confirm_section.pack_forget()
        self.scanner_section.pack(fill="both", expand=True)
        self.lbl_estado.config(text="Carga una imagen primero", fg=C_INK3)

    def guardar_transaccion(self):
        from database.db_manager import conectar
        texto_cat = self.cat_var.get()
        cats = listar_categorias()
        for c in cats:
            if f"{c['icono']} {c['nombre']}" == texto_cat:
                actualizar_categoria_transaccion(self.ultimo_trans_id, c["id"])
                break
        conn = conectar()
        comercio_nuevo = self.entries["Comercio:"].get().strip()
        if comercio_nuevo:
            conn.execute("UPDATE transacciones SET comercio = ? WHERE id = ?", (comercio_nuevo, self.ultimo_trans_id))
        try:
            total_texto = self.entries["Total:"].get().replace(",", "").strip()
            total_nuevo = float(total_texto)
            conn.execute("UPDATE transacciones SET total = ? WHERE id = ?", (total_nuevo, self.ultimo_trans_id))
        except ValueError:
            pass
        conn.commit()
        conn.close()
        messagebox.showinfo("Guardado", "Transacción guardada correctamente")
        self.cargar_resumen()
        self._volver_a_escaner()
        self._mostrar_pagina("inicio")

    def descartar_transaccion(self):
        if self.ultimo_trans_id:
            eliminar_transaccion(self.ultimo_trans_id)
        self._volver_a_escaner()
        self._mostrar_pagina("inicio")

    def _abrir_registro_manual(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Registro manual de factura")
        ventana.geometry("520x520")
        ventana.transient(self.root)
        ventana.grab_set()

        main = tk.Frame(ventana, bg=C_SURFACE3, padx=20, pady=16)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Ingresa los datos de la factura", bg=C_SURFACE3, fg=C_INK,
                 font=(FONT_TITLE_FAMILY, 14)).pack(anchor="w", pady=(0, 12))

        campos = tk.Frame(main, bg=C_SURFACE3)
        campos.pack(fill="both", expand=True)

        labels = ["Comercio:", "Fecha:", "Total:", "RUC:", "Tipo Doc.:", "Serie:", "Categoría:"]
        entries = {}
        for i, l in enumerate(labels):
            tk.Label(campos, text=l, bg=C_SURFACE3, fg=C_INK,
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if l == "Categoría:":
                var = tk.StringVar()
                cats = listar_categorias()
                combo = ttk.Combobox(campos, textvariable=var, state="readonly",
                                     width=40, font=("Segoe UI", 10))
                combo["values"] = [f"{c['icono']} {c['nombre']}" for c in cats]
                if cats:
                    combo.current(len(cats)-1)
                combo.grid(row=i, column=1, sticky="ew", pady=4)
                entries[l] = var
            else:
                var = tk.StringVar()
                entry = tk.Entry(campos, textvariable=var, width=40,
                                 font=("Segoe UI", 10),
                                 bd=1, relief="solid", highlightbackground=C_BORDER_TK)
                entry.grid(row=i, column=1, sticky="ew", pady=4)
                if l == "Fecha:":
                    var.set(datetime.now().strftime("%Y-%m-%d"))
                entries[l] = var

        tk.Label(campos, text="Detalle:", bg=C_SURFACE3, fg=C_INK,
                 font=("Segoe UI", 10)).grid(row=len(labels), column=0, sticky="nw", pady=4)
        detalle = scrolledtext.ScrolledText(campos, width=40, height=4,
                                            font=("Segoe UI", 9),
                                            bd=1, relief="solid")
        detalle.grid(row=len(labels), column=1, sticky="ew", pady=4)

        def _guardar_manual():
            comercio = entries["Comercio:"].get().strip()
            fecha = entries["Fecha:"].get().strip()
            total_str = entries["Total:"].get().strip().replace(",", "")
            ruc = entries["RUC:"].get().strip()
            tipo_doc = entries["Tipo Doc.:"].get().strip()
            serie = entries["Serie:"].get().strip()
            cat_var = entries["Categoría:"].get().strip()
            detalle_text = detalle.get("1.0", "end-1c").strip()

            if not comercio or not total_str:
                messagebox.showwarning("Campos requeridos", "Comercio y Total son obligatorios.")
                return
            try:
                total = float(total_str)
            except ValueError:
                messagebox.showwarning("Total inválido", "Ingresa un valor numérico para el Total.")
                return

            trans_id = insertar_transaccion(
                comercio=comercio, fecha=fecha, total=total,
                detalle=detalle_text, tipo_documento=tipo_doc,
                serie_numero=serie, ruc=ruc, qr_raw="",
                moneda="PEN",
            )
            if cat_var:
                for c in listar_categorias():
                    if f"{c['icono']} {c['nombre']}" == cat_var:
                        actualizar_categoria_transaccion(trans_id, c["id"])
                        break

            ventana.destroy()
            self.cargar_resumen()
            messagebox.showinfo("Registrado", f"Factura de {comercio} por $ {self._formatear_total(total)} registrada.")

        btn_frame = tk.Frame(main, bg=C_SURFACE3)
        btn_frame.pack(fill="x", pady=(12, 0))
        tk.Button(btn_frame, text="✅  Guardar", command=_guardar_manual,
                  bg=C_ACCENT, fg="white", bd=0, padx=16, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#6d28d9").pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="Cancelar", command=ventana.destroy,
                  bg=C_SURFACE3, fg=C_INK2, bd=1, relief="solid", padx=14, pady=5,
                  font=("Segoe UI", 9), cursor="hand2",
                  activebackground=C_SURFACE2).pack(side="left")
        return ventana

    def cargar_historial(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        trans = listar_transacciones(limite=200)
        for t in trans:
            cat = t.get("categoria_icono", "📁") or "📁"
            tag = t.get("categoria_nombre", "Otros") or "Otros"
            total_str = self._formatear_total(t["total"])
            self.tree.insert("", "end", values=(t["id"], t["fecha"], t["comercio"], f"{cat} {tag}", f"$ {total_str}"))

    def eliminar_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Seleccionar", "Selecciona una transacción de la lista")
            return
        item = self.tree.item(seleccion[0])
        trans_id = item["values"][0]
        comercio = item["values"][2]
        if messagebox.askyesno("Confirmar eliminación",
                                f"¿Seguro que quieres eliminar la factura de\n{comercio}?",
                                icon="warning"):
            eliminar_transaccion(trans_id)
            self.cargar_historial()
            self.cargar_resumen()

    def editar_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Seleccionar", "Selecciona una transacción de la lista")
            return
        item = self.tree.item(seleccion[0])
        trans_id = item["values"][0]
        trans = obtener_transaccion(trans_id)
        if not trans:
            messagebox.showerror("Error", "No se encontró la transacción")
            return
        self._abrir_ventana_edicion(trans)

    def _abrir_ventana_edicion(self, trans):
        ventana = tk.Toplevel(self.root)
        ventana.title("Editar Transacción")
        ventana.geometry("560x540")
        ventana.transient(self.root)
        ventana.grab_set()

        main = tk.Frame(ventana, bg=C_SURFACE3, padx=20, pady=16)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Editar datos de la transacción", bg=C_SURFACE3, fg=C_INK,
                 font=(FONT_TITLE_FAMILY, 14)).pack(anchor="w", pady=(0, 4))

        # Nota flotante DIAN
        nota_frame = tk.Frame(main, bg=C_WARNING_LIGHT, bd=1, relief="solid", highlightbackground=C_WARNING)
        nota_frame.pack(fill="x", pady=(0, 12))
        tk.Label(nota_frame, text="ℹ️  DIAN: Si el producto no pudo ser registrado, ingrese el valor y el nombre manualmente",
                 bg=C_WARNING_LIGHT, fg=C_INK, font=("Segoe UI", 9), wraplength=480, justify="left",
                 padx=10, pady=8).pack()

        campos = tk.Frame(main, bg=C_SURFACE3)
        campos.pack(fill="both", expand=True)

        labels = ["Comercio:", "Fecha:", "Total:", "RUC:", "Tipo Doc.:", "Serie:", "Categoría:"]
        entries = {}
        for i, l in enumerate(labels):
            tk.Label(campos, text=l, bg=C_SURFACE3, fg=C_INK,
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if l == "Categoría:":
                var = tk.StringVar()
                cats = listar_categorias()
                combo = ttk.Combobox(campos, textvariable=var, state="readonly",
                                     width=40, font=("Segoe UI", 10))
                combo["values"] = [f"{c['icono']} {c['nombre']}" for c in cats]
                cat_actual = next((f"{c['icono']} {c['nombre']}" for c in cats
                                   if c["id"] == trans.get("categoria_id")), None)
                if cat_actual:
                    combo.set(cat_actual)
                elif cats:
                    combo.current(len(cats) - 1)
                combo.grid(row=i, column=1, sticky="ew", pady=4)
                entries[l] = var
            else:
                var = tk.StringVar()
                entry = tk.Entry(campos, textvariable=var, width=40,
                                 font=("Segoe UI", 10),
                                 bd=1, relief="solid", highlightbackground=C_BORDER_TK)
                entry.grid(row=i, column=1, sticky="ew", pady=4)
                entries[l] = var

        entries["Comercio:"].set(trans["comercio"])
        entries["Fecha:"].set(trans["fecha"])
        entries["Total:"].set(str(trans["total"]))
        entries["RUC:"].set(trans.get("ruc", "") or "")
        entries["Tipo Doc.:"].set(trans.get("tipo_documento", "") or "")
        entries["Serie:"].set(trans.get("serie_numero", "") or "")

        # Texto "sin puntos ni comas" al lado del total
        sin_puntos = tk.Label(campos, text="sin puntos ni comas", bg=C_SURFACE3,
                              fg=C_INK3, font=("Segoe UI", 8))
        sin_puntos.grid(row=labels.index("Total:"), column=2, sticky="w", padx=(4, 0), pady=4)

        tk.Label(campos, text="Detalle:", bg=C_SURFACE3, fg=C_INK,
                 font=("Segoe UI", 10)).grid(row=len(labels), column=0, sticky="nw", pady=4)
        detalle = scrolledtext.ScrolledText(campos, width=40, height=4,
                                            font=("Segoe UI", 9),
                                            bd=1, relief="solid")
        detalle.grid(row=len(labels), column=1, sticky="ew", pady=4)
        detalle.insert("1.0", trans.get("detalle", "") or "")

        def _guardar_edicion():
            comercio = entries["Comercio:"].get().strip()
            fecha = entries["Fecha:"].get().strip()
            total_str = entries["Total:"].get().strip().replace(",", "")
            ruc = entries["RUC:"].get().strip()
            tipo_doc = entries["Tipo Doc.:"].get().strip()
            serie = entries["Serie:"].get().strip()
            cat_texto = entries["Categoría:"].get().strip()
            detalle_text = detalle.get("1.0", "end-1c").strip()

            if not comercio:
                messagebox.showwarning("Campo requerido", "El comercio es obligatorio.")
                return
            try:
                total_val = float(total_str) if total_str else 0.0
            except ValueError:
                messagebox.showwarning("Total inválido",
                    "Ingresa un valor numérico para el Total (sin puntos ni comas).")
                return

            actualizar_transaccion(
                trans["id"],
                comercio=comercio,
                fecha=fecha,
                total=total_val,
                detalle=detalle_text,
                tipo_documento=tipo_doc,
                serie_numero=serie,
                ruc=ruc,
            )
            if cat_texto:
                for c in listar_categorias():
                    if f"{c['icono']} {c['nombre']}" == cat_texto:
                        actualizar_categoria_transaccion(trans["id"], c["id"])
                        break

            ventana.destroy()
            self.cargar_historial()
            self.cargar_resumen()
            messagebox.showinfo("Editado", f"Transacción de {comercio} actualizada.")

        btn_frame = tk.Frame(main, bg=C_SURFACE3)
        btn_frame.pack(fill="x", pady=(12, 0))
        tk.Button(btn_frame, text="✅  Guardar cambios", command=_guardar_edicion,
                  bg=C_ACCENT, fg="white", bd=0, padx=16, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#6d28d9").pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="Cancelar", command=ventana.destroy,
                  bg=C_SURFACE3, fg=C_INK2, bd=1, relief="solid", padx=14, pady=5,
                  font=("Segoe UI", 9), cursor="hand2",
                  activebackground=C_SURFACE2).pack(side="left")

    def _mes_anio_seleccionados(self):
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_nombre = self.reporte_mes_var.get()
        mes = meses.index(mes_nombre) + 1
        anio = int(self.reporte_anio_var.get())
        return mes, anio

    def cargar_reporte(self):
        mes, anio = self._mes_anio_seleccionados()
        reporter = Reporter()
        texto = reporter.texto_reporte_mensual(anio, mes)
        self.reporte_text.config(state="normal")
        self.reporte_text.delete("1.0", "end")
        self.reporte_text.insert("1.0", texto)
        self.reporte_text.config(state="disabled")

    def _generar_pdf(self, ruta, mes, anio):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rlcanvas
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        _pdf_title_font = "Helvetica-Bold"

        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
        nombre_mes = meses[mes-1]
        reporter = Reporter()
        datos = reporter.reporte_mensual(anio, mes)
        r = datos["resumen"]
        curr_total = r['gasto_total']
        curr_txns = r['total_transacciones']
        curr_avg = r['promedio_por_transaccion']

        mes_prev = mes - 1
        anio_prev = anio
        if mes_prev == 0:
            mes_prev = 12
            anio_prev -= 1
        prev = calcular_resumen_mensual(anio_prev, mes_prev)
        prev_total = prev['gasto_total']
        prev_txns = prev['total_transacciones']
        prev_avg = prev['promedio_por_transaccion']

        PURPLE = colors.HexColor("#7C3AED")
        PURPLE_LIGHT = colors.HexColor("#EDE9FE")
        TEAL = colors.HexColor("#0F6E56")
        GRAY_DARK = colors.HexColor("#1E1136")
        GRAY_MID = colors.HexColor("#888780")
        GRAY_LIGHT = colors.HexColor("#F1EFE8")
        WHITE = colors.white
        RED_MID = colors.HexColor("#E24B4A")
        GREEN_MID = colors.HexColor("#639922")
        W, H = A4

        def fmt(n):
            return f"$ {n:,.0f}"

        def pct_diff(c, p):
            if p == 0: return 0
            return (c - p) / p * 100

        def draw_rect(cnv, x, y, w, h, fill=None, stroke=None, radius=4):
            cnv.saveState()
            if fill:
                cnv.setFillColor(fill)
            if stroke:
                cnv.setStrokeColor(stroke)
                cnv.setLineWidth(0.5)
            else:
                cnv.setLineWidth(0)
            p = cnv.beginPath()
            p.roundRect(x, y, w, h, radius)
            cnv.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)
            cnv.restoreState()

        def draw_text(cnv, text, x, y, size=10, color=GRAY_DARK, bold=False, align="left"):
            cnv.saveState()
            cnv.setFillColor(color)
            cnv.setFont(_pdf_title_font if bold else "Helvetica", size)
            if align == "right":
                cnv.drawRightString(x, y, text)
            elif align == "center":
                cnv.drawCentredString(x, y, text)
            else:
                cnv.drawString(x, y, text)
            cnv.restoreState()

        def draw_line(cnv, x1, y1, x2, y2, color=GRAY_LIGHT, width=0.5):
            cnv.saveState()
            cnv.setStrokeColor(color)
            cnv.setLineWidth(width)
            cnv.line(x1, y1, x2, y2)
            cnv.restoreState()

        def kpi_card(cnv, x, y, w, h, label, value, sub, accent=PURPLE):
            draw_rect(cnv, x, y, w, h, fill=GRAY_LIGHT, radius=6)
            draw_text(cnv, label.upper(), x+10, y+h-16, size=7, color=GRAY_MID)
            draw_text(cnv, value, x+10, y+h-38, size=18, color=accent, bold=True)
            draw_text(cnv, sub, x+10, y+10, size=8, color=GRAY_MID)

        def delta_badge(cnv, x, y, curr, prev_val, bigger_is_bad=False):
            diff = pct_diff(curr, prev_val)
            up = diff >= 0
            color = RED_MID if (up and bigger_is_bad) or (not up and not bigger_is_bad) else GREEN_MID
            arrow = "+" if up else ""
            label = f"{arrow}{diff:.1f}% vs {meses[mes_prev-1].lower()}"
            draw_text(cnv, label, x, y, size=8, color=color)

        def _pdf_amount_color(v):
            if v > 100000: return colors.HexColor("#dc2626")
            elif v > 50000: return colors.HexColor("#d97706")
            elif v > 20000: return colors.HexColor("#16a34a")
            else: return colors.HexColor("#2563eb")

        CHART_CURR = colors.HexColor("#7F77DD")
        CHART_PREV = colors.HexColor("#CECBF6")

        C = rlcanvas.Canvas(ruta, pagesize=A4)
        margin = 22*mm
        from datetime import date
        hoy = date.today()

        draw_rect(C, 0, H-56, W, 56, fill=GRAY_DARK)
        draw_text(C, "Pocket", margin, H-24, size=20, color=WHITE, bold=True)
        draw_text(C, "FORA", margin+62, H-24, size=20, color=PURPLE, bold=True)
        draw_text(C, "Reporte mensual de gastos", margin, H-40, size=9, color=GRAY_MID)
        draw_text(C, f"{nombre_mes.upper()} {anio}", W-margin, H-24, size=9, color=PURPLE_LIGHT, bold=True, align="right")
        draw_text(C, f"Generado el {hoy.day:02d} {meses[hoy.month-1].lower()} {hoy.year}", W-margin, H-40, size=8, color=GRAY_MID, align="right")

        y_cursor = H - 56 - 24

        kw = (W - 2*margin - 16) / 3
        kh = 58
        ky = y_cursor - kh
        kpi_card(C, margin, ky, kw, kh, "Total gastado", fmt(curr_total), "este mes", _pdf_amount_color(curr_total))
        kpi_card(C, margin+kw+8, ky, kw, kh, "Transacciones", str(curr_txns), "este mes", TEAL)
        kpi_card(C, margin+2*(kw+8), ky, kw, kh, "Promedio por tx", fmt(curr_avg), "por transaccion", _pdf_amount_color(curr_avg))

        delta_badge(C, margin+8, ky-16, curr_total, prev_total, bigger_is_bad=True)
        delta_badge(C, margin+kw+8+8, ky-16, curr_txns, prev_txns, bigger_is_bad=True)
        delta_badge(C, margin+2*(kw+8)+8, ky-16, curr_avg, prev_avg, bigger_is_bad=True)

        y_cursor = ky - 28

        draw_text(C, f"COMPARATIVA — {nombre_mes.upper()} VS {meses[mes_prev-1].upper()} {anio_prev}",
                  margin, y_cursor, size=9, color=GRAY_MID, bold=True)
        draw_line(C, margin, y_cursor-5, W-margin, y_cursor-5)
        y_cursor -= 18

        col_x = [margin, margin+130, margin+220, margin+300, margin+380]
        headers = ["Indicador", f"{meses[mes_prev-1]} {anio_prev}", f"{nombre_mes} {anio}", "Diferencia", "Cambio %"]
        for i, h_label in enumerate(headers):
            align_h = "right" if i > 0 else "left"
            draw_text(C, h_label, col_x[i], y_cursor, size=8, color=GRAY_MID, bold=True, align=align_h)
        draw_line(C, margin, y_cursor-5, W-margin, y_cursor-5)
        y_cursor -= 18

        def _pct_diff_str(curr_v, prev_v):
            d = pct_diff(curr_v, prev_v)
            return f"{d:+.1f}%"

        rows = [
            ("Total gastado",  fmt(prev_total), fmt(curr_total), fmt(curr_total-prev_total), _pct_diff_str(curr_total, prev_total), True),
            ("Transacciones",  str(prev_txns),  str(curr_txns),  str(curr_txns-prev_txns),   _pct_diff_str(curr_txns, prev_txns), True),
            ("Promedio por tx", fmt(prev_avg),  fmt(curr_avg),   fmt(curr_avg-prev_avg),     _pct_diff_str(curr_avg, prev_avg), True),
        ]

        for label, v_prev, v_curr, diff_val, diff_pct_str, bad_if_up in rows:
            val = float(diff_pct_str.replace('%','').replace('+',''))
            is_up = val >= 0
            d_color = RED_MID if (is_up and bad_if_up) else GREEN_MID
            draw_text(C, label, col_x[0], y_cursor, size=9)
            draw_text(C, v_prev, col_x[1], y_cursor, size=9, color=GRAY_MID, align="right")
            _cv = float(v_curr.replace("$ ","").replace(",",""))
            _c = _pdf_amount_color(_cv)
            draw_text(C, v_curr, col_x[2], y_cursor, size=9, color=_c, bold=True, align="right")
            draw_text(C, diff_val, col_x[3], y_cursor, size=9, color=d_color, align="right")
            draw_text(C, diff_pct_str, col_x[4], y_cursor, size=9, color=d_color, bold=True, align="right")
            y_cursor -= 5
            draw_line(C, margin, y_cursor, W-margin, y_cursor, color=GRAY_LIGHT)
            y_cursor -= 13

        y_cursor -= 14

        draw_text(C, "EVOLUCION MENSUAL", margin, y_cursor, size=9, color=GRAY_MID, bold=True)
        draw_line(C, margin, y_cursor-5, W-margin, y_cursor-5)
        y_cursor -= 20

        months_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                         "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
        months_curr = []
        months_prev = []
        for i in range(6):
            m = mes - 5 + i
            a = anio
            while m < 1:
                m += 12
                a -= 1
            while m > 12:
                m -= 12
                a += 1
            r_m = calcular_resumen_mensual(a, m)
            months_curr.append(r_m['gasto_total'])
            r_prev = calcular_resumen_mensual(a, m-1 if m > 1 else 12)
            months_prev.append(r_prev['gasto_total'])

        fig, ax = plt.subplots(figsize=(5.4, 2.1), dpi=150)
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")
        x = range(6)
        bw = 0.3
        ax.bar([i - bw/2 for i in x], months_prev, width=bw,
               color="#CECBF6", label="Mes anterior", zorder=3, edgecolor="#AFA9EC", linewidth=0.5)
        ax.bar([i + bw/2 for i in x], months_curr, width=bw,
               color="#7F77DD", label="Mes actual", zorder=3, edgecolor="#534AB7", linewidth=0.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels([months_labels[(mes-5+i) % 12] for i in range(6)], fontsize=9, color="#888780")
        ax.yaxis.set_visible(False)
        for s in ['top', 'right', 'left']:
            ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color("#D3D1C7")
        ax.tick_params(axis='x', colors='#888780', length=0)
        ax.set_axisbelow(True)
        ax.legend(fontsize=9, frameon=False, labelcolor="#888780", loc="upper left")
        plt.tight_layout(pad=0.5)
        import tempfile as _tf
        chart_file = _tf.NamedTemporaryFile(delete=False, suffix=".png")
        plt.savefig(chart_file.name, format='png', transparent=True, dpi=150)
        plt.close()

        chart_h = 100
        C.drawImage(chart_file.name, margin, y_cursor-chart_h, width=W-2*margin, height=chart_h)
        chart_file.close()
        os.unlink(chart_file.name)
        y_cursor -= chart_h + 18

        draw_text(C, "ULTIMAS TRANSACCIONES", margin, y_cursor, size=9, color=GRAY_MID, bold=True)
        draw_line(C, margin, y_cursor-5, W-margin, y_cursor-5)
        y_cursor -= 20

        for t in datos["transacciones"][:15]:
            tx_color = _pdf_amount_color(t['total'])
            C.saveState()
            C.setFillColor(tx_color)
            C.circle(margin+5, y_cursor+4, 4, fill=1, stroke=0)
            C.restoreState()
            comercio_limpio = t['comercio'].encode('latin-1', 'replace').decode('latin-1')
            draw_text(C, comercio_limpio, margin+16, y_cursor+5, size=10, bold=True)
            draw_text(C, t['fecha'], margin+16, y_cursor-6, size=8, color=GRAY_MID)
            draw_text(C, fmt(t['total']), W-margin, y_cursor+4, size=11, color=tx_color, bold=True, align="right")
            y_cursor -= 7
            draw_line(C, margin, y_cursor, W-margin, y_cursor, color=GRAY_LIGHT)
            y_cursor -= 15

        draw_rect(C, 0, 0, W, 24, fill=GRAY_LIGHT)
        draw_text(C, f"PocketFora · Reporte generado automaticamente · Datos al {hoy.day:02d} {meses[hoy.month-1].lower()} {hoy.year}",
                  margin, 8, size=7.5, color=GRAY_MID)
        draw_text(C, "Pagina 1 de 1", W-margin, 8, size=7.5, color=GRAY_MID, align="right")

        C.showPage()
        C.save()

    def descargar_pdf(self):
        from tkinter import filedialog
        mes, anio = self._mes_anio_seleccionados()
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
        nombre_mes = meses[mes-1]
        nombre_defecto = f"Reporte_{nombre_mes}_{anio}.pdf"
        ruta = filedialog.asksaveasfilename(
            title="Guardar reporte PDF",
            defaultextension=".pdf",
            initialfile=nombre_defecto,
            filetypes=[("PDF", "*.pdf")]
        )
        if not ruta:
            return
        try:
            self._generar_pdf(ruta, mes, anio)
            messagebox.showinfo("PDF", f"Reporte guardado en:\n{ruta}")
        except Exception as e:
            import traceback
            messagebox.showerror("Error PDF", f"No se pudo generar el PDF:\n{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


def main():
    root = tk.Tk()
    app = PocketForaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
