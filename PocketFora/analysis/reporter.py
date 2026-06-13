from datetime import datetime
from database.db_manager import calcular_gastos_mensuales, calcular_resumen_mensual, listar_transacciones


MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]


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
        s = f"{valor:,.2f}"
        if s.endswith(".00"):
            s = s[:-3]
        return s

    def texto_reporte_mensual(self, anio=None, mes=None):
        datos = self.reporte_mensual(anio, mes)
        r = datos["resumen"]
        lineas = []
        lineas.append(f"=== Reporte de {MESES[datos['mes'] - 1]} {datos['anio']} ===")
        lineas.append(f"Total gastado: $ {self._formatear_total(r['gasto_total'])}")
        lineas.append(f"Transacciones: {r['total_transacciones']}")
        lineas.append(f"Promedio: $ {self._formatear_total(r['promedio_por_transaccion'])}")
        lineas.append("")
        lineas.append("--- Por categoría ---")
        for cat in datos["categorias"]:
            if cat["total_gastado"] > 0:
                pct = (cat["total_gastado"] / r["gasto_total"] * 100) if r["gasto_total"] > 0 else 0
                lineas.append(f"{cat['icono']} {cat['nombre']}: $ {self._formatear_total(cat['total_gastado'])} ({pct:.1f}%) - {cat['cantidad']} transacciones")
        lineas.append("")
        lineas.append(f"--- Últimas transacciones ({len(datos['transacciones'])}) ---")
        for t in datos["transacciones"][:10]:
            icono = t.get("categoria_icono", "\U0001f4c1")
            lineas.append(f"[{t['fecha']}] {icono} {t['comercio']}: $ {self._formatear_total(t['total'])}")
        return "\n".join(lineas)

    def html_reporte_mensual(self, anio=None, mes=None):
        datos = self.reporte_mensual(anio, mes)
        r = datos["resumen"]
        mes_nombre = MESES[datos["mes"] - 1]
        ahora = datetime.now()

        mes_prev = mes - 1 if mes > 1 else 12
        anio_prev = anio if mes > 1 else anio - 1
        prev = calcular_resumen_mensual(anio_prev, mes_prev)
        mes_prev_nombre = MESES[mes_prev - 1]

        total = r["gasto_total"]
        transacciones = r["total_transacciones"]
        promedio = r["promedio_por_transaccion"]
        total_fmt = self._formatear_total(total)
        promedio_fmt = self._formatear_total(promedio)

        total_prev = prev["gasto_total"]
        trans_prev = prev["total_transacciones"]
        prom_prev = prev["promedio_por_transaccion"]

        def diff_pct(curr, p):
            return ((curr - p) / p * 100) if p else 0

        def diff_class(val):
            return "diff-up" if val >= 0 else "diff-down"

        def badge_class(val, bad_up=True):
            up = val >= 0
            if (up and bad_up) or (not up and not bad_up):
                return "badge-up"
            return "badge-down"

        def badge_arrow(val):
            return "\u25b2" if val >= 0 else "\u25bc"

        total_diff = diff_pct(total, total_prev)
        trans_diff = diff_pct(transacciones, trans_prev)
        prom_diff = diff_pct(promedio, prom_prev)

        total_prev_fmt = self._formatear_total(total_prev)
        prom_prev_fmt = self._formatear_total(prom_prev)

        chart_labels = []
        chart_data = []
        chart_colors = []
        for i in range(5, -1, -1):
            m = mes - i
            a = anio
            while m < 1:
                m += 12
                a -= 1
            while m > 12:
                m -= 12
                a += 1
            chart_labels.append(f'"{MESES[m - 1][:3]}"')
            r_m = calcular_resumen_mensual(a, m)
            v = r_m["gasto_total"]
            chart_data.append(str(v))
            is_current = (i == 0)
            chart_colors.append('"#7F77DD"' if is_current else '"#CECBF6"')

        cat_rows = ""
        for cat in datos["categorias"]:
            if cat["total_gastado"] > 0:
                cat_rows += f"""
            <tr>
              <td><span class="cat-pill">{cat['icono']} {cat['nombre']}</span></td>
              <td class="tx-amount">${self._formatear_total(cat['total_gastado'])}</td>
              <td class="tx-date">{cat['cantidad']} trans.</td>
            </tr>"""

        tx_rows = ""
        for t in datos["transacciones"][:20]:
            icono = t.get("categoria_icono", "\U0001f4c1") or "\U0001f4c1"
            cat_name = t.get("categoria_nombre", "Otros") or "Otros"
            tx_rows += f"""
            <tr>
              <td class="tx-date">{t['fecha'][-5:]}</td>
              <td>{t['comercio']}</td>
              <td><span class="cat-pill">{icono} {cat_name}</span></td>
              <td class="tx-amount">${self._formatear_total(t['total'])}</td>
            </tr>"""

        chart_labels_str = ", ".join(chart_labels)
        chart_data_str = ", ".join(chart_data)
        chart_colors_str = ", ".join(chart_colors)

        es_mes_actual = (mes == ahora.month and anio == ahora.year)
        badge_text = "Mes actual" if es_mes_actual else "Histórico"
        fecha_gen = ahora.strftime("%d %b %Y").lower()

        html = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reporte de Gastos — {mes_nombre} {anio}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #F4F2FE;
    color: #1a1a2e;
    min-height: 100vh;
    padding: 2rem 1rem;
  }}
  .page {{ max-width: 860px; margin: 0 auto; }}
  .report-header {{
    background: #26215C;
    border-radius: 16px;
    padding: 2rem 2rem 1.75rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }}
  .report-header-left h1 {{ font-size: 22px; font-weight: 600; color: #fff; letter-spacing: -0.3px; margin-bottom: 4px; }}
  .report-header-left p {{ font-size: 13px; color: #AFA9EC; }}
  .header-badge {{
    background: #7F77DD; color: #EEEDFE; font-size: 12px; font-weight: 500;
    padding: 6px 14px; border-radius: 20px; white-space: nowrap; align-self: flex-start;
  }}
  .section-label {{
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    color: #7F77DD; margin-bottom: 10px; margin-top: 1.75rem;
  }}
  .metrics-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .metric-card {{
    background: #fff; border-radius: 14px; padding: 1.25rem 1.25rem 1rem;
    border: 1px solid #CECBF6;
  }}
  .metric-icon {{
    width: 34px; height: 34px; border-radius: 10px; background: #EEEDFE;
    display: flex; align-items: center; justify-content: center; margin-bottom: 12px;
  }}
  .metric-icon svg {{ width: 18px; height: 18px; stroke: #534AB7; fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }}
  .metric-label {{ font-size: 12px; color: #7F77DD; margin-bottom: 4px; }}
  .metric-value {{ font-size: 21px; font-weight: 600; color: #26215C; letter-spacing: -0.5px; }}
  .metric-sub {{ font-size: 11px; color: #AFA9EC; margin-top: 4px; }}
  .card {{ background: #fff; border-radius: 14px; border: 1px solid #CECBF6; overflow: hidden; }}
  .card-inner {{ padding: 1.25rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{
    text-align: left; padding: 10px 14px; color: #7F77DD; font-weight: 600;
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
    background: #EEEDFE; border-bottom: 1px solid #CECBF6;
  }}
  td {{ padding: 11px 14px; border-bottom: 1px solid #F0EFFE; color: #26215C; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  .row-label {{ font-weight: 500; color: #3C3489; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 3px; font-size: 11px;
    font-weight: 600; padding: 3px 9px; border-radius: 20px;
  }}
  .badge-up {{ background: #FCEBEB; color: #A32D2D; }}
  .badge-down {{ background: #EAF3DE; color: #3B6D11; }}
  .diff-up {{ color: #A32D2D; font-weight: 500; }}
  .diff-down {{ color: #3B6D11; font-weight: 500; }}
  .chart-wrap {{
    background: #fff; border-radius: 14px; border: 1px solid #CECBF6; padding: 1.25rem;
  }}
  .chart-legend {{
    display: flex; gap: 16px; margin-bottom: 14px; font-size: 12px; color: #7F77DD;
  }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; margin-right: 5px; vertical-align: middle; }}
  .chart-canvas-wrap {{ position: relative; width: 100%; height: 240px; }}
  .tx-table th {{ background: #26215C; color: #CECBF6; }}
  .tx-table td {{ font-size: 13px; }}
  .cat-pill {{
    display: inline-block; font-size: 11px; font-weight: 500; padding: 3px 10px;
    border-radius: 20px; background: #EEEDFE; color: #534AB7;
  }}
  .tx-amount {{ font-weight: 600; color: #3C3489; text-align: right; }}
  .tx-date {{ color: #7F77DD; font-size: 12px; }}
  .report-footer {{ text-align: center; font-size: 12px; color: #AFA9EC; padding: 1.5rem 0 0.5rem; }}
  @media (max-width: 600px) {{ .metrics-row {{ grid-template-columns: 1fr 1fr; }} }}
  @media (max-width: 420px) {{ .metrics-row {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="page">

  <div class="report-header">
    <div class="report-header-left">
      <h1>Reporte de gastos</h1>
      <p>{mes_nombre} {anio} &nbsp;\u00b7&nbsp; Generado el {fecha_gen}</p>
    </div>
    <span class="header-badge">{badge_text}</span>
  </div>

  <p class="section-label">Resumen del mes</p>
  <div class="metrics-row">
    <div class="metric-card">
      <div class="metric-icon">
        <svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/></svg>
      </div>
      <div class="metric-label">Total gastado</div>
      <div class="metric-value">${total_fmt}</div>
      <div class="metric-sub">{mes_nombre} {anio}</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon">
        <svg viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>
      </div>
      <div class="metric-label">Transacciones</div>
      <div class="metric-value">{transacciones}</div>
      <div class="metric-sub">operaciones realizadas</div>
    </div>
    <div class="metric-card">
      <div class="metric-icon">
        <svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="m7 16 4-4 4 4 4-4"/></svg>
      </div>
      <div class="metric-label">Promedio por transacción</div>
      <div class="metric-value">${promedio_fmt}</div>
      <div class="metric-sub">por operación</div>
    </div>
  </div>

  <p class="section-label">Comparativa con el mes anterior</p>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th style="width:30%">Indicador</th>
          <th>{mes_prev_nombre} {anio_prev}</th>
          <th>{mes_nombre} {anio}</th>
          <th style="text-align:center">Variación</th>
          <th style="text-align:right">Diferencia</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="row-label">Total gastado</td>
          <td>${total_prev_fmt}</td>
          <td><strong>${total_fmt}</strong></td>
          <td style="text-align:center"><span class="badge {badge_class(total_diff)}">{badge_arrow(total_diff)} {total_diff:.1f}%</span></td>
          <td class="tx-amount {diff_class(total_diff)}">{'+' if total_diff >= 0 else '-'}${self._formatear_total(abs(total - total_prev))}</td>
        </tr>
        <tr>
          <td class="row-label">Transacciones</td>
          <td>{trans_prev}</td>
          <td><strong>{transacciones}</strong></td>
          <td style="text-align:center"><span class="badge {badge_class(trans_diff, True)}">{badge_arrow(trans_diff)} {trans_diff:.1f}%</span></td>
          <td class="tx-amount {diff_class(trans_diff)}">{'+' if trans_diff >= 0 else ''}{transacciones - trans_prev} ops</td>
        </tr>
        <tr>
          <td class="row-label">Promedio por tx</td>
          <td>${prom_prev_fmt}</td>
          <td><strong>${promedio_fmt}</strong></td>
          <td style="text-align:center"><span class="badge {badge_class(prom_diff, True)}">{badge_arrow(prom_diff)} {prom_diff:.1f}%</span></td>
          <td class="tx-amount {diff_class(prom_diff)}">{'+' if prom_diff >= 0 else '-'}${self._formatear_total(abs(promedio - prom_prev))}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <p class="section-label">Histórico de gastos — últimos 6 meses</p>
  <div class="chart-wrap">
    <div class="chart-legend">
      <span><span class="legend-dot" style="background:#CECBF6; border:1px dashed #7F77DD;"></span>Meses anteriores</span>
      <span><span class="legend-dot" style="background:#7F77DD;"></span>Mes actual</span>
    </div>
    <div class="chart-canvas-wrap">
      <canvas id="histChart" aria-label="Gráfica de barras de gastos mensuales"></canvas>
    </div>
  </div>

  <p class="section-label">Gastos por categoría</p>
  <div class="card">
    <table>
      <thead><tr><th>Categoría</th><th style="text-align:right">Total</th><th>Detalle</th></tr></thead>
      <tbody>{cat_rows}</tbody>
    </table>
  </div>

  <p class="section-label">Registro de transacciones</p>
  <div class="card">
    <table class="tx-table">
      <thead><tr><th style="width:14%">Fecha</th><th style="width:36%">Descripción</th><th style="width:24%">Categoría</th><th style="width:16%; text-align:right">Total</th></tr></thead>
      <tbody>{tx_rows}</tbody>
    </table>
  </div>

  <div class="report-footer">Reporte generado automáticamente &nbsp;\u00b7&nbsp; PocketFora</div>
</div>

<script>
new Chart(document.getElementById('histChart'), {{
  type: 'bar',
  data: {{
    labels: [{chart_labels_str}],
    datasets: [{{
      label: 'Total gastado',
      data: [{chart_data_str}],
      backgroundColor: [{chart_colors_str}],
      borderColor: ['#AFA9EC','#AFA9EC','#AFA9EC','#AFA9EC','#AFA9EC','#534AB7'],
      borderWidth: 1.5,
      borderRadius: 8,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => ' $' + ctx.parsed.y.toLocaleString('es-CO')
        }}
      }}
    }},
    scales: {{
      x: {{
        grid: {{ display: false }},
        ticks: {{ color: '#7F77DD', font: {{ size: 12 }}, autoSkip: false }}
      }},
      y: {{
        grid: {{ color: 'rgba(127,119,221,0.1)' }},
        ticks: {{ color: '#AFA9EC', font: {{ size: 11 }}, callback: v => '$' + (v / 1000000).toFixed(1) + 'M' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>'''
        return html
