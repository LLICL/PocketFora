import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pocketfora.db")


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar():
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = conectar()
    conn.executescript(schema)
    conn.commit()
    conn.close()


def insertar_transaccion(comercio, fecha, total, detalle=None, tipo_documento=None,
                          serie_numero=None, ruc=None, categoria_id=None, qr_raw=None, moneda="PEN"):
    conn = conectar()
    cursor = conn.execute("""
        INSERT INTO transacciones (comercio, fecha, total, moneda, detalle,
                                   tipo_documento, serie_numero, ruc, categoria_id, qr_raw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (comercio, fecha, total, moneda, detalle, tipo_documento, serie_numero, ruc, categoria_id, qr_raw))
    trans_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trans_id


def insertar_producto(transaccion_id, descripcion, cantidad=1, precio_unitario=0, subtotal=0):
    conn = conectar()
    conn.execute("""
        INSERT INTO productos (transaccion_id, descripcion, cantidad, precio_unitario, subtotal)
        VALUES (?, ?, ?, ?, ?)
    """, (transaccion_id, descripcion, cantidad, precio_unitario, subtotal))
    conn.commit()
    conn.close()


def listar_transacciones(limite=50, offset=0):
    conn = conectar()
    rows = conn.execute("""
        SELECT t.*, c.nombre as categoria_nombre, c.icono as categoria_icono
        FROM transacciones t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        ORDER BY t.fecha DESC, t.id DESC
        LIMIT ? OFFSET ?
    """, (limite, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_transaccion(trans_id):
    conn = conectar()
    row = conn.execute("""
        SELECT t.*, c.nombre as categoria_nombre, c.icono as categoria_icono
        FROM transacciones t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.id = ?
    """, (trans_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def obtener_productos(transaccion_id):
    conn = conectar()
    rows = conn.execute("""
        SELECT * FROM productos WHERE transaccion_id = ?
    """, (transaccion_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_categorias():
    conn = conectar()
    rows = conn.execute("SELECT * FROM categorias ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def actualizar_categoria_transaccion(trans_id, categoria_id):
    conn = conectar()
    conn.execute("UPDATE transacciones SET categoria_id = ? WHERE id = ?", (categoria_id, trans_id))
    conn.commit()
    conn.close()


def eliminar_transaccion(trans_id):
    conn = conectar()
    conn.execute("DELETE FROM transacciones WHERE id = ?", (trans_id,))
    conn.commit()
    conn.close()


def calcular_gastos_mensuales(anio, mes):
    conn = conectar()
    fecha_inicio = f"{anio:04d}-{mes:02d}-01"
    if mes == 12:
        fecha_fin = f"{anio + 1:04d}-01-01"
    else:
        fecha_fin = f"{anio:04d}-{mes + 1:02d}-01"
    rows = conn.execute("""
        SELECT c.id, c.nombre, c.icono, COALESCE(SUM(t.total), 0) as total_gastado,
               COUNT(t.id) as cantidad
        FROM categorias c
        LEFT JOIN transacciones t ON t.categoria_id = c.id
            AND t.fecha >= ? AND t.fecha < ?
        GROUP BY c.id
        ORDER BY total_gastado DESC
    """, (fecha_inicio, fecha_fin)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def calcular_resumen_mensual(anio, mes):
    conn = conectar()
    fecha_inicio = f"{anio:04d}-{mes:02d}-01"
    if mes == 12:
        fecha_fin = f"{anio + 1:04d}-01-01"
    else:
        fecha_fin = f"{anio:04d}-{mes + 1:02d}-01"
    row = conn.execute("""
        SELECT COUNT(*) as total_transacciones,
               COALESCE(SUM(total), 0) as gasto_total,
               COALESCE(AVG(total), 0) as promedio_por_transaccion
        FROM transacciones
        WHERE fecha >= ? AND fecha < ?
    """, (fecha_inicio, fecha_fin)).fetchone()
    conn.close()
    return dict(row) if row else {"total_transacciones": 0, "gasto_total": 0, "promedio_por_transaccion": 0}
