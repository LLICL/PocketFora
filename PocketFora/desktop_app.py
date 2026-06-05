import sys
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import (inicializar, insertar_transaccion, insertar_producto,
                                  listar_transacciones, listar_categorias,
                                  actualizar_categoria_transaccion, eliminar_transaccion,
                                  calcular_gastos_mensuales, calcular_resumen_mensual,
                                  obtener_transaccion, conectar)
from parser.invoice_parser import InvoiceParser
from scanner.qr_scanner import QRScanner
from analysis.reporter import Reporter

# ── Colores del diseño ──
C_INK          = "#1a1a2e"
C_INK2         = "#3a3a5c"
C_INK3         = "#7c7c9a"
C_SURFACE      = "#f5f4f0"
C_SURFACE2     = "#ede9e1"
C_SURFACE3     = "#ffffff"
C_ACCENT       = "#2563eb"
C_ACCENT_LIGHT = "#dbeafe"
C_DANGER       = "#dc2626"
C_DANGER_LIGHT = "#fee2e2"
C_SUCCESS      = "#16a34a"
C_SUCCESS_LIGHT= "#dcfce7"
C_WARNING      = "#d97706"
C_WARNING_LIGHT= "#fef3c7"
C_BORDER       = "#1c1c33"
C_BORDER_TK    = "#e0dfdb"

FONT_HEAD = ("Segoe UI", 10, "bold")
FONT_BODY = ("Segoe UI", 10)


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

        icon_frame = tk.Frame(logo_frame, bg=C_ACCENT, width=34, height=34)
        icon_frame.pack(side="left", padx=(0, 10))
        icon_frame.pack_propagate(False)
        lbl_icon = tk.Label(icon_frame, text="🏪", bg=C_ACCENT, fg="white", font=("Segoe UI", 14))
        lbl_icon.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(logo_frame, text="PocketFora", bg=C_INK, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(logo_frame, text="Gestión de gastos", bg=C_INK,
                 fg="#71717d", font=("Segoe UI", 9)).pack(anchor="w")

        nav_frame = tk.Frame(self.sidebar, bg=C_INK)
        nav_frame.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        titulos = [
            ("PRINCIPAL", [
                ("inicio",    "Inicio",      "◈"),
                ("escaner",   "Escanear",    "◈"),
                ("historial", "Historial",   "◈"),
            ]),
            ("ANÁLISIS", [
                ("reporte",   "Reporte",     "◈"),
            ]),
        ]

        self.nav_labels = {}

        for seccion, items in titulos:
            tk.Label(nav_frame, text=seccion, bg=C_INK,
                     fg="#5a5a68", font=("Segoe UI", 8, "bold"),
                     anchor="w", padx=8).pack(fill="x", pady=(14, 4))
            for key, texto, icono in items:
                lbl = tk.Label(nav_frame, text=f"  {icono}  {texto}", bg=C_INK,
                               fg="#91919a",
                               font=("Segoe UI", 10), anchor="w", padx=10, pady=7,
                               cursor="hand2")
                lbl.pack(fill="x")
                lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg="#252540") if l != self.nav_labels.get(self.current_page) else None)
                lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=C_INK) if l != self.nav_labels.get(self.current_page) else None)
                lbl.bind("<Button-1>", lambda e, k=key: self._navegar(k))
                self.nav_labels[key] = lbl

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
                                      font=("Segoe UI", 16, "bold"), anchor="w")
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
                old.config(bg=C_INK, fg="#91919a")
        self.current_page = nombre
        self.paginas[nombre].grid()
        new = self.nav_labels.get(nombre)
        if new:
            new.config(bg="#252540", fg="white")
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

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # wrap in a frame with padding
        container = tk.Frame(scroll_frame, bg=C_SURFACE)
        container.pack(fill="both", expand=True, padx=22, pady=16)

        # ── Banner QR ──
        banner = tk.Frame(container, bg=C_ACCENT_LIGHT, bd=0, highlightbackground="#1c2853", highlightthickness=1)
        banner.pack(fill="x", pady=(0, 18))

        inner = tk.Frame(banner, bg=C_ACCENT_LIGHT)
        inner.pack(fill="both", padx=14, pady=12)

        icon_b = tk.Frame(inner, bg=C_ACCENT, width=36, height=36)
        icon_b.pack(side="left", padx=(0, 12))
        icon_b.pack_propagate(False)
        tk.Label(icon_b, text="◈", bg=C_ACCENT, fg="white",
                 font=("Segoe UI", 16)).place(relx=0.5, rely=0.5, anchor="center")

        txt_f = tk.Frame(inner, bg=C_ACCENT_LIGHT)
        txt_f.pack(side="left", fill="x", expand=True)
        tk.Label(txt_f, text="¿Tienes una factura nueva?", bg=C_ACCENT_LIGHT,
                 fg=C_INK, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(txt_f, text="Escanea el código QR para registrar el gasto automáticamente.",
                 bg=C_ACCENT_LIGHT, fg=C_INK2, font=("Segoe UI", 9), anchor="w").pack(fill="x")

        tk.Button(inner, text="Abrir escáner", bg="white", fg=C_ACCENT,
                  bd=1, relief="solid", highlightbackground="#2a4a8a",
                  padx=10, pady=4, font=("Segoe UI", 9, "bold"), cursor="hand2",
                  activebackground="#f0f6ff",
                  command=lambda: self._navegar("escaner")).pack(side="right")

        # ── Stats cards ──
        stats = tk.Frame(container, bg=C_SURFACE)
        stats.pack(fill="x", pady=(0, 16))
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform="stats")

        card_data = [
            ("Gasto total",   "danger",  "◆"),
            ("Transacciones", "blue",    "◆"),
            ("Promedio diario","green",  "◆"),
        ]

        self.stat_widgets = {}
        for i, (label, color, icon) in enumerate(card_data):
            border_color = {"danger": C_DANGER, "blue": C_ACCENT, "green": C_SUCCESS}[color]
            card = tk.Frame(stats, bg=C_SURFACE3, bd=0, highlightbackground=C_BORDER_TK, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=4)

            # left color bar
            bar = tk.Frame(card, bg=border_color, width=3)
            bar.pack(side="left", fill="y")

            body = tk.Frame(card, bg=C_SURFACE3)
            body.pack(side="left", fill="both", expand=True, padx=14, pady=12)

            tk.Label(body, text=f"{icon}  {label.upper()}", bg=C_SURFACE3,
                     fg=C_INK3, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x")

            value_color = C_DANGER if color == "danger" else C_INK
            val = tk.Label(body, text="S/ 0", bg=C_SURFACE3, fg=value_color,
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
                 fg=C_INK, font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left")

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
                 fg=C_INK, font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left")

        # bar chart canvas
        self.bar_canvas = tk.Canvas(chart_card, bg=C_SURFACE3, height=100,
                                     bd=0, highlightthickness=0)
        self.bar_canvas.pack(fill="x", padx=16, pady=(4, 2))

        # legend
        leg = tk.Frame(chart_card, bg=C_SURFACE3)
        leg.pack(fill="x", padx=16, pady=(0, 6))
        for color, text in [(C_ACCENT, "Mes actual"), ("#93c5fd", "Mes anterior"), (C_ACCENT_LIGHT, "Previos")]:
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
                 fg=C_INK, font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left")

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
                                              font=("Segoe UI", 10, "bold"),
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
                  activebackground="#1d4ed8").pack(side="left", padx=5)
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
        tk.Button(btn_frame, text="🗑️  Eliminar seleccionada", command=self.eliminar_seleccionada, **btn_st).pack(side="left", padx=2)

        columns = ("id", "fecha", "comercio", "categoria", "total")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=20)
        self.tree.heading("id", text="ID")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("comercio", text="Comercio")
        self.tree.heading("categoria", text="Categoría")
        self.tree.heading("total", text="Total")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("fecha", width=90)
        self.tree.column("comercio", width=230)
        self.tree.column("categoria", width=130)
        self.tree.column("total", width=90, anchor="e")

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

        btn_frame = tk.Frame(container, bg=C_SURFACE)
        btn_frame.pack(fill="x", pady=(0, 8))

        btn_st = {"bg": C_SURFACE3, "fg": C_INK2, "bd": 1, "relief": "solid",
                  "font": ("Segoe UI", 9), "padx": 12, "pady": 5, "cursor": "hand2",
                  "activebackground": C_SURFACE2}
        tk.Button(btn_frame, text="🔄  Generar Reporte", command=self.cargar_reporte, **btn_st).pack(side="left", padx=2)
        tk.Button(btn_frame, text="📄  Descargar PDF", command=self.descargar_pdf, **btn_st).pack(side="left", padx=2)

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
        total_f = self._formatear_total(resumen['gasto_total'])
        prom_f = self._formatear_total(resumen['promedio_por_transaccion'])

        # update stat widgets on dashboard
        card_gasto = self.stat_widgets.get("Gasto total", {}).get("val")
        if card_gasto:
            card_gasto.config(text=f"S/ {total_f}")
        card_tx = self.stat_widgets.get("Transacciones", {}).get("val")
        if card_tx:
            card_tx.config(text=str(resumen['total_transacciones']))
        card_prom = self.stat_widgets.get("Promedio diario", {}).get("val")
        if card_prom:
            card_prom.config(text=f"S/ {prom_f}")

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
            amt = tk.Label(row, text=f"S/ {self._formatear_total(t['total'])}",
                            bg=C_SURFACE3, fg=C_DANGER,
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

        w = self.bar_canvas.winfo_width() or 400
        h = 100
        if w < 50:
            w = 400
        self.bar_canvas.config(width=w)
        bar_w = (w - 40) / len(meses)
        max_v = max(totals) if max(totals) > 0 else 1

        for i, (m, v) in enumerate(zip(meses, totals)):
            pct = v / max_v
            bh = max(pct * (h - 30), 4)
            x0 = 20 + i * bar_w + 4
            x1 = x0 + bar_w - 8
            y0 = h - 20 - bh
            y1 = h - 20

            color = C_ACCENT if i == len(meses)-1 else "#93c5fd" if i == len(meses)-2 else C_ACCENT_LIGHT
            self.bar_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            lbl = f"S/{v:.0f}" if v == int(v) else f"S/{v:.1f}"
            self.bar_canvas.create_text((x0+x1)/2, y0-4, text=lbl,
                                         fill=C_INK2, font=("Segoe UI", 7, "bold"))
            self.bar_canvas.create_text((x0+x1)/2, h-6, text=m,
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
            tk.Label(top, text=f"S/ {self._formatear_total(c['total_gastado'])}",
                     bg=C_SURFACE3, fg=C_INK,
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
        self.lbl_estado.config(text="Leyendo imagen...", fg="blue")
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
        self.lbl_estado.config(text="Escaneando QR...", fg="blue")
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
        self.video_canvas.config(width=nuevo_w, height=nuevo_h)
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
        s = f"{valor:,.2f}".replace(",", ".")
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
            total_texto = self.entries["Total:"].get().replace(".", "").replace(",", ".").strip()
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

    def cargar_historial(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        trans = listar_transacciones(limite=200)
        for t in trans:
            cat = t.get("categoria_icono", "📁") or "📁"
            tag = t.get("categoria_nombre", "Otros") or "Otros"
            total_str = self._formatear_total(t["total"])
            self.tree.insert("", "end", values=(t["id"], t["fecha"], t["comercio"], f"{cat} {tag}", f"S/ {total_str}"))

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

    def cargar_reporte(self):
        reporter = Reporter()
        texto = reporter.texto_reporte_mensual()
        self.reporte_text.config(state="normal")
        self.reporte_text.delete("1.0", "end")
        self.reporte_text.insert("1.0", texto)
        self.reporte_text.config(state="disabled")

    def descargar_pdf(self):
        from fpdf import FPDF
        from tkinter import filedialog
        ruta = filedialog.asksaveasfilename(
            title="Guardar reporte PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not ruta:
            return
        try:
            reporter = Reporter()
            datos = reporter.reporte_mensual()
            pdf = FPDF()
            pdf.add_page()
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 12, f"PocketFora - Reporte {meses[datos['mes']-1]} {datos['anio']}", ln=True, align="C")
            pdf.ln(8)
            r = datos["resumen"]
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Resumen del Mes", ln=True)
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(0, 7, f"Total gastado: S/ {r['gasto_total']:.2f}", ln=True)
            pdf.cell(0, 7, f"Transacciones: {r['total_transacciones']}", ln=True)
            pdf.cell(0, 7, f"Promedio: S/ {r['promedio_por_transaccion']:.2f}", ln=True)
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Gasto por Categoria", ln=True)
            pdf.set_font("Helvetica", "", 11)
            for c in datos["categorias"]:
                if c["total_gastado"] > 0:
                    pct = (c["total_gastado"] / r["gasto_total"] * 100) if r["gasto_total"] > 0 else 0
                    nombre_limpio = c['nombre'].encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(0, 7, f"[{c['icono']}] {nombre_limpio}: S/ {c['total_gastado']:.2f} ({pct:.1f}%) - {c['cantidad']} trans.", ln=True)
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, f"Ultimas Transacciones ({len(datos['transacciones'])})", ln=True)
            pdf.set_font("Helvetica", "", 10)
            for t in datos["transacciones"][:15]:
                comercio_limpio = t['comercio'].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 6, f"[{t['fecha']}] {comercio_limpio}: S/ {t['total']:.2f}", ln=True)
            pdf.output(ruta)
            messagebox.showinfo("PDF", f"Reporte guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error PDF", f"No se pudo generar el PDF:\n{type(e).__name__}: {e}")


def main():
    root = tk.Tk()
    app = PocketForaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
