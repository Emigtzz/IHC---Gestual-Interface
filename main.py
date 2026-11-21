"""
main.py
Integra las capas:  Reconocedor (cámara + MediaPipe, en su propio hilo)  ->  comando  ->  Juego.

Control: la posición de la palma (o de la nariz, en modo cabeza) respecto a un centro neutral
(cuadro amarillo del indicador).

Teclas:
  H         cambiar la entrada: MANO <-> CABEZA
  C         calibrar centro neutral (con la palma o la cabeza en posición cómoda)
  V         mostrar / ocultar el video de la cámara (por defecto se ve solo el indicador de mano)
  R         reiniciar el laberinto
  ESC / Q   salir
El personaje se controla únicamente con la mano o la cabeza; el teclado solo gestiona la aplicación.

Pantalla: el laberinto ocupa la izquierda y el panel derecho aloja el indicador de mano y el HUD,
de modo que la retroalimentación nunca tapa el escenario.

Diagnóstico (HUD): FPS del juego, FPS que entrega la cámara y milisegundos que tarda MediaPipe por
frame. Si algo se vuelve lento, estos tres números dicen cuál es la causa.
"""
import sys

import cv2
import pygame

from indicador import dibujar_indicador
from juego import Juego, formato_tiempo
from reconocedor import Reconocedor

ANCHO, ALTO = 1280, 720
MINI_ANCHO, MINI_ALTO = 400, 300
PANEL_X = 790                                  # el panel derecho empieza aquí
CAM_X = PANEL_X + (ANCHO - PANEL_X - MINI_ANCHO) // 2
CAM_Y = 40
BLANCO = (255, 255, 255)
GRIS = (170, 175, 195)
ACENTO = (255, 200, 60)
ROJO = (230, 70, 70)

FPS_CAMARA_MIN = 20   # por debajo se avisa de cámara lenta
MS_IA_MAX = 35        # por encima se avisa de MediaPipe lento (a 30 fps hay ~33 ms por frame)


def avisos_de_rendimiento(est):
    """Texto y color de un aviso si la cámara o MediaPipe están lentos; (None, None) si todo va bien."""
    if est["error"]:
        return f"Error: {est['error'][:40]}", ROJO
    if est["fps_camara"] == 0:
        return "Sin imagen de la cámara", ROJO
    if est["fps_camara"] < FPS_CAMARA_MIN:
        return "Cámara lenta: revisa la luz", ACENTO
    if est["ms_ia"] > MS_IA_MAX:
        return "MediaPipe lento (CPU)", ACENTO
    return None, None


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Control gestual - Avance IHC")
    reloj = pygame.time.Clock()
    fuente = pygame.font.SysFont(None, 32)
    fuente_chica = pygame.font.SysFont(None, 27)
    fuente_grande = pygame.font.SysFont(None, 60)

    reconocedor = Reconocedor()
    if not reconocedor.camara_disponible():
        print("No se pudo abrir la cámara. Revisa el índice (0, 1...) o los permisos.")
        sys.exit(1)
    reconocedor.iniciar()

    juego = Juego(ANCHO, ALTO)
    mensaje, mensaje_hasta = "", 0

    corriendo = True
    while corriendo:
        dt = reloj.tick(60) / 1000.0
        ahora = pygame.time.get_ticks()

        # --- Eventos de teclado (gestionan la aplicación, no al personaje) ------
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_ESCAPE, pygame.K_q):
                    corriendo = False
                elif evento.key == pygame.K_r:
                    juego.reiniciar()
                elif evento.key == pygame.K_v:
                    reconocedor.mostrar_video = not reconocedor.mostrar_video
                elif evento.key == pygame.K_h:
                    mensaje = f"Entrada: {reconocedor.cambiar_fuente().upper()}"
                    mensaje_hasta = ahora + 1500
                elif evento.key == pygame.K_c:
                    mensaje = "Centro calibrado" if reconocedor.calibrar() else "No se detecta nada"
                    mensaje_hasta = ahora + 1500

        # --- Entrada: únicamente la mano o la cabeza (último resultado del hilo; no espera a la cámara) ---
        comando, frame = reconocedor.obtener()

        # --- Lógica y dibujo -------------------------------------------
        juego.actualizar(comando, dt)
        juego.dibujar(pantalla)

        # Retroalimentación: indicador de mano/cabeza (o el video, si se pidió con V)
        if reconocedor.mostrar_video and frame is not None:
            mini = cv2.resize(frame, (MINI_ANCHO, MINI_ALTO))
            rgb = cv2.cvtColor(mini, cv2.COLOR_BGR2RGB)
            superficie = pygame.image.frombuffer(rgb.tobytes(), (MINI_ANCHO, MINI_ALTO), "RGB")
            pantalla.blit(superficie, (CAM_X, CAM_Y))
            pygame.draw.rect(pantalla, BLANCO, (CAM_X, CAM_Y, MINI_ANCHO, MINI_ALTO), 2)
        else:
            rect = pygame.Rect(CAM_X + (MINI_ANCHO - MINI_ALTO) // 2, CAM_Y, MINI_ALTO, MINI_ALTO)
            dibujar_indicador(pantalla, rect, reconocedor.info(), comando, fuente)

        # HUD (panel derecho, debajo del indicador)
        est = reconocedor.estadisticas()
        aviso, color_aviso = avisos_de_rendimiento(est)
        y = CAM_Y + MINI_ALTO + 25
        pantalla.blit(fuente_grande.render(comando, True, BLANCO), (CAM_X, y))
        pantalla.blit(fuente.render(f"Tiempo: {formato_tiempo(juego.tiempo)}", True, BLANCO), (CAM_X, y + 62))
        pantalla.blit(fuente_chica.render(f"Juego: {reloj.get_fps():.0f} fps", True, GRIS), (CAM_X, y + 100))
        pantalla.blit(
            fuente_chica.render(f"Cámara: {est['fps_camara']:.0f} fps  |  MediaPipe: {est['ms_ia']:.0f} ms",
                                True, color_aviso or GRIS),
            (CAM_X, y + 128),
        )
        pantalla.blit(fuente_chica.render(f"Entrada: {reconocedor.fuente.upper()}", True, BLANCO), (CAM_X, y + 190))
        if aviso:
            pantalla.blit(fuente_chica.render(aviso, True, color_aviso), (CAM_X, y + 156))
        elif ahora < mensaje_hasta:
            pantalla.blit(fuente_chica.render(mensaje, True, ACENTO), (CAM_X, y + 156))
        pantalla.blit(fuente_chica.render("H: mano/cabeza | C: calibrar | V: cámara", True, GRIS), (CAM_X, ALTO - 70))
        pantalla.blit(fuente_chica.render("R: reiniciar | ESC: salir", True, GRIS), (CAM_X, ALTO - 40))

        pygame.display.flip()

    reconocedor.cerrar()
    pygame.quit()


if __name__ == "__main__":
    main()
