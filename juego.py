"""
juego.py
Capa del juego: un personaje que se mueve en 4 direcciones y mira hacia donde va.
No sabe nada de cámaras ni de MediaPipe: solo recibe comandos de texto.

Sprites: busca estos archivos en la carpeta assets/ (cualquier tamaño, de preferencia PNG
con fondo transparente):
    assets/arriba.png   assets/abajo.png   assets/izquierda.png   assets/derecha.png
Si alguno no existe, se dibuja un personaje de respaldo para esa dirección.
"""
import os

import pygame

from comandos import ABAJO, ARRIBA, DERECHA, IZQUIERDA, QUIETO, VECTORES

CARPETA_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
DIRECCIONES = (ARRIBA, ABAJO, IZQUIERDA, DERECHA)


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
            sprites[d] = pygame.transform.smoothscale(imagen, (tam, tam))
        else:
            sprites[d] = _sprite_respaldo(d, tam)
    return sprites


class Juego:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto
        self.tam = 110           # tamaño del personaje (px)
        self.velocidad = 420     # píxeles por segundo
        self.x = ancho / 2
        self.y = alto / 2
        self.comando = QUIETO
        self.mirando = ABAJO     # última dirección: el personaje conserva su orientación al detenerse
        self.sprites = cargar_sprites(self.tam)  # requiere la ventana ya creada (convert_alpha)

    def actualizar(self, comando, dt):
        """Mueve al personaje según el comando. dt = segundos desde el último frame."""
        self.comando = comando
        if comando != QUIETO:
            self.mirando = comando

        vx, vy = VECTORES[comando]
        self.x += vx * self.velocidad * dt
        self.y += vy * self.velocidad * dt

        # Limita al personaje dentro de la pantalla
        mitad = self.tam / 2
        self.x = max(mitad, min(self.ancho - mitad, self.x))
        self.y = max(mitad, min(self.alto - mitad, self.y))

    def dibujar(self, pantalla):
        pantalla.fill((25, 28, 40))

        # Cuadrícula de fondo (da referencia visual del movimiento)
        for gx in range(0, self.ancho, 80):
            pygame.draw.line(pantalla, (40, 44, 60), (gx, 0), (gx, self.alto))
        for gy in range(0, self.alto, 80):
            pygame.draw.line(pantalla, (40, 44, 60), (0, gy), (self.ancho, gy))

        # Sombra y personaje con la imagen de la dirección actual
        pygame.draw.ellipse(
            pantalla, (15, 17, 25),
            (self.x - self.tam * 0.35, self.y + self.tam * 0.40, self.tam * 0.7, self.tam * 0.16),
        )
        sprite = self.sprites[self.mirando]
        pantalla.blit(sprite, sprite.get_rect(center=(int(self.x), int(self.y))))
