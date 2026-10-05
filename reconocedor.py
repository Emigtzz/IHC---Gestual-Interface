"""
reconocedor.py
Capa de captura y reconocimiento de gestos.

Flujo por cada frame:
  cámara -> espejo -> MediaPipe (21 landmarks) -> posición de la palma
  -> suavizado -> clasificación en 4 direcciones -> estabilizador -> comando

Gesto definido: posición de la palma respecto a un centro neutral.
  Palma arriba / abajo / izquierda / derecha del centro -> ese comando
  Palma dentro de la zona muerta, o sin mano visible    -> QUIETO
"""
from collections import Counter, deque

import cv2
import mediapipe as mp

from comandos import ABAJO, ARRIBA, DERECHA, IZQUIERDA, QUIETO


class Reconocedor:
    def __init__(
        self,
        indice_camara=0,
        zona_muerta=0.12,   # tamaño de la zona neutral (fracción del frame)
        alfa=0.5,           # suavizado de posición: 1 = sin suavizar, menor = más suave
        ventana=5,          # cuántos comandos recientes se consideran
        votos_min=3,        # cuántos deben coincidir para aceptar un cambio
    ):
        self.cap = cv2.VideoCapture(indice_camara)
        self.zona_muerta = zona_muerta
        self.alfa = alfa
        self.votos_min = votos_min

        self.centro = (0.5, 0.5)       # centro neutral (se puede calibrar)
        self._palma_suave = None       # última posición suavizada (x, y)
        self._historial = deque(maxlen=ventana)
        self._comando_estable = QUIETO

        self._mp_hands = mp.solutions.hands
        self._dibujo = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )

    # ------------------------------------------------------------------
    def camara_disponible(self):
        return self.cap.isOpened()

    def calibrar(self):
        """Fija el centro neutral donde está la palma ahora. False si no hay mano."""
        if self._palma_suave is None:
            return False
        self.centro = self._palma_suave
        return True

    # ------------------------------------------------------------------
    def _clasificar(self, x, y):
        """Convierte una posición (0-1) en un comando crudo (sin estabilizar)."""
        dx = x - self.centro[0]
        dy = y - self.centro[1]

        # Dentro de la zona muerta: no hay comando
        if abs(dx) < self.zona_muerta and abs(dy) < self.zona_muerta:
            return QUIETO

        # Fuera: gana el eje con mayor desplazamiento (solo 4 direcciones cardinales)
        if abs(dx) > abs(dy):
            return DERECHA if dx > 0 else IZQUIERDA
        return ABAJO if dy > 0 else ARRIBA

    def _estabilizar(self, crudo):
        """
        Votación por mayoría sobre los últimos frames. Un cambio de comando solo
        se acepta si aparece al menos `votos_min` veces: elimina el parpadeo.
        """
        self._historial.append(crudo)
        candidato, votos = Counter(self._historial).most_common(1)[0]
        if votos >= self.votos_min:
            self._comando_estable = candidato
        return self._comando_estable

    # ------------------------------------------------------------------
    def procesar(self):
        """
        Lee un frame y devuelve (comando, frame_anotado).
        Si la cámara falla devuelve (QUIETO, None).
        """
        ok, frame = self.cap.read()
        if not ok:
            return QUIETO, None

        frame = cv2.flip(frame, 1)  # espejo: mapeo natural izquierda-derecha
        alto, ancho, _ = frame.shape

        # MediaPipe espera RGB; OpenCV entrega BGR
        resultado = self._hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if resultado.multi_hand_landmarks:
            mano = resultado.multi_hand_landmarks[0]
            self._dibujo.draw_landmarks(frame, mano, self._mp_hands.HAND_CONNECTIONS)

            # Landmark 9 = base del dedo medio, nuestra "palma" (punto estable)
            lm = mano.landmark[9]
            if self._palma_suave is None:
                self._palma_suave = (lm.x, lm.y)
            else:
                # Media móvil exponencial: reduce el temblor de la detección
                px, py = self._palma_suave
                self._palma_suave = (
                    self.alfa * lm.x + (1 - self.alfa) * px,
                    self.alfa * lm.y + (1 - self.alfa) * py,
                )

            crudo = self._clasificar(*self._palma_suave)
            comando = self._estabilizar(crudo)

            cv2.circle(
                frame,
                (int(self._palma_suave[0] * ancho), int(self._palma_suave[1] * alto)),
                10, (0, 255, 0), -1,
            )
        else:
            # Sin mano: se detiene de inmediato (medida de seguridad)
            self._palma_suave = None
            self._historial.clear()
            self._comando_estable = QUIETO
            comando = QUIETO

        self._dibujar_zona_muerta(frame, ancho, alto)
        return comando, frame

    def _dibujar_zona_muerta(self, frame, ancho, alto):
        cx, cy = self.centro
        zm = self.zona_muerta
        p1 = (int((cx - zm) * ancho), int((cy - zm) * alto))
        p2 = (int((cx + zm) * ancho), int((cy + zm) * alto))
        cv2.rectangle(frame, p1, p2, (255, 200, 0), 2)

    # ------------------------------------------------------------------
    def cerrar(self):
        self._hands.close()
        self.cap.release()
