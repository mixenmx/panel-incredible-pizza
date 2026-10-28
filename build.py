#!/usr/bin/env python3
"""Arma data/metricas.json para el panel público de Incredible Pizza Chihuahua.

Entradas (respuestas de Meta Ads, ads_get_ad_entities; se acepta la respuesta completa
{"ad_entities": "..."} o solo la lista):
  raw/cuenta.json     level=ad_account, time_increment=monthly, desde 2026-02-15.
                      fields: amount_spent, reach, impressions, frequency, cpm, like,
                      instagram_profile_follow_v2
  raw/campanas.json   level=campaign, time_increment=monthly, amount_spent > 0.
                      fields: name, objective, amount_spent, reach, impressions, results
  raw/cortes/<AAAA-MM-DD>_cuenta.json y raw/cortes/<AAAA-MM-DD>_campanas.json
                      Cortes acumulados del mes en curso (1-7, 1-14, 1-21, 1-28): las mismas
                      dos consultas que arriba, pero SIN time_increment y con time_range
                      desde el día 1 hasta el fin del corte (o hasta hoy si el corte no ha
                      terminado). El nombre del archivo es el fin nominal del corte
                      (p. ej. 2026-11-07).
  data/cortes.json    Historial de cortes ya calculados (se actualiza con lo anterior).

Salida: data/metricas.json con una fila por mes, sus cortes acumulados y la fecha de
actualización. Misma lógica que el panel de Claude:
  - mensajes: conversaciones de WhatsApp iniciadas de las campañas que optimizan a eso
  - cpl: gasto de esas campañas / mensajes
  - walk-in: alcance de la campaña con resultado "reach" (IP | Impressions and Reach,
    desde el 22 de julio); si no corrió en el periodo, equivalente = alcance de las
    campañas de visibilidad (no mensajes, no leads, no ventas)
  - seguidores: Facebook (like) + Instagram (instagram_profile_follow_v2) atribuidos a anuncios
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
MSG = "actions:onsite_conversion.messaging_conversation_started_7d"
LEAD = "actions:onsite_conversion.lead_grouped"
INICIO = "2026-02-15"
MERIDA = timezone(timedelta(hours=-6))
CORTES = (7, 14, 21, 28)


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "ad_entities" not in data:
            raise SystemExit(f"{path}: no trae ad_entities; llaves: {list(data)}")
        data = data["ad_entities"]
        if isinstance(data, str):
            data = json.loads(data)
    return data


def num(v):
    if isinstance(v, dict):
        v = v.get("value")
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def result_value(r):
    vals = (r.get("results") or {}).get("values")
    if isinstance(vals, list) and vals:
        return num(vals[0].get("value"))
    return None


def change(a, b):
    if a is None or b in (None, 0):
        return None
    return round((a - b) / b, 3)


def fila(c, campanas):
    """Métricos de un periodo: c = fila de la cuenta; campanas = filas de campaña del mismo periodo."""
    ind = lambda x: (x.get("results") or {}).get("indicator")
    activas = [x for x in campanas if (num(x.get("amount_spent")) or 0) > 0]
    ws = [x for x in activas if ind(x) == MSG and result_value(x) is not None]
    oficial = [x for x in activas if ind(x) == "reach"]
    visib = [x for x in activas if ind(x) not in (MSG, LEAD) and x.get("objective") not in ("OUTCOME_LEADS", "OUTCOME_SALES")]
    walk = oficial or visib
    mensajes = int(sum(result_value(x) for x in ws))
    inv_ws = sum(num(x.get("amount_spent")) or 0 for x in ws)
    inv = num(c.get("amount_spent")) or 0
    imp = int(num(c.get("impressions")) or 0)
    alc = int(num(c.get("reach")) or 0)
    fb = int(num(c.get("like")) or 0)
    ig = int(num(c.get("instagram_profile_follow_v2")) or 0)
    return {
        "inversion": round(inv, 2),
        "impresiones": imp,
        "alcance": alc,
        "frecuencia": round(imp / alc, 2) if alc else None,
        "cpm": round(inv / imp * 1000, 2) if imp else None,
        "alcance_walkin": int(sum(num(x.get("reach")) or 0 for x in walk)) if walk else None,
        "walkin_tipo": "campaña walk-in" if oficial else ("equivalente" if visib else None),
        "walkin_campanas": " + ".join(x.get("name", "") for x in walk),
        "mensajes": mensajes,
        "inversion_ws": round(inv_ws, 2),
        "cpl": round(inv_ws / mensajes, 2) if mensajes else None,
        "seguidores_fb": fb,
        "seguidores_ig": ig,
        "seguidores": fb + ig,
    }


def cortes_nuevos(hoy):
    """Recalcula los cortes que traiga raw/cortes/ (los del mes en curso)."""
    salida = {}
    carpeta = BASE / "raw" / "cortes"
    for f in sorted(carpeta.glob("*_cuenta.json")):
        corte = f.name.split("_")[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", corte):
            continue
        fc = carpeta / f"{corte}_campanas.json"
        if not fc.exists():
            raise SystemExit(f"Falta {fc.name} para el corte {corte}")
        cuenta = load(f)
        if not cuenta:
            raise SystemExit(f"{f.name} viene vacío")
        r = fila(cuenta[0], load(fc))
        mes = corte[:7]
        r["desde"] = INICIO if mes == INICIO[:7] else mes + "-01"
        r["hasta"] = min(corte, hoy)
        r["corte"] = corte
        r["fuente"] = "Meta Ads: consulta acumulada por corte"
        salida[corte] = r
    return salida


def main():
    hoy = datetime.now(MERIDA).strftime("%Y-%m-%d")
    cuenta = load(BASE / "raw" / "cuenta.json")
    campanas = load(BASE / "raw" / "campanas.json")

    filas = []
    for c in sorted(cuenta, key=lambda r: r["date_start"]):
        if (num(c.get("impressions")) or 0) <= 0:
            continue
        mes = c["date_start"]
        r = fila(c, [x for x in campanas if x.get("date_start") == mes])
        r["frecuencia"] = round(num(c.get("frequency")) or 0, 2) or r["frecuencia"]
        r["cpm"] = num(c.get("cpm")) if num(c.get("cpm")) is not None else r["cpm"]
        r["mes"] = mes
        r["hasta"] = min(c.get("date_stop") or hoy, hoy)
        filas.append(r)
    if not filas:
        raise SystemExit("Sin filas con impresiones: no se actualiza nada.")

    # Cortes acumulados: historial + los del mes en curso
    ruta_cortes = BASE / "data" / "cortes.json"
    historial = json.loads(ruta_cortes.read_text(encoding="utf-8")) if ruta_cortes.exists() else {}
    historial.update(cortes_nuevos(hoy))
    ruta_cortes.write_text(json.dumps(historial, ensure_ascii=False, indent=1), encoding="utf-8")

    # Si un corte cubre el mismo periodo que el mes y es más reciente, el mes toma esos valores
    for r in filas:
        for x in historial.values():
            if x.get("desde") == r["mes"] and x.get("hasta", "") >= r["hasta"] and x["corte"][:7] == r["mes"][:7]:
                r.update({k: x[k] for k in x if k not in ("desde", "corte", "fuente")})

    for i, r in enumerate(filas):
        p = filas[i - 1] if i else None
        for k in ("inversion", "impresiones", "alcance", "mensajes", "cpl", "alcance_walkin"):
            r["d_" + k] = change(r[k], p[k]) if p else None

    for r in filas:
        mes = r["mes"][:7]
        lista = []
        for dia in CORTES:
            corte = f"{mes}-{dia:02d}"
            if corte < r["mes"]:          # febrero empieza el 15: no hay 1-7 ni 1-14
                continue
            x = historial.get(corte)
            if x is None:
                continue
            x = dict(x)
            x["etiqueta"] = f"Del 1 al {dia}"
            x["en_curso"] = x.get("hasta", corte) < corte or corte >= hoy
            lista.append(x)
        r["cortes"] = lista

    salida = {"actualizado": datetime.now(MERIDA).strftime("%Y-%m-%d %H:%M"), "meses": filas}
    (BASE / "data" / "metricas.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    ult = filas[-1]
    print(f"OK {len(filas)} meses; último {ult['mes']}: {ult['mensajes']} mensajes, CPL {ult['cpl']}, "
          f"gasto {ult['inversion']}; cortes del mes: {[c['corte'][-2:] for c in ult['cortes']]}")


if __name__ == "__main__":
    sys.exit(main())
