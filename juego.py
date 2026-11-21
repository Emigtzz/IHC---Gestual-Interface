"""
juego.py
Capa del juego: un personaje que recorre un laberinto en 4 direcciones y mira hacia donde va.
No sabe nada de cámaras ni de MediaPipe: solo recibe comandos de texto.

Sprites: busca estos archivos en la carpeta assets/ (cualquier tamaño, de preferencia PNG
con fondo transparente):
    assets/arriba.png   assets/abajo.png   assets/izquierda.png   assets/derecha.png
Si alguno no existe, se dibuja un personaje de respaldo para esa dirección.
"""
import os

import pygame

from comandos import ABAJO, ARRIBA, DERECHA, DIRECCIONES, IZQUIERDA, QUIETO, VECTORES
from laberinto import Laberinto

CARPETA_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _sprite_respaldo(direccion, tam):
    """Dibuja un personaje simple que mira hacia `direccion` (usado si falta la imagen)."""
    s = pygame.Surface((tam, tam), pygame.SRCALPHA)
    cuerpo = (80, 170, 235)
    contorno = (30, 60, 100)
    pelo = (60, 40, 30)
    piel = (255, 210, 170)

    # Cuerpo
    pygame.draw.rect(s, cuerpo, (tam * 0.18, tam * 0.45, tam * 0.64, tam * 0.50), border_radius=int(tam * 0.12))
    pygame.draw.rect(s, contorno, (tam * 0.18, tam * 0.45, tam * 0.64, tam * 0.50), 3, border_radius=int(tam * 0.12))

    # Cabeza
    centro = (tam // 2, int(tam * 0.30))
    radio = int(tam * 0.26)
    pygame.draw.circle(s, piel, centro, radio)

    if direccion == ARRIBA:
        # De espaldas: se ve el pelo, sin cara
        pygame.draw.circle(s, pelo, centro, radio)
    elif direccion == ABAJO:
        # De frente: dos ojos
        pygame.draw.circle(s, pelo, (centro[0], centro[1] - radio // 3), radio, draw_top_left=True, draw_top_right=True)
        for dx in (-radio // 2, radio // 2):
            pygame.draw.circle(s, (20, 20, 20), (centro[0] + dx, centro[1] + radio // 5), max(2, tam // 22))
    elif direccion == IZQUIERDA:
        pygame.draw.circle(s, pelo, (centro[0] + radio // 3, centro[1] - radio // 4), int(radio * 0.8))
        pygame.draw.circle(s, piel, (centro[0] - radio // 4, centro[1] + radio // 6), int(radio * 0.7))
        pygame.draw.circle(s, (20, 20, 20), (centro[0] - radio // 2, centro[1]), max(2, tam // 22))
    elif direccion == DERECHA:
        pygame.draw.circle(s, pelo, (centro[0] - radio // 3, centro[1] - radio // 4), int(radio * 0.8))
        pygame.draw.circle(s, piel, (centro[0] + radio // 4, centro[1] + radio // 6), int(radio * 0.7))
        pygame.draw.circle(s, (20, 20, 20), (centro[0] + radio // 2, centro[1]), max(2, tam // 22))

    pygame.draw.circle(s, contorno, centro, radio, 3)

    # Flecha pequeña bajo el personaje que indica hacia dónde mira
    c = (tam // 2, int(tam * 0.97))
    k = tam * 0.06
    puntos = {
        ARRIBA: [(c[0], c[1] - k * 2), (c[0] - k, c[1]), (c[0] + k, c[1])],
        ABAJO: [(c[0], c[1]), (c[0] - k, c[1] - k * 2), (c[0] + k, c[1] - k * 2)],
        IZQUIERDA: [(c[0] - k, c[1] - k), (c[0] + k, c[1] - k * 2), (c[0] + k, c[1])],
        DERECHA: [(c[0] + k, c[1] - k), (c[0] - k, c[1] - k * 2), (c[0] - k, c[1])],
    }[direccion]
    pygame.draw.polygon(s, (255, 220, 100), puntos)
    return s


def cargar_sprites(tam):
    """Devuelve {direccion: Surface}. Usa assets/<direccion>.png si existe."""
    sprites = {}
    for d in DIRECCIONES:
        ruta = os.path.join(CARPETA_ASSETS, f"{d.lower()}.png")
        if os.path.exists(ruta):
            imagen = pygame.image.load(ruta).convert_alpha()
            # scale (vecino más cercano) conserva los bordes nítidos del pixel art de 16x16
            sprites[d] = pygame.transform.scale(imagen, (tam, tam))
        else:
            sprites[d] = _sprite_respaldo(d, tam)
    return sprites


def _acercar(valor, objetivo, paso):
    """Mueve `valor` hacia `objetivo` como máximo `paso`, sin pasarse."""
    if abs(objetivo - valor) <= paso:
        return objetivo
    return valor + paso if objetivo > valor else valor - paso


class Juego:
    def __init__(self, ancho, alto, origen_laberinto=None):
        self.ancho = ancho
        self.alto = alto

        # El laberinto ocupa la parte izquierda; la derecha queda libre para el panel de la cámara
        if origen_laberinto is None:
            origen_laberinto = (110, (alto - 8 * 80) // 2)
        self.laberinto = Laberinto(origen_laberinto, celda=80, grosor=12)

        self.tam = 64            # tamaño del sprite (px): 16 x 4, escala entera para el pixel art
        self.caja = 21           # mitad del lado de la caja de colisión (px): 42 px en un pasillo libre de 68
        self.velocidad = 200     # píxeles por segundo (~2.5 celdas/s: da margen a la latencia del gesto)
        self.sprites = cargar_sprites(self.tam)  # requiere la ventana ya creada (convert_alpha)
        self._fuente = None
        self._velo = None        # fondo oscuro de la pantalla de victoria (se crea una sola vez)
        self.reiniciar()

    def reiniciar(self):
        """Devuelve al personaje a la entrada y pone el cronómetro en cero."""
        self.x, self.y = self.laberinto.centro_celda(self.laberinto.fila_entrada, 0)
        self.comando = QUIETO
        self.mirando = DERECHA   # última dirección: el personaje conserva su orientación al detenerse
        self.moviendo = False    # True si en el último frame cambió de posición
        self.tiempo = 0.0        # el cronómetro arranca con el primer movimiento
        self.en_marcha = False
        self.gano = False

    # ------------------------------------------------------------------
    def actualizar(self, comando, dt):
        """Mueve al personaje según el comando. dt = segundos desde el último frame."""
        self.comando = comando
        if self.gano:
            self.comando = QUIETO
            self.moviendo = False
            return

        # Evita "saltos" a través de las paredes si un frame tarda demasiado (p. ej. al arrastrar la ventana)
        dt = min(dt, 1 / 30)

        if comando in DIRECCIONES:
            self.mirando = comando
            self.en_marcha = True
        if self.en_marcha:
            self.tiempo += dt

        x0, y0 = self.x, self.y
        if comando in DIRECCIONES:
            paso = self.velocidad * dt
            self._alinear_en_carril(comando, paso)
            vx, vy = VECTORES[comando]
            self._mover(vx * paso, vy * paso)
        self.moviendo = (self.x, self.y) != (x0, y0)

        if self.laberinto.es_meta(self.x, self.y):
            self.gano = True
            self.moviendo = False

    def _alinear_en_carril(self, comando, paso):
        """
        Ayuda para girar: si en la celda actual se puede avanzar en `comando`, el personaje se va
        centrando en el pasillo (eje perpendicular). Así, una orden de giro dada un poco antes o
        después de la esquina no lo deja atorado contra el borde; con un gesto impreciso es esencial.
        """
        celda = self.laberinto.celda_en(self.x, self.y)
        if celda is None or not self.laberinto.abierto(*celda, comando):
            return
        cx, cy = self.laberinto.centro_celda(*celda)
        if comando in (IZQUIERDA, DERECHA):
            self.y = _acercar(self.y, cy, paso)
        else:
            self.x = _acercar(self.x, cx, paso)

    def _solapa(self, pared):
        h = self.caja
        return (self.x - h < pared.right and self.x + h > pared.left
                and self.y - h < pared.bottom and self.y + h > pared.top)

    def _mover(self, dx, dy):
        """Movimiento con colisión, un eje a la vez: al tocar una pared se desliza por ella."""
        h = self.caja
        if dx:
            self.x += dx
            for pared in self.laberinto.colisiones:
                if self._solapa(pared):
                    self.x = pared.left - h if dx > 0 else pared.right + h
        if dy:
            self.y += dy
            for pared in self.laberinto.colisiones:
                if self._solapa(pared):
                    self.y = pared.top - h if dy > 0 else pared.bottom + h

    # ------------------------------------------------------------------
    def dibujar(self, pantalla):
        pantalla.fill((25, 28, 40))
        self.laberinto.dibujar(pantalla)

        # Sombra y personaje con la imagen de la dirección actual
        pygame.draw.ellipse(
            pantalla, (15, 17, 25),
            (self.x - self.tam * 0.35, self.y + self.tam * 0.30, self.tam * 0.7, self.tam * 0.16),
        )
        sprite = self.sprites[self.mirando]
        pantalla.blit(sprite, sprite.get_rect(center=(int(self.x), int(self.y))))

        # Si el personaje no se está moviendo (mano en reposo o empujando una pared),
        # las flechas muestran hacia dónde se puede ir
        if not self.moviendo and not self.gano:
            self._dibujar_salidas(pantalla)

        if self.gano:
            self._dibujar_victoria(pantalla)

    def _dibujar_salidas(self, pantalla):
        """Flechas en las direcciones por las que se puede seguir: guían hacia dónde mover la mano."""
        celda = self.laberinto.celda_en(self.x, self.y)
        if celda is None:
            return
        latido = 2 * (pygame.time.get_ticks() // 350 % 2)   # parpadeo suave para llamar la atención
        d = 54  # distancia desde el centro del personaje, dentro del pasillo vecino
        for direccion in DIRECCIONES:
            if not self.laberinto.abierto(*celda, direccion):
                continue
            vx, vy = VECTORES[direccion]
            px, py = self.x + vx * d, self.y + vy * d
            k = 9 + latido
            punta = (px + vx * k, py + vy * k)
            base1 = (px - vx * k - vy * k, py - vy * k + vx * k)
            base2 = (px - vx * k + vy * k, py - vy * k - vx * k)
            pygame.draw.polygon(pantalla, (255, 200, 60), (punta, base1, base2))
            pygame.draw.polygon(pantalla, (90, 60, 0), (punta, base1, base2), 2)

    def _dibujar_victoria(self, pantalla):
        lab = self.laberinto
        if self._fuente is None:
            self._fuente = (pygame.font.SysFont(None, 64), pygame.font.SysFont(None, 34))
            self._velo = pygame.Surface((lab.ancho, lab.alto), pygame.SRCALPHA)
            self._velo.fill((0, 0, 0, 170))
        grande, normal = self._fuente
        pantalla.blit(self._velo, (lab.ox, lab.oy))
        centro_x = lab.ox + lab.ancho // 2
        centro_y = lab.oy + lab.alto // 2
        for texto, fuente, color, dy in (
            ("¡Llegaste a la meta!", grande, (255, 220, 100), -40),
            (f"Tiempo: {formato_tiempo(self.tiempo)}", normal, (255, 255, 255), 15),
            ("Presiona R para jugar de nuevo", normal, (170, 175, 195), 55),
        ):
            s = fuente.render(texto, True, color)
            pantalla.blit(s, s.get_rect(center=(centro_x, centro_y + dy)))


def formato_tiempo(segundos):
    """mm:ss.d"""
    minutos, resto = divmod(segundos, 60)
    return f"{int(minutos):02d}:{resto:04.1f}"
