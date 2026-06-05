import cv2
import numpy as np
from pyzbar.pyzbar import decode


class QRScanner:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.cap = None

    def abrir_camara(self):
        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara {self.camera_id}")
        return self.cap

    def cerrar_camara(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def escanear_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        codigos = decode(gray)
        resultados = []
        for codigo in codigos:
            datos = codigo.data.decode("utf-8")
            rect = codigo.rect
            poligono = codigo.polygon
            resultados.append({
                "datos": datos,
                "rect": rect,
                "poligono": [(p.x, p.y) for p in poligono]
            })
            self._dibujar_rectangulo(frame, codigo)
        return frame, resultados

    def escanear_archivo(self, ruta_imagen):
        img = cv2.imread(ruta_imagen)
        if img is None:
            raise FileNotFoundError(f"No se encontró la imagen: {ruta_imagen}")
        return self.escanear_frame(img)

    def _dibujar_rectangulo(self, frame, codigo):
        pts = np.array([(p.x, p.y) for p in codigo.polygon], np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
        x, y, w, h = codigo.rect
        cv2.putText(frame, codigo.data.decode("utf-8")[:30] + "...",
                    (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def capturar_y_escanear(self):
        if not self.cap:
            self.abrir_camara()
        ret, frame = self.cap.read()
        if not ret:
            return None, []
        return self.escanear_frame(frame)

    def __enter__(self):
        self.abrir_camara()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar_camara()
