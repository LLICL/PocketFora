import re
import threading
from datetime import datetime
from queue import Queue


class DianConsultor:
    def __init__(self):
        self._detener = False
        self._hilo = None
        self._extraer_event = threading.Event()
        self._cufe = ""
        self._texto_pegado = ""

    def detener(self):
        self._detener = True
        self._extraer_event.set()

    def extraer_ahora(self, texto_pegado=""):
        self._texto_pegado = texto_pegado
        self._extraer_event.set()

    def consultar(self, url_dian, cufe, queue):
        self._cufe = cufe
        self._extraer_event.clear()
        self._detener = False
        self._hilo = threading.Thread(
            target=self._ejecutar,
            args=(url_dian, cufe, queue),
            daemon=True,
        )
        self._hilo.start()

    def _normalizar_url(self, url):
        if not url:
            return url
        if url.startswith("http://"):
            url = "https://" + url[7:]
        return url

    def _ejecutar(self, url_dian, cufe, queue):
        try:
            url_dian = self._normalizar_url(url_dian)

            queue.put(("URL", url_dian))

            señal_ok = self._extraer_event.wait(timeout=300)

            if not señal_ok:
                queue.put(("ERROR", "Tiempo de espera agotado (5 min)"))
                return

            if self._detener:
                queue.put(("ERROR", "Consulta cancelada"))
                return

            texto = getattr(self, '_texto_pegado', "")
            if len(texto.strip()) < 50:
                queue.put(("ERROR", "Texto muy corto. Copia toda la página (Ctrl+A, Ctrl+C)."))
                return

            datos = self._extraer_desde_texto(texto, cufe)
            queue.put(("RESULTADO", datos))

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            queue.put(("ERROR", f"Error: {type(e).__name__}: {e}"))
            queue.put(("DEBUG_HTML", tb))

    @staticmethod
    def _parsear_numero_colombiano(texto):
        if not texto:
            return 0.0
        texto = texto.strip().replace("$", "").replace(" ", "").replace("COP", "").strip()
        if not texto:
            return 0.0
        if re.search(r'\d{1,3}\.\d{3}', texto):
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")
        elif re.search(r'\d{1,3},\d{3}', texto):
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            return 0.0

    @staticmethod
    def _normalizar_fecha(raw):
        if not raw:
            return ""
        raw = raw.strip()

        m = re.match(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', raw)
        if m:
            y, mes, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= d <= 31 and 1 <= mes <= 12:
                return f"{y:04d}-{mes:02d}-{d:02d}"

        m = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$', raw)
        if not m:
            return raw
        a, b, c = int(m.group(1)), int(m.group(2)), m.group(3)
        y = 2000 + int(c) if len(c) == 2 else int(c)

        if a > 12:
            d, mes, yy = a, b, y
        elif b > 12:
            d, mes, yy = b, a, y
        else:
            d, mes, yy = a, b, y

        if 1 <= d <= 31 and 1 <= mes <= 12:
            return f"{yy:04d}-{mes:02d}-{d:02d}"
        return raw

    def _extraer_desde_texto(self, texto, cufe):
        lineas = [l.strip() for l in texto.split("\n") if l.strip()]

        fecha = ""
        total = 0.0
        comercio = ""
        nit = ""
        numero = ""
        estado = ""

        for i, linea in enumerate(lineas):
            linea_l = linea.lower()

            if not comercio:
                for palabra in ["razón social:", "razon social:", "nombre:", "emisor:"]:
                    if palabra in linea_l:
                        partes = linea.split(":", 1)
                        if len(partes) > 1:
                            comercio = partes[1].strip()
                        break

            if not nit:
                for palabra in ["nit:", "identificación:", "identificacion:", "documento:"]:
                    if palabra in linea_l:
                        partes = linea.split(":", 1)
                        if len(partes) > 1:
                            candidato = partes[1].strip()
                            if any(c.isdigit() for c in candidato) and len(candidato) >= 5:
                                nit = candidato
                        break

            if not fecha:
                m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', linea)
                if m:
                    fecha = m.group(1)

            if not total:
                for etiqueta in ["total", "valor", "pagar", "payable"]:
                    if etiqueta in linea_l:
                        m = re.search(r'[\$\s]*([\d.,]+)', linea)
                        if m:
                            total = self._parsear_numero_colombiano(m.group(1))
                            if total:
                                break

            if not numero:
                for palabra in ["factura:", "número:", "numero:", "consecutivo:"]:
                    if palabra in linea_l:
                        partes = linea.split(":", 1)
                        if len(partes) > 1:
                            numero = partes[1].strip()
                        break

            if not estado:
                for palabra in ["estado:", "resultado:"]:
                    if palabra in linea_l:
                        partes = linea.split(":", 1)
                        if len(partes) > 1:
                            estado = partes[1].strip()
                        break

        if not comercio:
            for palabra in ["razón social", "razon social", "nombre del emisor"]:
                idx = texto.lower().find(palabra)
                if idx >= 0:
                    fragmento = texto[idx:idx+150]
                    for sep in ["\n", ".", "  "]:
                        partes = fragmento.split(":", 1)
                        if len(partes) > 1:
                            comercio = partes[1].split("\n")[0].strip()
                            break
                    if comercio:
                        break

        if not nit:
            for m in re.finditer(r'\b(\d{9,15})\b', texto):
                candidato = m.group(1)
                if len(candidato) >= 9:
                    nit = candidato
                    break

        if not total:
            for linea in reversed(lineas):
                nums = re.findall(r'[\d.,]+', linea)
                for n in reversed(nums):
                    val = self._parsear_numero_colombiano(n)
                    if val > 1000:
                        total = val
                        break
                if total:
                    break

        if fecha:
            fecha = self._normalizar_fecha(fecha)

        detalle = f"CUFE: {cufe}"
        if estado:
            detalle += f" | Estado: {estado}"

        return {
            "comercio": comercio or "DIAN - Factura Electrónica",
            "fecha": fecha or datetime.now().strftime("%Y-%m-%d"),
            "total": total,
            "moneda": "COP",
            "detalle": detalle,
            "tipo_documento": "Factura Electrónica",
            "serie_numero": numero or cufe[:20],
            "ruc": nit,
            "nit_emisor": nit,
            "productos": [],
            "cufe": cufe,
            "estado": estado,
        }
