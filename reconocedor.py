"""
reconocedor.py
Capa de captura y reconocimiento: posición de la palma -> comando de dirección.

Flujo por cada frame de la cámara:
  cámara -> espejo -> MediaPipe -> posición de un punto -> suavizado
  -> clasificación en 4 direcciones -> estabilizador -> comando

Hay dos fuentes de entrada intercambiables; solo la activa ejecuta su modelo (ahorra CPU):
  MANO   (MediaPipe Hands, landmark 9 = palma)       zona muerta 0.12
  CABEZA (MediaPipe Face Detection, punta de la nariz) zona muerta 0.05
La cabeza se mueve mucho menos que una mano, por eso su zona neutral es más pequeña. Ambas pasan
exactamente por la misma lógica (suavizado, zona muerta, 4 direcciones, estabilizador).

Gesto definido: posición de la palma respecto a un centro neutral.
  Palma arriba / abajo / izquierda / derecha del centro -> ese comando
  Palma dentro de la zona muerta, o sin mano visible    -> QUIETO

Todo esto corre en un HILO propio. Leer la cámara y ejecutar MediaPipe tarda decenas de milisegundos
por frame; si ocurriera dentro del bucle del juego, los FPS del juego serían los de la cámara (y se
verían afectados por poca luz o por la CPU). Con el hilo, el juego dibuja a 60 fps y simplemente usa
el último comando disponible.
"""
import threading
import time
from collections import Counter, deque

import cv2
import mediapipe as mp

from comandos import ABAJO, ARRIBA, DERECHA, IZQUIERDA, QUIETO

# Si el último resultado es más viejo que esto (cámara congelada, hilo caído), el comando pasa a
# QUIETO: es preferible que el personaje se detenga a que siga caminando con un dato viejo.
CADUCIDAD_S = 0.5

MANO, CABEZA = "mano", "cabeza"
FUENTES = (MANO, CABEZA)
ZONA_MUERTA = {MANO: 0.12, CABEZA: 0.05}   # fracción del frame; la cabeza se desplaza menos


class Reconocedor:
    def __init__(
        self,
        indice_camara=0,
        fuente=MANO,        # MANO o CABEZA
        alfa=0.5,           # suavizado de posición: 1 = sin suavizar, menor = más suave
        ventana=5,          # cuántos comandos recientes se consideran
        votos_min=3,        # cuántos deben coincidir para aceptar un cambio
    ):
        self.cap = cv2.VideoCapture(indice_camara)
        self._configurar_camara()
        self.alfa = alfa
        self.votos_min = votos_min

        self.fuente = fuente
        self.centros = {MANO: (0.5, 0.5), CABEZA: (0.5, 0.5)}   # centro neutral por fuente (calibrable)
        self._autocentrar = fuente == CABEZA   # la cabeza se centra sola en la primera detección
        self.mostrar_video = False     # el hilo solo dibuja sobre el frame si alguien lo va a ver
        self._palma_suave = None       # última posición suavizada (x, y)
        self._historial = deque(maxlen=ventana)
        self._comando_estable = QUIETO

        # Estado compartido con el bucle del juego (siempre bajo candado)
        self._lock = threading.Lock()
        self._comando = QUIETO
        self._frame = None
        self._t_resultado = float("-inf")   # instante del último resultado (para detectar datos viejos)
        self._fps_camara = 0.0
        self._ms_ia = 0.0
        self._error = None
        self._activo = False
        self._hilo = None

        self._mp_hands = mp.solutions.hands
        self._mp_cara = mp.solutions.face_detection
        self._dibujo = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            max_num_hands=1,
            model_complexity=0,         # modelo ligero: sobra para ubicar la palma y es bastante más rápido
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._cara = self._mp_cara.FaceDetection(
            model_selection=0,          # modelo de corto alcance (rostro a < 2 m): el más ligero
            min_detection_confidence=0.5,
        )

    def _configurar_camara(self):
        """
        Pide a la cámara una configuración que no limite los FPS. Es una petición: algunas cámaras
        o sistemas la ignoran sin avisar. Muchas webcams entregan video sin comprimir (YUYV) a solo
        15 fps; MJPG permite 30 fps en 640x480.
        """
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # sin cola de frames viejos = menos retraso

    @property
    def centro(self):
        return self.centros[self.fuente]

    @property
    def zona_muerta(self):
        return ZONA_MUERTA[self.fuente]

    def cambiar_fuente(self):
        """Alterna MANO <-> CABEZA. Reinicia el filtrado para no arrastrar datos de la otra fuente."""
        with self._lock:
            self.fuente = CABEZA if self.fuente == MANO else MANO
            self._palma_suave = None
            self._historial.clear()
            self._comando_estable = QUIETO
            self._comando = QUIETO
            self._autocentrar = self.fuente == CABEZA
        return self.fuente

    # ------------------------------------------------------------------
    # Control del hilo
    def camara_disponible(self):
        return self.cap.isOpened()

    def iniciar(self):
        """Arranca el hilo de captura y reconocimiento."""
        if self._hilo is None:
            self._activo = True
            self._hilo = threading.Thread(target=self._bucle, daemon=True)
            self._hilo.start()

    def _bucle(self):
        instantes = deque(maxlen=30)   # llegada de los últimos frames, para medir los FPS de la cámara
        try:
            while self._activo:
                ok, frame = self.cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                t0 = time.perf_counter()
                comando, anotado = self._procesar_frame(frame)
                ms = (time.perf_counter() - t0) * 1000
                instantes.append(t0)
                with self._lock:
                    self._comando, self._frame = comando, anotado
                    self._t_resultado = time.perf_counter()
                    self._ms_ia = ms if self._ms_ia == 0 else 0.9 * self._ms_ia + 0.1 * ms
                    if len(instantes) > 1:
                        self._fps_camara = (len(instantes) - 1) / (instantes[-1] - instantes[0])
        except Exception as e:   # un fallo en el hilo no debe dejar al personaje caminando solo
            with self._lock:
                self._error = f"{type(e).__name__}: {e}"
                self._comando = QUIETO

    def obtener(self):
        """
        Último (comando, frame). No bloquea. El frame es None salvo que `mostrar_video` sea True.
        Si el resultado está caducado (cámara congelada o hilo caído), el comando es QUIETO.
        """
        with self._lock:
            fresco = time.perf_counter() - self._t_resultado < CADUCIDAD_S
            return (self._comando if fresco else QUIETO), self._frame

    def estadisticas(self):
        """FPS que entrega la cámara y ms que tarda MediaPipe por frame (para diagnosticar lentitud)."""
        with self._lock:
            fresco = time.perf_counter() - self._t_resultado < CADUCIDAD_S
            return {
                "fps_camara": self._fps_camara if fresco else 0.0,
                "ms_ia": self._ms_ia,
                "error": self._error,
            }

    def calibrar(self):
        """Fija el centro neutral donde está el punto seguido ahora. False si no se detecta nada."""
        with self._lock:
            if self._palma_suave is None:
                return False
            self.centros[self.fuente] = self._palma_suave
            return True

    def info(self):
        """Estado para dibujar el indicador (la vista no necesita saber cómo se calcula)."""
        with self._lock:
            fresco = time.perf_counter() - self._t_resultado < CADUCIDAD_S
            return {
                "fuente": self.fuente,
                "punto": self._palma_suave if fresco else None,   # sin datos recientes = sin detección
                "centro": self.centro,
                "zona_muerta": self.zona_muerta,
            }

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
    def _buscar_punto(self, fuente, rgb):
        """
        Ejecuta el modelo de la fuente activa. Devuelve (x, y) normalizado (0-1) o None, más lo
        necesario para dibujar (solo la mano trae landmarks que dibujar).
        """
        if fuente == MANO:
            res = self._hands.process(rgb)
            if res.multi_hand_landmarks:
                mano = res.multi_hand_landmarks[0]
                lm = mano.landmark[9]          # base del dedo medio: nuestra "palma" (punto estable)
                return (lm.x, lm.y), mano
            return None, None
        res = self._cara.process(rgb)
        if res.detections:
            # Se toma la primera detección (la de mayor confianza) y su punta de la nariz
            nariz = res.detections[0].location_data.relative_keypoints[self._mp_cara.FaceKeyPoint.NOSE_TIP]
            return (nariz.x, nariz.y), None
        return None, None

    def _procesar_frame(self, frame):
        """Procesa un frame de la cámara y devuelve (comando, frame_anotado o None)."""
        frame = cv2.flip(frame, 1)  # espejo: mapeo natural izquierda-derecha
        alto, ancho, _ = frame.shape
        dibujar = self.mostrar_video
        fuente = self.fuente        # se fija al inicio: el modelo y el filtrado deben ser de la misma fuente

        # MediaPipe espera RGB; OpenCV entrega BGR. El modelo es lo lento: va fuera del candado.
        punto, mano = self._buscar_punto(fuente, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        with self._lock:
            if fuente != self.fuente:
                # Se cambió de fuente mientras procesábamos: este resultado ya no sirve
                return QUIETO, None
            if punto is not None:
                if self._palma_suave is None:
                    self._palma_suave = punto
                    if self._autocentrar:
                        # La cabeza no tiene "posición cómoda" universal: el centro es donde estás al empezar
                        self.centros[fuente] = punto
                        self._autocentrar = False
                else:
                    # Media móvil exponencial: reduce el temblor de la detección
                    px, py = self._palma_suave
                    self._palma_suave = (
                        self.alfa * punto[0] + (1 - self.alfa) * px,
                        self.alfa * punto[1] + (1 - self.alfa) * py,
                    )
                comando = self._estabilizar(self._clasificar(*self._palma_suave))
                suave = self._palma_suave
            else:
                # Sin detección: se detiene de inmediato (medida de seguridad)
                self._palma_suave = None
                self._historial.clear()
                self._comando_estable = QUIETO
                comando, suave = QUIETO, None

        if not dibujar:
            return comando, None
        if mano is not None:
            self._dibujo.draw_landmarks(frame, mano, self._mp_hands.HAND_CONNECTIONS)
        if suave is not None:
            cv2.circle(frame, (int(suave[0] * ancho), int(suave[1] * alto)), 10, (0, 255, 0), -1)
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
        self._activo = False
        if self._hilo is not None:
            self._hilo.join(timeout=1.0)   # primero detener el hilo, luego liberar lo que usa
        self._hands.close()
        self._cara.close()
        self.cap.release()
