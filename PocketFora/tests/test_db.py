import sys
import os
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import db_manager


class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = os.path.join(self.temp_dir, "test_pocketfora.db")
        db_manager.inicializar()

    def tearDown(self):
        db_manager.DB_PATH = self.original_db_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_insertar_y_listar_transaccion(self):
        trans_id = db_manager.insertar_transaccion(
            comercio="Test Store",
            fecha="2025-06-01",
            total=100.50,
            detalle="Producto de prueba",
            tipo_documento="Boleta",
            serie_numero="B001-0001",
            ruc="20123456789",
            qr_raw="datos qr de prueba",
        )
        self.assertGreater(trans_id, 0)
        transacciones = db_manager.listar_transacciones()
        self.assertEqual(len(transacciones), 1)
        self.assertEqual(transacciones[0]["comercio"], "Test Store")
        self.assertEqual(transacciones[0]["total"], 100.50)

    def test_insertar_producto(self):
        trans_id = db_manager.insertar_transaccion(
            comercio="Tienda",
            fecha="2025-06-01",
            total=50.00,
        )
        db_manager.insertar_producto(
            transaccion_id=trans_id,
            descripcion="Producto A",
            cantidad=2,
            precio_unitario=25.00,
            subtotal=50.00,
        )
        productos = db_manager.obtener_productos(trans_id)
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0]["descripcion"], "Producto A")
        self.assertEqual(productos[0]["cantidad"], 2)

    def test_obtener_transaccion(self):
        trans_id = db_manager.insertar_transaccion(
            comercio="Mi Tienda",
            fecha="2025-06-15",
            total=200.00,
        )
        trans = db_manager.obtener_transaccion(trans_id)
        self.assertIsNotNone(trans)
        self.assertEqual(trans["comercio"], "Mi Tienda")
        self.assertEqual(trans["total"], 200.00)

    def test_actualizar_categoria(self):
        trans_id = db_manager.insertar_transaccion(
            comercio="Supermercado",
            fecha="2025-06-01",
            total=300.00,
        )
        categorias = db_manager.listar_categorias()
        self.assertGreater(len(categorias), 0)
        cat_id = categorias[0]["id"]
        db_manager.actualizar_categoria_transaccion(trans_id, cat_id)
        trans = db_manager.obtener_transaccion(trans_id)
        self.assertEqual(trans["categoria_id"], cat_id)

    def test_eliminar_transaccion(self):
        trans_id = db_manager.insertar_transaccion(
            comercio="A eliminar",
            fecha="2025-06-01",
            total=50.00,
        )
        db_manager.eliminar_transaccion(trans_id)
        trans = db_manager.obtener_transaccion(trans_id)
        self.assertIsNone(trans)

    def test_calcular_resumen_mensual(self):
        db_manager.insertar_transaccion(comercio="A", fecha="2025-06-01", total=100)
        db_manager.insertar_transaccion(comercio="B", fecha="2025-06-15", total=200)
        resumen = db_manager.calcular_resumen_mensual(2025, 6)
        self.assertEqual(resumen["total_transacciones"], 2)
        self.assertEqual(resumen["gasto_total"], 300.0)
        self.assertEqual(resumen["promedio_por_transaccion"], 150.0)

    def test_calcular_gastos_mensuales_por_categoria(self):
        trans_id = db_manager.insertar_transaccion(comercio="A", fecha="2025-06-01", total=150)
        categorias = db_manager.listar_categorias()
        db_manager.actualizar_categoria_transaccion(trans_id, categorias[0]["id"])
        gastos = db_manager.calcular_gastos_mensuales(2025, 6)
        total_gastado = next(c["total_gastado"] for c in gastos if c["id"] == categorias[0]["id"])
        self.assertEqual(total_gastado, 150.0)

    def test_listar_categorias(self):
        categorias = db_manager.listar_categorias()
        self.assertGreater(len(categorias), 0)
        self.assertIn("nombre", categorias[0])


if __name__ == "__main__":
    unittest.main()
