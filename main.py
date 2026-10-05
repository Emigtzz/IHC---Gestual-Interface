"""
main.py
Integra las tres capas:  Reconocedor (cámara + gestos)  ->  comando  ->  Juego.

Teclas:
  C         calibrar centro neutral (con la palma en posición cómoda)
  ESC / Q   salir
El personaje se controla únicamente con gestos de la mano.
"""
import sys

import cv2
import pygame

from juego import Juego
from reconocedor import Reconocedor

ANCHO, ALTO = 1280, 720
MINI_ANCHO, MINI_ALTO = 400, 300


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Control gestual - Avance IHC")
    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont(None, 32)
    fuente_grande = pygame.font.SysFont(None, 60)

    reconocedor = Reconocedor()
    if not reconocedor.camara_disponible():
        print("No se pudo abrir la cámara. Revisa el índice (0, 1...) o los permisos.")
        sys.exit(1)

    juego = Juego(ANCHO, ALTO)
    mensaje, mensaje_hasta = "", 0

    corriendo = True
    while corriendo:
        dt = reloj.tick(60) / 1000.0

        # --- Eventos ---------------------------------------------------
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_ESCAPE, pygame.K_q):
                    corriendo = False
                elif evento.key == pygame.K_c:
                    ok = reconocedor.calibrar()
                    mensaje = "Centro calibrado" if ok else "No se detecta la mano"
                    mensaje_hasta = pygame.time.get_ticks() + 1500

        # --- Entrada: únicamente el gesto ------------------------------
        comando, frame = reconocedor.procesar()

        # --- Lógica y dibujo -------------------------------------------
        juego.actualizar(comando, dt)
        juego.dibujar(pantalla)

        # Vista previa de la cámara (retroalimentación visual)
        if frame is not None:
            mini = cv2.resize(frame, (MINI_ANCHO, MINI_ALTO))
            rgb = cv2.cvtColor(mini, cv2.COLOR_BGR2RGB)
            superficie = pygame.image.frombuffer(rgb.tobytes(), (MINI_ANCHO, MINI_ALTO), "RGB")
            pos = (ANCHO - MINI_ANCHO - 15, 15)
            pantalla.blit(superficie, pos)
            pygame.draw.rect(pantalla, (255, 255, 255), (*pos, MINI_ANCHO, MINI_ALTO), 2)

        # HUD
        pantalla.blit(fuente_grande.render(comando, True, (255, 255, 255)), (25, 20))
        pantalla.blit(
            fuente.render(f"FPS: {reloj.get_fps():.0f}", True, (170, 175, 195)),
            (25, 78),
        )
        pantalla.blit(
            fuente.render("C: calibrar centro | ESC: salir", True, (170, 175, 195)),
            (25, ALTO - 40),
        )
        if pygame.time.get_ticks() < mensaje_hasta:
            pantalla.blit(fuente.render(mensaje, True, (255, 220, 100)), (25, 115))

        pygame.display.flip()

    reconocedor.cerrar()
    pygame.quit()


if __name__ == "__main__":
    main()
