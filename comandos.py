"""
comandos.py
Vocabulario compartido entre el reconocedor y el juego.
Así ambas capas se comunican solo con estas constantes y no se conocen entre sí.

El comando es un ESTADO: mientras la mano siga a la derecha del centro, llega DERECHA en cada
frame y el personaje se mueve mientras dure. QUIETO significa "no mover".
"""

ARRIBA = "ARRIBA"
ABAJO = "ABAJO"
IZQUIERDA = "IZQUIERDA"
DERECHA = "DERECHA"
QUIETO = "QUIETO"

DIRECCIONES = (ARRIBA, ABAJO, IZQUIERDA, DERECHA)

# Vector de movimiento (dx, dy) de cada comando.
# En pantalla, y crece hacia ABAJO.
VECTORES = {
    ARRIBA: (0, -1),
    ABAJO: (0, 1),
    IZQUIERDA: (-1, 0),
    DERECHA: (1, 0),
    QUIETO: (0, 0),
}
