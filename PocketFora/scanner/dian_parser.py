import re
import defusedxml.ElementTree as ET


NAMESPACES = {
    "fe": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

TIPO_DOC_DIAN = {
    "01": "Factura Electrónica",
    "02": "Factura de Venta",
    "03": "Boleta de Venta",
    "04": "Liquidación de Compra",
    "05": "Nota de Crédito",
    "06": "Nota de Débito",
    "07": "Nota de Ajuste",
}

CUFE_PATTERN = re.compile(
    r"catalogo-vpfe\.dian\.gov\.co.*document(?:key)?=([a-f0-9]+)",
    re.IGNORECASE,
)


class DianParser:
    def parsear_xml(self, ruta=None, xml_string=None):
        if ruta:
            tree = ET.parse(ruta)
            root = tree.getroot()
        elif xml_string:
            root = ET.fromstring(xml_string)
        else:
            raise ValueError("Debe proporcionar ruta o xml_string")

        ns = NAMESPACES

        numero = root.find(".//cbc:ID", ns)
        numero_factura = numero.text if numero is not None else ""

        cufe = root.find(".//cbc:UUID", ns)
        cufe_text = cufe.text if cufe is not None else ""

        fecha = root.find(".//cbc:IssueDate", ns)
        fecha_text = fecha.text if fecha is not None else ""

        tipo = root.find(".//cbc:InvoiceTypeCode", ns)
        tipo_codigo = tipo.text if tipo is not None else ""
        tipo_doc = TIPO_DOC_DIAN.get(tipo_codigo, tipo_codigo)

        moneda = root.find(".//cbc:DocumentCurrencyCode", ns)
        moneda_text = moneda.text if moneda is not None else "COP"

        emisor_nombre = root.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", ns
        )
        emisor_nit = root.find(
            ".//cac:AccountingSupplierParty/cac:Party/"
            "cac:PartyLegalEntity/cbc:CompanyID", ns
        )

        cliente_nombre = root.find(
            ".//cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name", ns
        )

        total_pagar = root.find(".//cac:LegalMonetaryTotal/cbc:PayableAmount", ns)

        productos = []
        lineas = root.findall(".//cac:InvoiceLine", ns)
        for linea in lineas:
            desc = linea.find("cac:Item/cbc:Description", ns)
            qty = linea.find("cbc:InvoicedQuantity", ns)
            precio = linea.find("cac:Price/cbc:PriceAmount", ns)
            total_linea = linea.find("cbc:LineExtensionAmount", ns)
            productos.append({
                "descripcion": desc.text if desc is not None else "",
                "cantidad": float(qty.text) if qty is not None and qty.text else 1,
                "precio_unitario": float(precio.text) if precio is not None and precio.text else 0,
                "subtotal": float(total_linea.text) if total_linea is not None and total_linea.text else 0,
            })

        return {
            "numero_factura": numero_factura,
            "cufe": cufe_text,
            "fecha": fecha_text,
            "tipo_documento": tipo_doc,
            "moneda": moneda_text,
            "comercio": emisor_nombre.text if emisor_nombre is not None else "",
            "nit_emisor": emisor_nit.text if emisor_nit is not None else "",
            "cliente": cliente_nombre.text if cliente_nombre is not None else "",
            "total": float(total_pagar.text) if total_pagar is not None and total_pagar.text else 0.0,
            "productos": productos,
        }

    def extraer_cufe_desde_url(self, texto):
        m = CUFE_PATTERN.search(texto)
        if m:
            return m.group(1)
        return None

    def parsear_qr(self, texto_qr):
        resultado = {
            "cufe": None,
            "url": None,
            "es_dian": False,
        }
        if not texto_qr:
            return resultado
        cufe = self.extraer_cufe_desde_url(texto_qr)
        if cufe:
            resultado["cufe"] = cufe
            resultado["url"] = texto_qr
            resultado["es_dian"] = True
        return resultado
