# Control gestual de personaje en un laberinto (Avance IHC)

Un personaje recorre un laberinto controlado con la posición de la palma, o de la cabeza, frente a una webcam.
Tecnologías: Python, OpenCV, MediaPipe Hands y Pygame.

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

1. Siéntate frente a la cámara a 40-80 cm, con buena luz de frente. Con la mano, que se vea completa.
2. Elige la entrada con **H** (MANO o CABEZA; el HUD muestra la activa). Coloca la palma, o la cabeza,
   en una posición cómoda y presiona **C** para calibrar el centro. En modo cabeza el centro se fija
   solo en la primera detección.
3. Mueve la mano (o desplaza la cabeza **un poco**, sin dejar de mirar la pantalla) hacia arriba,
   abajo, izquierda o derecha del cuadro amarillo del indicador.
4. Dentro del cuadro o fuera de cámara = personaje detenido.
5. Lleva al personaje desde la **ENTRADA** (izquierda) hasta la **META** a cuadros (arriba a la
   derecha). El cronómetro arranca con el primer movimiento.

| Tecla | Acción |
|---|---|
| **H** | Cambiar la entrada: MANO <-> CABEZA |
| **C** | Calibrar el centro neutral de la entrada activa |
| **V** | Mostrar u ocultar el video de la cámara (por defecto solo se ve el indicador de mano o cabeza) |
| **R** | Reiniciar el laberinto |
| **ESC / Q** | Salir |

**Flechas amarillas:** cuando el personaje no se mueve (mano en reposo o empujando una pared),
aparecen flechas hacia las direcciones por las que se puede seguir.

## El laberinto

Es la transcripción del laberinto de la imagen del proyecto (cuadrícula de 8 x 8 celdas) y está
definido como texto en `laberinto.py` (`MAPA`), así que se puede editar a mano. Las celdas del juego
son cuadradas (en la imagen original estaban estiradas); la topología de pasillos y paredes es idéntica.

- **Colisiones:** las paredes son rectángulos; el personaje se desliza a lo largo de ellas.
- **Ayuda en giros:** si en la celda actual se puede avanzar en la dirección ordenada, el personaje se
  centra solo en el pasillo. Una orden de giro dada un poco antes o después de la esquina no lo atora.
- **Velocidad:** 200 px/s (`Juego.velocidad`), pensada para tolerar la latencia del gesto.

## Imágenes del personaje

Coloca en `assets/` cuatro imágenes (de preferencia PNG con fondo transparente):
`arriba.png`, `abajo.png`, `izquierda.png`, `derecha.png`. Se escalan automáticamente.
Si falta alguna, se dibuja un personaje de respaldo para esa dirección.
Al detenerse, el personaje conserva la orientación de su último movimiento.

## Arquitectura (capas)

```
 hilo de captura                                          hilo principal (60 fps)
+------------------------------------------+            +---------------------------+
| Cámara -> Reconocedor (MediaPipe,        |  comando   |  Juego (Pygame) + HUD     |
| suavizado, zona muerta, estabilizador)   | ---------> |  indicador de mano        |
+------------------------------------------+            +---------------------------+
```

| Archivo | Responsabilidad |
|---|---|
| `comandos.py` | Vocabulario compartido (ARRIBA, ABAJO, IZQUIERDA, DERECHA, QUIETO) |
| `reconocedor.py` | Captura y MediaPipe en un hilo propio; posición de la palma o la nariz -> comando estabilizado |
| `laberinto.py` | Mapa del laberinto, paredes (colisión) y su dibujo |
| `juego.py` | Personaje, movimiento con colisiones, flechas de salidas, cronómetro y meta (no conoce la cámara) |
| `indicador.py` | Indicador compacto de la mano (reemplaza al video como retroalimentación principal) |
| `main.py` | Integra capas, HUD (panel derecho) y teclas |
| `assets/` | Imágenes del personaje (opcional) |

## Rendimiento y diagnóstico

Leer la cámara y ejecutar MediaPipe se hace en un **hilo aparte**: el juego dibuja a 60 fps
independientemente de la cámara y usa el último comando disponible. Si el resultado tiene más de
0.5 s (cámara congelada, fallo en el hilo), el comando pasa a QUIETO: el personaje se detiene en vez
de seguir caminando con un dato viejo.

El HUD muestra tres números que separan las posibles causas de lentitud:

| Línea del HUD | Si baja o sube |
|---|---|
| `Juego: N fps` | Problema del dibujo (debería mantenerse en ~60) |
| `Cámara: N fps` | La cámara entrega pocos frames: poca luz (la exposición automática baja los FPS), ancho de banda USB o formato de video |
| `MediaPipe: N ms` | La CPU no alcanza (calor, otros programas). Por encima de ~35 ms no se sostienen 30 fps |

Si la cámara baja a ~15 fps con el tiempo: mejora la iluminación frontal; en Linux, si la cámara lo
expone, `v4l2-ctl -d /dev/video0 --set-ctrl=exposure_dynamic_framerate=0` evita que baje los FPS para
exponer más. `Reconocedor` pide además MJPG a 640x480 y 30 fps (algunas cámaras ignoran la petición)
y usa el modelo ligero de MediaPipe (`model_complexity=0`).

## Decisiones de diseño (IHC)

- **Gesto:** posición de la palma respecto a un centro neutral. Natural, sin aprendizaje
  y puede hacerse con el codo apoyado, lo que reduce la fatiga.
- **Entrada alternativa, cabeza:** la punta de la nariz (MediaPipe Face Detection, modelo de corto
  alcance) pasa por la misma lógica que la palma. La zona muerta es más chica (0.05 contra 0.12)
  porque la cabeza se desplaza mucho menos. Solo corre el modelo de la entrada activa para no gastar
  CPU, y el centro de la cabeza se fija solo al empezar, ya que no existe una "posición cómoda"
  universal. Pensada para quien no puede usar las manos; con movimientos pequeños de traslado, no
  giros grandes, para no perder de vista la pantalla.
- **Zona muerta:** evita movimientos involuntarios y da un estado de descanso.
- **Calibración (C):** se adapta a la postura de cada usuario.
- **Espejo:** mapeo natural entre el movimiento del usuario y la pantalla.
- **Estabilizador:** media móvil exponencial + votación por mayoría. Elimina el parpadeo.
- **Sin mano o sin datos = detenido:** medida de seguridad.
- **Indicador en lugar de video:** el video mostraba mucho más de lo necesario y competía con el
  laberinto. El indicador solo muestra la mano, la zona neutral y la dirección reconocida.
- **Flechas de salidas:** orientan al usuario sobre hacia dónde puede mover la mano.

### Historial: control por deslizamientos (descartado)

Se implementó y probó un segundo modo en el que deslizar la mano arriba/abajo/izquierda/derecha
hacía correr al personaje hasta la siguiente bifurcación (puño = alto). En pruebas con la cámara real
los gestos no se reconocían de forma confiable y no era claro cómo mover al personaje, por lo que se
retiró y se conservó el control por posición. Se conservaron las flechas de salidas, que sí
resultaron útiles.

## Parámetros ajustables (`Reconocedor`)

| Parámetro | Efecto |
|---|---|
| `ZONA_MUERTA` (mano 0.12, cabeza 0.05) | Mayor = menos sensible, menos falsos movimientos |
| `alfa` (0.5) | Menor = más suave pero con más retraso |
| `ventana` / `votos_min` (5 / 3) | Mayor = más estable pero con más latencia |

## Limitaciones observadas

- La detección se pierde si la mano está demasiado cerca de la cámara.
- Con más de una mano visible se rastrea solo una (`max_num_hands=1`).
- Depende de la iluminación y del contraste con el fondo.
- El modo mano requiere una mano con la palma visible; el modo cabeza lo cubre, pero puede cansar el
  cuello y no sirve con movilidad cervical limitada. Ambos modos dependen de la luz.
- El modo cabeza no se ha probado con usuarios reales: la zona muerta de 0.05 es una estimación.

## Pendiente para siguientes avances

- Pruebas con usuarios (tiempo de resolución, errores, cuestionario SUS).
- Más niveles (otros mapas en `laberinto.py`).
