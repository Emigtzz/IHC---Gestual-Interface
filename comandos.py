"""
comandos.py
Vocabulario compartido entre el reconocedor de gestos y el juego.
Así ambas capas se comunican solo con estas constantes y no se conocen entre sí.
"""

ARRIBA = "ARRIBA"
ABAJO = "ABAJO"
IZQUIERDA = "IZQUIERDA"
DERECHA = "DERECHA"
QUIETO = "QUIETO"

# Vector de movimiento (dx, dy) de cada comando.
# En pantalla, y crece hacia ABAJO.
VECTORES = {
    ARRIBA: (0, -1),
    ABAJO: (0, 1),
    IZQUIERDA: (-1, 0),
    DERECHA: (1, 0),
    QUIETO: (0, 0),
}
