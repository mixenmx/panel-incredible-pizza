# Panel público · Incredible Pizza Chihuahua × Mixen

Sitio estático (GitHub Pages). No depende de Claude ni de servicios externos.

## Archivos
- `index.html`: la página (métricos + calendario).
- `data/metricas.json`: métricos por mes. Lo genera `build.py`; no se edita a mano.
- `data/piezas.json`: piezas aprobadas del calendario (lista vacía `[]` = calendario en limpio).
- `raw/`: respuestas de Meta Ads que usa `build.py`.
- `assets/logo-incredible-pizza.png`: logo oficial (Incredible Pizza Company).

## Actualizar métricos (lo hace la tarea programada a diario)
1. Meta Ads, cuenta 1705372499505042, `ads_get_ad_entities`, `time_increment: monthly`,
   `time_range` desde 2026-02-15 hasta hoy:
   - level `ad_account`, fields: amount_spent, reach, impressions, frequency, cpm, like, instagram_profile_follow_v2 → `raw/cuenta.json`
   - level `campaign`, fields: name, objective, amount_spent, reach, impressions, results; filtro amount_spent > 0 → `raw/campanas.json`
2. `python3 build.py`
3. Commit y push a `main`.

## Agregar una pieza al calendario
Añadir un objeto a `data/piezas.json`:
```json
{"id": "2026-11-02-muertos", "fecha": "2026-11-02", "hora": "12:00", "red": "Instagram",
 "formato": "Carrusel", "titulo": "Altar de sabores", "copy": "Texto del post…",
 "imagen": "piezas/2026-11-02-muertos.jpg"}
```
La imagen va en la carpeta `piezas/`.

## Cálculos
Ver `claude/panel-cliente-metodologia.md` en el proyecto "Incredible Pizza".
