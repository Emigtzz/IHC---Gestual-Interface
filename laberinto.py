"""
laberinto.py
Geometría del laberinto: el mapa, las paredes (rectángulos de colisión) y su dibujo.
No sabe nada de cámaras, gestos ni del personaje: solo describe el escenario.

El mapa es la transcripción del laberinto de la imagen del proyecto (8 x 8 celdas).
Formato ASCII: las líneas pares dibujan las paredes horizontales ("---") y las impares
las verticales ("|"). Cada celda mide 4 caracteres de ancho:

    +---+---+        "+---+" = pared arriba / abajo de la celda
    |       |        "|"     = pared a la izquierda / derecha de la celda

Las dos aberturas del borde son la ENTRADA (izquierda, fila 4) y la SALIDA (derecha, fila 1).
"""
import pygame

from comandos import ABAJO, ARRIBA, DERECHA, IZQUIERDA

MAPA = [
    "+---+---+---+---+---+---+---+---+",
    "|           |           |        ",
    "+   +---+---+   +   +---+   +---+",
    "|               |   |       |   |",
    "+   +---+---+---+   +   +---+   +",
    "|       |           |   |       |",
    "+---+   +   +---+---+   +---+   +",
    "    |   |           |       |   |",
    "+   +   +---+---+   +---+   +   +",
    "|   |       |       |   |       |",
    "+   +   +---+   +   +   +---+   +",
    "|       |       |           |   |",
    "+---+---+   +---+   +---+---+   +",
    "|           |       |           |",
    "+   +---+---+---+---+   +---+---+",
    "|                               |",
    "+---+---+---+---+---+---+---+---+",
]

COLOR_SUELO = (157, 185, 225)   # azul de los pasillos, igual que la imagen original
COLOR_PARED = (0, 0, 0)
COLOR_ENTRADA = (70, 190, 110)
COLOR_TEXTO = (170, 175, 195)


def _parsear(mapa):
    """Convierte el mapa ASCII en dos matrices de booleanos: paredes horizontales y verticales."""
    ancho_linea = len(mapa[0])
    mapa = [linea.ljust(ancho_linea) for linea in mapa]  # los espacios finales pueden faltar
    filas = (len(mapa) - 1) // 2
    cols = (ancho_linea - 1) // 4
    # horiz[f][c]: hay pared en el borde SUPERIOR de la celda (f, c); f va de 0 a filas
    horiz = [[mapa[2 * f][4 * c + 1:4 * c + 4] == "---" for c in range(cols)]
             for f in range(filas + 1)]
    # vert[f][c]: hay pared en el borde IZQUIERDO de la celda (f, c); c va de 0 a cols
    vert = [[mapa[2 * f + 1][4 * c] == "|" for c in range(cols + 1)]
            for f in range(filas)]
    return filas, cols, horiz, vert


class Laberinto:
    def __init__(self, origen, celda=80, grosor=12):
        """
        origen: esquina superior izquierda del laberinto en pantalla (px).
        celda:  lado de cada celda (px). El pasillo libre mide celda - grosor.
        grosor: grosor de las paredes (px).
        """
        self.ox, self.oy = origen
        self.celda = celda
        self.grosor = grosor
        self.filas, self.cols, self._horiz, self._vert = _parsear(MAPA)
        self.ancho = self.cols * celda
        self.alto = self.filas * celda

        self.fila_entrada = next(f for f in range(self.filas) if not self._vert[f][0])
        self.fila_salida = next(f for f in range(self.filas) if not self._vert[f][self.cols])

        self.paredes = self._construir_paredes()
        # La entrada está abierta en el dibujo, pero se sella para que el personaje no salga por ahí
        self.sello_entrada = self._rect_vertical(0, self.fila_entrada)
        self.colisiones = self.paredes + [self.sello_entrada]

        self._fuente = None  # se crea al dibujar (requiere pygame.font inicializado)

    # ------------------------------------------------------------------
    # Construcción
    def _rect_horizontal(self, fila_linea, col):
        g = self.grosor
        x = self.ox + col * self.celda - g // 2
        y = self.oy + fila_linea * self.celda - g // 2
        return pygame.Rect(x, y, self.celda + g, g)

    def _rect_vertical(self, col_linea, fila):
        g = self.grosor
        x = self.ox + col_linea * self.celda - g // 2
        y = self.oy + fila * self.celda - g // 2
        return pygame.Rect(x, y, g, self.celda + g)

    def _construir_paredes(self):
        rects = []
        for f in range(self.filas + 1):
            for c in range(self.cols):
                if self._horiz[f][c]:
                    rects.append(self._rect_horizontal(f, c))
        for f in range(self.filas):
            for c in range(self.cols + 1):
                if self._vert[f][c]:
                    rects.append(self._rect_vertical(c, f))
        return rects

    # ------------------------------------------------------------------
    # Consultas
    def celda_en(self, x, y):
        """(fila, col) de la celda que contiene el punto (x, y), o None si está fuera."""
        col = int((x - self.ox) // self.celda)
        fila = int((y - self.oy) // self.celda)
        if 0 <= fila < self.filas and 0 <= col < self.cols:
            return fila, col
        return None

    def centro_celda(self, fila, col):
        return (self.ox + (col + 0.5) * self.celda, self.oy + (fila + 0.5) * self.celda)

    def abierto(self, fila, col, direccion):
        """True si no hay pared entre la celda (fila, col) y su vecina en esa dirección."""
        if direccion == IZQUIERDA and col == 0 and fila == self.fila_entrada:
            return False  # la entrada está dibujada abierta, pero sellada: no se puede salir por ahí
        if direccion == ARRIBA:
            return not self._horiz[fila][col]
        if direccion == ABAJO:
            return not self._horiz[fila + 1][col]
        if direccion == IZQUIERDA:
            return not self._vert[fila][col]
        if direccion == DERECHA:
            return not self._vert[fila][col + 1]
        return False

    def es_meta(self, x, y):
        """La meta se alcanza al cruzar el borde derecho por la salida."""
        salida = self.oy + self.fila_salida * self.celda
        return x >= self.ox + self.ancho and salida <= y <= salida + self.celda

    # ------------------------------------------------------------------
    # Dibujo
    def dibujar(self, pantalla):
        if self._fuente is None:
            self._fuente = pygame.font.SysFont(None, 26)

        pygame.draw.rect(pantalla, COLOR_SUELO, (self.ox, self.oy, self.ancho, self.alto))
        for pared in self.paredes:
            pygame.draw.rect(pantalla, COLOR_PARED, pared)

        # Entrada: línea verde en el borde izquierdo (aquí empieza el personaje)
        pygame.draw.rect(pantalla, COLOR_ENTRADA, self.sello_entrada.inflate(0, -self.grosor))
        y_ent = self.oy + (self.fila_entrada + 0.5) * self.celda
        texto = self._fuente.render("ENTRADA", True, COLOR_ENTRADA)
        pantalla.blit(texto, texto.get_rect(midright=(self.ox - self.grosor - 6, y_ent)))

        # Salida: meta a cuadros en el borde derecho
        self._dibujar_meta(pantalla)
        y_sal = self.oy + (self.fila_salida + 0.5) * self.celda
        texto = self._fuente.render("META", True, (255, 220, 100))
        pantalla.blit(texto, texto.get_rect(midleft=(self.ox + self.ancho + self.grosor + 10, y_sal)))

    def _dibujar_meta(self, pantalla):
        lado = 8
        x0 = self.ox + self.ancho - lado
        y0 = self.oy + self.fila_salida * self.celda
        for i in range(self.celda // lado):
            for j in range(2):
                color = (255, 255, 255) if (i + j) % 2 == 0 else (30, 30, 30)
                pygame.draw.rect(pantalla, color, (x0 + j * lado, y0 + i * lado, lado, lado))
