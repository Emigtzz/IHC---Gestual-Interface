# Graph Report - IHC---Gestual-Interface-main  (2026-11-21)

## Corpus Check
- 7 files · ~6,245 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: (none) 1)

## Summary
- 109 nodes · 182 edges · 11 communities (2 shown, 9 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- main
- Juego
- juego.py
- main.py
- Control gestual de personaje en un laberinto (Avance IHC)
- Laberinto
- Reconocedor

## God Nodes (most connected - your core abstractions)
1. `Reconocedor` - 24 edges
2. `main()` - 20 edges
3. `Laberinto` - 14 edges
4. `Juego` - 13 edges
5. `Control gestual de personaje en un laberinto (Avance IHC)` - 11 edges
6. `dibujar_indicador()` - 7 edges
7. `formato_tiempo()` - 4 edges
8. `cargar_sprites()` - 4 edges
9. `_sprite_respaldo()` - 4 edges
10. `avisos_de_rendimiento()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Ejecución` --references--> `Reconocedor`  [INFERRED]
  README.md → reconocedor.py
- `Parámetros ajustables (`Reconocedor`)` --references--> `Reconocedor`  [INFERRED]
  README.md → reconocedor.py
- `Rendimiento y diagnóstico` --references--> `Reconocedor`  [INFERRED]
  README.md → reconocedor.py
- `Juego` --uses--> `Laberinto`  [INFERRED]
  juego.py → laberinto.py
- `main()` --calls--> `dibujar_indicador()`  [EXTRACTED]
  main.py → indicador.py

## Import Cycles
- None detected.

## Communities (11 total, 9 thin omitted)

### Community 2 - "juego.py"
Cohesion: 0.11
Nodes (6): dibujar_indicador(), _flecha(), _acercar(), cargar_sprites(), _sprite_respaldo(), _parsear()

### Community 4 - "Control gestual de personaje en un laberinto (Avance IHC)"
Cohesion: 0.15
Nodes (12): Arquitectura (capas), Control gestual de personaje en un laberinto (Avance IHC), Decisiones de diseño (IHC), Ejecución, El laberinto, Historial: control por deslizamientos (descartado), Imágenes del personaje, Limitaciones observadas (+4 more)

## Knowledge Gaps
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Reconocedor` connect `Reconocedor` to `main`, `main.py`, `Control gestual de personaje en un laberinto (Avance IHC)`, `._clasificar`, `._procesar_frame`, `.cambiar_fuente`, `.obtener`?**
  _High betweenness centrality (0.460) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Reconocedor` (e.g. with `Ejecución` and `Parámetros ajustables (`Reconocedor`)`) actually correct?**
  _`Reconocedor` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `juego.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11462450592885376 - nodes in this community are weakly interconnected._
- **Why does `main()` connect `main` to `Juego`, `juego.py`, `main.py`, `Laberinto`, `._clasificar`, `Reconocedor`, `.cambiar_fuente`, `.obtener`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `main()` (e.g. with `.actualizar()` and `.dibujar()`) actually correct?**
  _`main()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Why does `Juego` connect `Juego` to `main`, `juego.py`, `main.py`, `Laberinto`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._