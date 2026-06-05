import io
import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image as KivyImage

import cv2
import numpy as np

from database.db_manager import (inicializar, insertar_transaccion, insertar_producto,
                                  listar_transacciones, listar_categorias,
                                  actualizar_categoria_transaccion, eliminar_transaccion,
                                  calcular_gastos_mensuales, calcular_resumen_mensual,
                                  obtener_transaccion, obtener_productos)
from parser.invoice_parser import InvoiceParser
from scanner.qr_scanner import QRScanner
from analysis.reporter import Reporter


class EscanerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scanner = None
        self.ultimo_texto_qr = ""
        self.evento_camara = None
        self.parser = InvoiceParser()

    def on_enter(self):
        try:
            self.scanner = QRScanner()
            self.scanner.abrir_camara()
            self.evento_camara = Clock.schedule_interval(self.actualizar_camara, 1.0 / 30)
        except Exception as e:
            self.ids.status_label.text = f"Error cámara: {e}"

    def on_leave(self):
        if self.evento_camara:
            self.evento_camara.cancel()
            self.evento_camara = None
        if self.scanner:
            self.scanner.cerrar_camara()
            self.scanner = None

    def actualizar_camara(self, dt):
        if not self.scanner or not self.scanner.cap:
            return
        try:
            ret, frame = self.scanner.cap.read()
            if not ret:
                return
            frame, codigos = self.scanner.escanear_frame(frame)
            buf = cv2.flip(frame, 0)
            buf = cv2.cvtColor(buf, cv2.COLOR_BGR2RGB)
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="rgb")
            texture.blit_buffer(buf.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
            self.ids.camera_image.texture = texture
            if codigos:
                self.ultimo_texto_qr = codigos[0]["datos"]
                self.ids.status_label.text = "¡QR Detectado!"
                self.ids.status_label.color = (0, 1, 0, 1)
                Clock.schedule_once(lambda dt: self.procesar_qr(), 0.5)
        except Exception as e:
            self.ids.status_label.text = f"Error: {e}"

    def procesar_qr(self):
        if not self.ultimo_texto_qr:
            return
        if self.evento_camara:
            self.evento_camara.cancel()
        datos = self.parser.parsear(self.ultimo_texto_qr)
        trans_id = insertar_transaccion(
            comercio=datos.comercio,
            fecha=datos.fecha,
            total=datos.total,
            detalle=datos.detalle,
            tipo_documento=datos.tipo_documento,
            serie_numero=datos.serie_numero,
            ruc=datos.ruc,
            qr_raw=self.ultimo_texto_qr,
            moneda=datos.moneda,
        )
        for prod in datos.productos:
            insertar_producto(trans_id, prod["descripcion"], prod["cantidad"],
                              prod["precio_unitario"], prod.get("subtotal", 0))
        self.ultimo_texto_qr = ""
        app = App.get_running_app()
        app.root.get_screen("confirmar").cargar_transaccion(trans_id)
        app.root.current = "confirmar"

    def capturar_manual(self):
        if self.ultimo_texto_qr:
            self.procesar_qr()


class ConfirmarScreen(Screen):
    transaccion_id = NumericProperty(0)
    comercio = StringProperty("")
    fecha = StringProperty("")
    total = StringProperty("")
    detalle = StringProperty("")
    tipo_doc = StringProperty("")
    serie = StringProperty("")
    ruc = StringProperty("")

    def cargar_transaccion(self, trans_id):
        self.transaccion_id = trans_id
        trans = obtener_transaccion(trans_id)
        if not trans:
            return
        self.comercio = trans["comercio"]
        self.fecha = trans["fecha"]
        self.total = f"S/ {trans['total']:.2f}"
        self.detalle = trans.get("detalle", "") or ""
        self.tipo_doc = trans.get("tipo_documento", "") or ""
        self.serie = trans.get("serie_numero", "") or ""
        self.ruc = trans.get("ruc", "") or ""
        categorias = listar_categorias()
        self.ids.categoria_spinner.values = [f"{c['icono']} {c['nombre']}" for c in categorias]
        self.ids.categoria_spinner.text = "📁 Otros"

    def guardar(self):
        texto_cat = self.ids.categoria_spinner.text
        categorias = listar_categorias()
        for c in categorias:
            if f"{c['icono']} {c['nombre']}" == texto_cat:
                actualizar_categoria_transaccion(self.transaccion_id, c["id"])
                break
        app = App.get_running_app()
        app.root.current = "principal"

    def descartar(self):
        eliminar_transaccion(self.transaccion_id)
        app = App.get_running_app()
        app.root.current = "principal"


class HistorialScreen(Screen):
    def on_enter(self):
        self.cargar_historial()

    def cargar_historial(self):
        scroll = self.ids.historial_scroll
        scroll.clear_widgets()
        transacciones = listar_transacciones(limite=100)
        if not transacciones:
            scroll.add_widget(Label(text="No hay transacciones registradas",
                                    size_hint_y=None, height=dp(40)))
            return
        layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        layout.bind(minimum_height=layout.setter("height"))
        for t in transacciones:
            card = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50),
                             padding=dp(8), spacing=dp(8))
            icono = t.get("categoria_icono", "📁") or "📁"
            info = Label(
                text=f"[{t['fecha']}] {icono} {t['comercio']}",
                size_hint_x=0.6, halign="left", valign="middle",
                text_size=(None, None), markup=True
            )
            monto = Label(
                text=f"S/ {t['total']:.2f}",
                size_hint_x=0.3, halign="right", valign="middle"
            )
            card.add_widget(info)
            card.add_widget(monto)
            layout.add_widget(card)
        scroll.add_widget(layout)


class ReporteScreen(Screen):
    def on_enter(self):
        self.generar_reporte()

    def generar_reporte(self, anio=None, mes=None):
        scroll = self.ids.reporte_scroll
        scroll.clear_widgets()
        reporter = Reporter()
        texto = reporter.texto_reporte_mensual(anio, mes)
        label = Label(
            text=texto,
            size_hint_y=None,
            halign="left",
            valign="top",
            markup=True,
            font_size=dp(13),
            padding=(dp(10), dp(10)),
        )
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1] + dp(20)))
        scroll.add_widget(label)


class InicioScreen(Screen):
    def on_enter(self):
        self.mostrar_resumen()

    def mostrar_resumen(self):
        ahora = datetime.now()
        resumen = calcular_resumen_mensual(ahora.year, ahora.month)
        self.ids.total_label.text = f"S/ {resumen['gasto_total']:.2f}"
        self.ids.transacciones_label.text = f"{resumen['total_transacciones']} transacciones"

    def ir_a_escaner(self):
        self.manager.current = "escaner"

    def ir_a_historial(self):
        self.manager.current = "historial"

    def ir_a_reporte(self):
        self.manager.current = "reporte"


class PocketForaApp(App):
    def build(self):
        inicializar()
        sm = ScreenManager()
        sm.add_widget(InicioScreen(name="principal"))
        sm.add_widget(EscanerScreen(name="escaner"))
        sm.add_widget(ConfirmarScreen(name="confirmar"))
        sm.add_widget(HistorialScreen(name="historial"))
        sm.add_widget(ReporteScreen(name="reporte"))
        return sm


if __name__ == "__main__":
    PocketForaApp().run()
