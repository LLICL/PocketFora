import re
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs


TIPO_DOC_MAP = {
    "01": "Factura",
    "03": "Boleta",
    "07": "Nota de Crédito",
    "08": "Nota de Débito",
}


class InvoiceData:
    def __init__(self):
        self.comercio = ""
        self.fecha = ""
        self.total = 0.0
        self.moneda = "PEN"
        self.detalle = ""
        self.tipo_documento = ""
        self.serie_numero = ""
        self.ruc = ""
        self.productos = []

    def to_dict(self):
        return {
            "comercio": self.comercio,
            "fecha": self.fecha,
            "total": self.total,
            "moneda": self.moneda,
            "detalle": self.detalle,
            "tipo_documento": self.tipo_documento,
            "serie_numero": self.serie_numero,
            "ruc": self.ruc,
            "productos": self.productos,
        }


class InvoiceParser:
    DIAN_PATTERN = re.compile(r'catalogo-vpfe\.dian\.gov\.co.*document(?:key)?=([a-f0-9]+)', re.IGNORECASE)

    def parsear(self, texto_qr):
        resultado = InvoiceData()
        if not texto_qr or not texto_qr.strip():
            self._post_procesar(resultado)
            return resultado
        texto = texto_qr.strip()
        if texto.startswith("http") or texto.startswith("https"):
            if self._parsear_url(texto, resultado):
                self._post_procesar(resultado)
                return resultado
        if texto.startswith("{") or texto.startswith("["):
            self._parsear_json(texto, resultado)
        elif "|" in texto and ":" in texto:
            self._parsear_sunat(texto, resultado)
        elif "\n" in texto and ":" in texto:
            self._parsear_clave_valor(texto, resultado)
        else:
            self._parsear_texto_libre(texto, resultado)
        self._post_procesar(resultado)
        return resultado

    def _parsear_url(self, texto, resultado):
        m = self.DIAN_PATTERN.search(texto)
        if m:
            cufe = m.group(1)
            resultado.comercio = "DIAN - Factura Electrónica"
            resultado.tipo_documento = "Factura Electrónica Colombiana"
            resultado.detalle = f"CUFE: {cufe}"
            resultado.serie_numero = cufe[:20]
            resultado.total = 0.0
            resultado.moneda = "COP"
            return True
        return False

    def _parsear_json(self, texto, resultado):
        try:
            datos = json.loads(texto)
            if isinstance(datos, list):
                datos = datos[0] if datos else {}
            resultado.comercio = self._extraer_campo_json(datos, ["comercio", "razonSocial", "nombre", "business", "merchant", "emisor"])
            resultado.fecha = self._extraer_campo_json(datos, ["fecha", "fechaEmision", "date", "issueDate"])
            resultado.total = float(self._extraer_campo_json(datos, ["total", "importeTotal", "amount", "totalAmount"], "0"))
            resultado.moneda = self._extraer_campo_json(datos, ["moneda", "currency", "divisa"], "PEN")
            resultado.tipo_documento = self._extraer_campo_json(datos, ["tipoDocumento", "documentType", "tipo"])
            resultado.serie_numero = self._extraer_campo_json(datos, ["serieNumero", "seriesNumber", "serie"])
            resultado.ruc = self._extraer_campo_json(datos, ["ruc", "taxId", "numeroRUC"])
            resultado.detalle = self._extraer_campo_json(datos, ["detalle", "description", "concepto"])
            productos_raw = self._extraer_campo_json(datos, ["productos", "items", "detalle", "products"], None)
            if isinstance(productos_raw, list):
                for p in productos_raw:
                    if isinstance(p, dict):
                        resultado.productos.append({
                            "descripcion": p.get("descripcion", p.get("description", p.get("nombre", ""))),
                            "cantidad": float(p.get("cantidad", p.get("quantity", 1))),
                            "precio_unitario": float(p.get("precioUnitario", p.get("unitPrice", p.get("precio", 0)))),
                            "subtotal": float(p.get("subtotal", p.get("total", 0))),
                        })
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    def _parsear_sunat(self, texto, resultado):
        partes = texto.split("|")
        mapa = {}
        for parte in partes:
            if ":" in parte:
                clave, _, valor = parte.partition(":")
                mapa[clave.strip().lower()] = valor.strip()
        resultado.ruc = mapa.get("ruc", mapa.get("numeroruc", ""))
        tipo_raw = mapa.get("tipodocumento", mapa.get("tipo", ""))
        resultado.tipo_documento = TIPO_DOC_MAP.get(tipo_raw, tipo_raw)
        serie = mapa.get("serie", "")
        numero = mapa.get("numero", mapa.get("numerodocumento", ""))
        resultado.serie_numero = f"{serie}-{numero}" if serie and numero else (serie or numero)
        total_str = mapa.get("total", mapa.get("importetotal", "0"))
        resultado.total = self._parsear_numero(total_str)
        resultado.moneda = mapa.get("moneda", "PEN")
        fecha_str = mapa.get("fechaemision", mapa.get("fecha", ""))
        resultado.fecha = self._normalizar_fecha(fecha_str)
        resultado.detalle = mapa.get("detalle", mapa.get("concepto", ""))
        resultado.comercio = mapa.get("comercio", mapa.get("razonsocial", mapa.get("razon_social", "")))

    def _parsear_clave_valor(self, texto, resultado):
        mapa = {}
        lineas = texto.split("\n")
        for i, linea in enumerate(lineas):
            linea = linea.strip()
            if not linea:
                continue
            if ":" in linea and not linea.startswith("http"):
                clave, _, valor = linea.partition(":")
                mapa[clave.strip().lower()] = valor.strip()
            else:
                if i == 0 and not resultado.comercio:
                    resultado.comercio = linea[:60]
                if not resultado.fecha:
                    m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', linea)
                    if m:
                        resultado.fecha = self._normalizar_fecha(m.group(1))
        resultado.ruc = mapa.get("ruc", mapa.get("r.u.c.", ""))
        resultado.comercio = mapa.get("comercio", mapa.get("razón social", mapa.get("razon social", mapa.get("empresa", "")))) or resultado.comercio
        resultado.total = self._parsear_numero(mapa.get("total", mapa.get("importe total", mapa.get("precio", "0"))))
        resultado.moneda = mapa.get("moneda", "PEN")
        fecha_map = mapa.get("fecha", mapa.get("fecha de emisión", mapa.get("fecha emision", "")))
        if fecha_map:
            resultado.fecha = self._normalizar_fecha(fecha_map)
        resultado.detalle = mapa.get("detalle", mapa.get("descripción", mapa.get("concepto", mapa.get("glosa", ""))))
        resultado.tipo_documento = mapa.get("tipo", mapa.get("tipo documento", ""))

    def _parsear_texto_libre(self, texto, resultado):
        lineas = [l.strip() for l in texto.split("\n") if l.strip()]
        patrones_moneda = r'[\$S/\.]?\s*(\d+(?:[.,]\d{2})?)'
        for i, linea in enumerate(lineas):
            if linea.startswith("http"):
                continue
            m = re.search(r'\b(\d{11})\b', linea)
            if m and not resultado.ruc:
                resultado.ruc = m.group(1)
            if re.search(r'(total|importe|precio|monto|s/\.)', linea, re.IGNORECASE):
                m2 = re.search(patrones_moneda, linea)
                if m2:
                    resultado.total = self._parsear_numero(m2.group(1))
            m3 = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', linea)
            if m3 and not resultado.fecha:
                resultado.fecha = self._normalizar_fecha(m3.group(1))
            if i == 0 and not resultado.comercio:
                resultado.comercio = linea[:60]
        if not resultado.total:
            nums = [self._parsear_numero(l) for l in lineas
                    if not l.startswith("http") and self._parsear_numero(l) > 0]
            if nums:
                resultado.total = max(nums)
        resultado.detalle = " | ".join(lineas[:5])

    def _extraer_campo_json(self, datos, claves, default=""):
        for clave in claves:
            valor = datos.get(clave, datos.get(clave.upper(), datos.get(clave.lower())))
            if valor is not None and valor != "":
                return valor
        return default

    def _parsear_numero(self, valor):
        if isinstance(valor, (int, float)):
            return float(valor)
        if not valor:
            return 0.0
        valor = str(valor).strip()
        if re.search(r'\d{1,3}(?:,\d{3})+(?:\.\d+)', valor):
            valor = valor.replace(",", "")
        elif re.search(r'\d{1,3}(?:\.\d{3})+(?:,\d+)', valor):
            valor = valor.replace(".", "").replace(",", ".")
        else:
            valor = valor.replace(",", ".")
        numeros = re.findall(r'[\d.]+', valor)
        if numeros:
            try:
                return float(numeros[-1])
            except ValueError:
                return 0.0
        return 0.0

    def _normalizar_fecha(self, texto):
        if not texto:
            return ""
        try:
            for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y"]:
                try:
                    return datetime.strptime(texto.strip(), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        except Exception:
            pass
        return ""

    def _post_procesar(self, resultado):
        if not resultado.fecha:
            resultado.fecha = datetime.now().strftime("%Y-%m-%d")
        if not resultado.comercio:
            resultado.comercio = "Desconocido"
