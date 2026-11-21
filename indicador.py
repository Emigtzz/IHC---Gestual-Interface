"""
indicador.py
Indicador compacto de la mano o la cabeza: reemplaza al video de la cámara como retroalimentación principal.

Por qué: el video muestra mucho más de lo que el usuario necesita mientras juega (su cuarto, su cara)
y compite por su atención con el laberinto. Aquí solo se dibuja lo que importa para saber si el
sistema lo entiende: dónde está la mano, dónde está la zona neutral (cuadro amarillo) y qué
dirección reconoció (la flecha se enciende mientras la mano esté fuera de la zona).
"""
import pygame

from comandos import ABAJO, ARRIBA, DERECHA, IZQUIERDA, VECTORES

FONDO = (32, 36, 52)
BORDE = (90, 96, 120)
GRIS = (110, 116, 140)
CLARO = (170, 175, 195)
ACENTO = (255, 200, 60)
VERDE = (80, 220, 120)
ROJO = (230, 70, 70)


def _flecha(pantalla, centro, direccion, activa):
    vx, vy = VECTORES[direccion]
    k = 13
    punta = (centro[0] + vx * k, centro[1] + vy * k)
    base1 = (centro[0] - vx * k - vy * k, centro[1] - vy * k + vx * k)
    base2 = (centro[0] - vx * k + vy * k, centro[1] - vy * k - vx * k)
    if activa:
        pygame.draw.polygon(pantalla, ACENTO, (punta, base1, base2))
    else:
        pygame.draw.polygon(pantalla, GRIS, (punta, base1, base2), 2)


def dibujar_indicador(pantalla, rect, info, comando, fuente):
    """rect: zona de pantalla donde se dibuja. info: Reconocedor.info(). comando: el comando actual."""
    pygame.draw.rect(pantalla, FONDO, rect, border_radius=12)
    pygame.draw.rect(pantalla, BORDE, rect, 2, border_radius=12)

    def a_pantalla(p):
        return (rect.x + p[0] * rect.w, rect.y + p[1] * rect.h)

    # Flechas en los cuatro lados
    margen = 24
    lados = {
        ARRIBA: (rect.centerx, rect.y + margen),
        ABAJO: (rect.centerx, rect.bottom - margen - 22),
        IZQUIERDA: (rect.x + margen, rect.centery),
        DERECHA: (rect.right - margen, rect.centery),
    }
    for direccion, pos in lados.items():
        _flecha(pantalla, pos, direccion, activa=(comando == direccion))

    # Zona neutral
    cx, cy = info["centro"]
    zm = info["zona_muerta"]
    zona = pygame.Rect(0, 0, zm * 2 * rect.w, zm * 2 * rect.h)
    zona.center = a_pantalla((cx, cy))
    pygame.draw.rect(pantalla, ACENTO, zona, 2, border_radius=6)

    punto = info["punto"]
    nombre = "Mano" if info["fuente"] == "mano" else "Cabeza"
    if punto is not None:
        pygame.draw.circle(pantalla, VERDE, a_pantalla(punto), 9)
        pygame.draw.circle(pantalla, (255, 255, 255), a_pantalla(punto), 9, 2)
        estado, color = f"{nombre} detectada" if nombre == "Mano" else "Cabeza detectada", CLARO
    else:
        estado, color = f"SIN {nombre.upper()}", ROJO
    pantalla.blit(fuente.render(estado, True, color), (rect.x + 14, rect.bottom - 30))
