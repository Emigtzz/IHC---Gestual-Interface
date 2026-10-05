# Control gestual de personaje en 4 direcciones (Avance IHC)

Un personaje se mueve arriba, abajo, izquierda y derecha según la posición de la
palma frente a una webcam. Tecnologías: Python, OpenCV, MediaPipe Hands y Pygame.

## Ejecución

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Si la ventana no abre en Linux: `export QT_QPA_PLATFORM=xcb`.
Si no detecta la cámara: cambiar `indice_camara=0` por `1` en `Reconocedor()`.

## Uso

1. Siéntate frente a la cámara a 40-80 cm, con la mano completa visible.
2. Coloca la palma en una posición cómoda y presiona **C** para calibrar el centro.
3. Mueve la mano hacia arriba, abajo, izquierda o derecha del cuadro azul.
4. Mano dentro del cuadro o fuera de cámara = personaje detenido.

## Imágenes del personaje

Coloca en `assets/` cuatro imágenes (de preferencia PNG con fondo transparente):
`arriba.png`, `abajo.png`, `izquierda.png`, `derecha.png`. Se escalan automáticamente.
Si falta alguna, se dibuja un personaje de respaldo para esa dirección.
Al detenerse, el personaje conserva la orientación de su último movimiento.

## Arquitectura (capas)

```
Cámara -> Reconocedor (MediaPipe + suavizado + estabilizador) -> comando -> Juego (Pygame)
                          ^                                                     |
                          +------------ retroalimentación visual <--------------+
```

| Archivo | Responsabilidad |
|---|---|
| `comandos.py` | Vocabulario compartido (ARRIBA, ABAJO, IZQUIERDA, DERECHA, QUIETO) |
| `reconocedor.py` | Captura, detección de mano, clasificación y estabilización |
| `juego.py` | Personaje con sprite por dirección y lógica de movimiento (no conoce la cámara) |
| `main.py` | Integra capas, HUD y calibración |
| `assets/` | Imágenes del personaje (opcional): `arriba.png`, `abajo.png`, `izquierda.png`, `derecha.png` |

## Decisiones de diseño (IHC)

- **Gesto:** posición de la palma respecto a un centro neutral. Natural, sin aprendizaje
  y puede hacerse con el codo apoyado, lo que reduce la fatiga.
- **Zona muerta:** evita movimientos involuntarios y da un estado de descanso.
- **Calibración (C):** se adapta a la postura de cada usuario.
- **Espejo:** mapeo natural entre el movimiento del usuario y la pantalla.
- **Estabilizador:** media móvil exponencial + votación por mayoría. Elimina el parpadeo.
- **Sin mano = detenido:** medida de seguridad.
- **Retroalimentación visual:** cámara en vivo, zona muerta, comando actual y FPS.

## Parámetros ajustables (`Reconocedor`)

| Parámetro | Efecto |
|---|---|
| `zona_muerta` (0.12) | Mayor = menos sensible, menos falsos movimientos |
| `alfa` (0.5) | Menor = más suave pero con más retraso |
| `ventana` / `votos_min` (5 / 3) | Mayor = más estable pero con más latencia |

## Limitaciones observadas

- La detección se pierde si la mano está demasiado cerca de la cámara.
- Con más de una mano visible se rastrea solo una (`max_num_hands=1`).
- Depende de la iluminación y del contraste con el fondo.

## Pendiente para siguientes avances

- Pruebas con usuarios (tasa de error, latencia, cuestionario SUS).
- Comparar contra un segundo gesto (dedo índice apuntando).
- Objetivos o niveles en el juego.
