from datetime import datetime
from database.db_manager import calcular_gastos_mensuales, calcular_resumen_mensual, listar_transacciones


class Reporter:
    def reporte_mensual(self, anio=None, mes=None):
        ahora = datetime.now()
        anio = anio or ahora.year
        mes = mes or ahora.month
        resumen = calcular_resumen_mensual(anio, mes)
        categorias = calcular_gastos_mensuales(anio, mes)
        transacciones = listar_transacciones(limite=100)
        transacciones_mes = [
            t for t in transacciones
            if t["fecha"].startswith(f"{anio:04d}-{mes:02d}")
        ]
        return {
            "anio": anio,
            "mes": mes,
            "resumen": resumen,
            "categorias": categorias,
            "transacciones": transacciones_mes,
        }

    @staticmethod
    def _formatear_total(valor):
        s = f"{valor:,.2f}".replace(",", ".")
        if s.endswith(".00"):
            s = s[:-3]
        return s

    def texto_reporte_mensual(self, anio=None, mes=None):
        datos = self.reporte_mensual(anio, mes)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
        r = datos["resumen"]
        lineas = []
        lineas.append(f"=== Reporte de {meses[datos['mes'] - 1]} {datos['anio']} ===")
        lineas.append(f"Total gastado: S/ {self._formatear_total(r['gasto_total'])}")
        lineas.append(f"Transacciones: {r['total_transacciones']}")
        lineas.append(f"Promedio: S/ {self._formatear_total(r['promedio_por_transaccion'])}")
        lineas.append("")
        lineas.append("--- Por categoría ---")
        for cat in datos["categorias"]:
            if cat["total_gastado"] > 0:
                pct = (cat["total_gastado"] / r["gasto_total"] * 100) if r["gasto_total"] > 0 else 0
                lineas.append(f"{cat['icono']} {cat['nombre']}: S/ {self._formatear_total(cat['total_gastado'])} ({pct:.1f}%) - {cat['cantidad']} transacciones")
        lineas.append("")
        lineas.append(f"--- Últimas transacciones ({len(datos['transacciones'])}) ---")
        for t in datos["transacciones"][:10]:
            icono = t.get("categoria_icono", "📁")
            lineas.append(f"[{t['fecha']}] {icono} {t['comercio']}: S/ {self._formatear_total(t['total'])}")
        return "\n".join(lineas)
