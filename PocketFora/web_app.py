import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from database.db_manager import (inicializar, insertar_transaccion, insertar_producto,
                                  listar_transacciones, listar_categorias,
                                  actualizar_categoria_transaccion, eliminar_transaccion,
                                  calcular_gastos_mensuales, calcular_resumen_mensual,
                                  obtener_transaccion)
from parser.invoice_parser import InvoiceParser

app = Flask(__name__)
parser = InvoiceParser()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/resumen")
def api_resumen():
    ahora = datetime.now()
    resumen = calcular_resumen_mensual(ahora.year, ahora.month)
    return jsonify(resumen)


@app.route("/api/transacciones")
def api_transacciones():
    trans = listar_transacciones(limite=100)
    return jsonify(trans)


@app.route("/api/categorias")
def api_categorias():
    cats = listar_categorias()
    return jsonify(cats)


@app.route("/api/parsear", methods=["POST"])
def api_parsear():
    data = request.get_json()
    texto = data.get("qr_text", "")
    if not texto:
        return jsonify({"error": "Texto QR vacío"}), 400
    datos = parser.parsear(texto)
    return jsonify(datos.to_dict())


@app.route("/api/guardar", methods=["POST"])
def api_guardar():
    data = request.get_json()
    trans_id = insertar_transaccion(
        comercio=data["comercio"],
        fecha=data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
        total=float(data["total"]),
        detalle=data.get("detalle", ""),
        tipo_documento=data.get("tipo_documento", ""),
        serie_numero=data.get("serie_numero", ""),
        ruc=data.get("ruc", ""),
        qr_raw=data.get("qr_raw", ""),
        moneda=data.get("moneda", "PEN"),
    )
    cat_id = data.get("categoria_id")
    if cat_id:
        actualizar_categoria_transaccion(trans_id, int(cat_id))
    return jsonify({"id": trans_id, "status": "ok"})


@app.route("/api/eliminar/<int:trans_id>", methods=["DELETE"])
def api_eliminar(trans_id):
    eliminar_transaccion(trans_id)
    return jsonify({"status": "ok"})


@app.route("/api/reporte")
def api_reporte():
    ahora = datetime.now()
    gastos = calcular_gastos_mensuales(ahora.year, ahora.month)
    resumen = calcular_resumen_mensual(ahora.year, ahora.month)
    return jsonify({"resumen": resumen, "categorias": gastos})


if __name__ == "__main__":
    inicializar()
    print("PocketFora Web abierto en http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
