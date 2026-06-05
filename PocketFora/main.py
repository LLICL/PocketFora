#!/usr/bin/env python3
"""
PocketFora - Sistema inteligente de gestión de gastos personales
 mediante escaneo de códigos QR en facturas.

Autor: PocketFora Dev Team
Versión: 1.0.0
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import inicializar
from parser.invoice_parser import InvoiceParser
from analysis.reporter import Reporter


def modo_cli():
    inicializar()
    parser = InvoiceParser()
    reporter = Reporter()
    print("=== PocketFora - CLI ===")
    print("Comandos: parsear <texto>, reporte, salir")
    while True:
        try:
            entrada = input("\n> ").strip()
            if not entrada:
                continue
            if entrada.lower() == "salir":
                break
            if entrada.lower() == "reporte":
                print(reporter.texto_reporte_mensual())
                continue
            if entrada.lower().startswith("parsear "):
                texto = entrada[8:]
                datos = parser.parsear(texto)
                print(f"Comercio: {datos.comercio}")
                print(f"Fecha: {datos.fecha}")
                print(f"Total: S/ {datos.total:.2f}")
                print(f"RUC: {datos.ruc}")
                print(f"Tipo: {datos.tipo_documento}")
                print(f"Serie: {datos.serie_numero}")
                if datos.productos:
                    print("Productos:")
                    for p in datos.productos:
                        print(f"  - {p['descripcion']} x{p['cantidad']} @ S/ {p['precio_unitario']:.2f}")
                continue
            print("Comando no reconocido")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    print("¡Hasta luego!")


def main():
    if "--cli" in sys.argv:
        modo_cli()
        return
    try:
        from desktop_app import main as desktop_main
        desktop_main()
    except ImportError as e:
        print(f"No se pudo cargar la interfaz de escritorio: {e}")
        print("Usando modo CLI...")
        modo_cli()


if __name__ == "__main__":
    main()
