import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from parser.invoice_parser import InvoiceParser


class TestInvoiceParser(unittest.TestCase):

    def setUp(self):
        self.parser = InvoiceParser()

    def test_parsear_sunat_formato(self):
        texto = "RUC: 20123456789|TIPO: 01|SERIE: F001|NUMERO: 000123|TOTAL: 150.00|IGV: 27.00|FECHA: 15/01/2025"
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.ruc, "20123456789")
        self.assertEqual(datos.tipo_documento, "Factura")
        self.assertEqual(datos.serie_numero, "F001-000123")
        self.assertEqual(datos.total, 150.00)
        self.assertEqual(datos.fecha, "2025-01-15")

    def test_parsear_sunat_boleta(self):
        texto = "RUC: 20876543210|TIPO: 03|SERIE: B001|NUMERO: 000456|TOTAL: 89.90|FECHA: 20/03/2025"
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.ruc, "20876543210")
        self.assertEqual(datos.tipo_documento, "Boleta")
        self.assertEqual(datos.total, 89.90)
        self.assertEqual(datos.fecha, "2025-03-20")

    def test_parsear_json_formato(self):
        texto = '{"comercio": "Supermercado ABC", "fecha": "2025-06-01", "total": 250.50, "moneda": "PEN", "ruc": "20123456789"}'
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.comercio, "Supermercado ABC")
        self.assertEqual(datos.fecha, "2025-06-01")
        self.assertEqual(datos.total, 250.50)
        self.assertEqual(datos.ruc, "20123456789")

    def test_parsear_json_con_productos(self):
        texto = '{"comercio": "Tienda XYZ", "total": 100.00, "productos": [{"descripcion": "Producto A", "cantidad": 2, "precioUnitario": 25.00, "total": 50.00}, {"descripcion": "Producto B", "cantidad": 1, "precioUnitario": 50.00, "total": 50.00}]}'
        datos = self.parser.parsear(texto)
        self.assertEqual(len(datos.productos), 2)
        self.assertEqual(datos.productos[0]["descripcion"], "Producto A")
        self.assertEqual(datos.productos[0]["cantidad"], 2)
        self.assertEqual(datos.total, 100.00)

    def test_parsear_clave_valor(self):
        texto = """RUC: 20123456789
Razón Social: Mi Comercio S.A.C.
Total: S/ 350.00
Fecha: 10/02/2025
Moneda: PEN"""
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.ruc, "20123456789")
        self.assertEqual(datos.comercio, "Mi Comercio S.A.C.")
        self.assertEqual(datos.total, 350.00)
        self.assertEqual(datos.fecha, "2025-02-10")

    def test_parsear_texto_libre(self):
        texto = """Supermercado La Casa
Av. Principal 123
RUC: 20123456789
Total: S/ 125.00
15/03/2025"""
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.comercio, "Supermercado La Casa")
        self.assertEqual(datos.ruc, "20123456789")
        self.assertEqual(datos.total, 125.00)
        self.assertEqual(datos.fecha, "2025-03-15")

    def test_parsear_texto_vacio(self):
        datos = self.parser.parsear("")
        self.assertEqual(datos.comercio, "Desconocido")
        self.assertEqual(datos.total, 0.0)

    def test_normalizar_fecha_dmy(self):
        resultado = self.parser._normalizar_fecha("25/12/2025")
        self.assertEqual(resultado, "2025-12-25")

    def test_normalizar_fecha_ymd(self):
        resultado = self.parser._normalizar_fecha("2025-06-15")
        self.assertEqual(resultado, "2025-06-15")

    def test_parsear_numero_con_formato(self):
        valor = self.parser._parsear_numero("S/ 1,234.56")
        self.assertAlmostEqual(valor, 1234.56, places=2)

    def test_parsear_numero_entero(self):
        valor = self.parser._parsear_numero("150")
        self.assertEqual(valor, 150.0)

    def test_parsear_tipo_documento_factura(self):
        texto = "RUC: 20123456789|TIPO: 01|SERIE: F001|NUMERO: 1|TOTAL: 100.00|FECHA: 01/01/2025"
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.tipo_documento, "Factura")

    def test_parsear_tipo_documento_boleta(self):
        texto = "RUC: 20123456789|TIPO: 03|SERIE: B001|NUMERO: 1|TOTAL: 100.00|FECHA: 01/01/2025"
        datos = self.parser.parsear(texto)
        self.assertEqual(datos.tipo_documento, "Boleta")


if __name__ == "__main__":
    unittest.main()
