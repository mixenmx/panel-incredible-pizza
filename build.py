#!/usr/bin/env python3
"""Arma data/metricas.json para el panel público de Incredible Pizza Chihuahua.

Entrada:
  raw/cuenta.json    lista de filas por mes de la cuenta (ads_get_ad_entities, level=ad_account,
                     fields amount_spent, reach, impressions, frequency, cpm, like,
                     instagram_profile_follow_v2; time_increment=monthly, desde 2026-02-15)
  raw/campanas.json  lista de filas campaña x mes (level=campaign, fields name, objective,
                     amount_spent, reach, impressions, results; amount_spent > 0)
  Ambos aceptan la respuesta completa de Meta ({"ad_entities": "..."}) o solo la lista.

Salida: data/metricas.json con una fila por mes y la fecha de actualización.
Misma lógica que el panel de Claude:
  - mensajes: conversaciones de WhatsApp iniciadas de las campañas que optimizan a eso
  - cpl: gasto de esas campañas / mensajes
  - walk-in: alcance de la campaña con resultado "reach" (IP | Impressions and Reach, desde julio);
    antes, equivalente = alcance de campañas de visibilidad (no mensajes, no leads, no ventas)
  - seguidores: Facebook (like) + Instagram (instagram_profile_follow_v2) atribuidos a anuncios
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
MSG = "actions:onsite_conversion.messaging_conversation_started_7d"
LEAD = "actions:onsite_conversion.lead_grouped"


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
    res = r.get("results") or {}
    vals = res.get("values")
    if isinstance(vals, list) and vals:
        return num(vals[0].get("value"))
    return None


def change(a, b):
    if a is None or b in (None, 0):
        return None
    return round((a - b) / b, 3)


def main():
    cuenta = load(BASE / "raw" / "cuenta.json")
    campanas = load(BASE / "raw" / "campanas.json")
    filas = []
    for c in sorted(cuenta, key=lambda r: r["date_start"]):
        imp = num(c.get("impressions")) or 0
        if imp <= 0:
            continue
        mes = c["date_start"]
        del_mes = [x for x in campanas if x.get("date_start") == mes and (num(x.get("amount_spent")) or 0) > 0]
        ind = lambda x: (x.get("results") or {}).get("indicator")
        ws = [x for x in del_mes if ind(x) == MSG and result_value(x) is not None]
        oficial = [x for x in del_mes if ind(x) == "reach"]
        visib = [x for x in del_mes if ind(x) not in (MSG, LEAD) and x.get("objective") not in ("OUTCOME_LEADS", "OUTCOME_SALES")]
        walk = oficial or visib
        mensajes = int(sum(result_value(x) for x in ws))
        inv_ws = sum(num(x.get("amount_spent")) or 0 for x in ws)
        fb = int(num(c.get("like")) or 0)
        ig = int(num(c.get("instagram_profile_follow_v2")) or 0)
        filas.append({
            "mes": mes,
            "inversion": round(num(c.get("amount_spent")) or 0, 2),
            "impresiones": int(imp),
            "alcance": int(num(c.get("reach")) or 0),
            "frecuencia": round(num(c.get("frequency")) or 0, 2),
            "cpm": num(c.get("cpm")),
            "alcance_walkin": int(sum(num(x.get("reach")) or 0 for x in walk)) if walk else None,
            "walkin_tipo": "campaña walk-in" if oficial else ("equivalente" if visib else None),
            "walkin_campanas": " + ".join(x.get("name", "") for x in walk),
            "mensajes": mensajes,
            "inversion_ws": round(inv_ws, 2),
            "cpl": round(inv_ws / mensajes, 2) if mensajes else None,
            "seguidores_fb": fb,
            "seguidores_ig": ig,
            "seguidores": fb + ig,
        })
    for i, r in enumerate(filas):
        p = filas[i - 1] if i else None
        for k in ("inversion", "impresiones", "alcance", "mensajes", "cpl", "alcance_walkin"):
            r["d_" + k] = change(r[k], p[k]) if p else None
    if not filas:
        raise SystemExit("Sin filas con impresiones: no se actualiza nada.")
    merida = timezone(timedelta(hours=-6))
    salida = {"actualizado": datetime.now(merida).strftime("%Y-%m-%d %H:%M"), "meses": filas}
    (BASE / "data").mkdir(exist_ok=True)
    (BASE / "data" / "metricas.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    ult = filas[-1]
    print(f"OK {len(filas)} meses; último {ult['mes']}: {ult['mensajes']} mensajes, CPL {ult['cpl']}, gasto {ult['inversion']}")


if __name__ == "__main__":
    sys.exit(main())
