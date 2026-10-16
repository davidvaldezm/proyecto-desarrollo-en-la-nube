#!/usr/bin/env python3
"""Prueba de sobreventa contra la API desplegada (Tarea 2 / Flujo 1).

Crea un evento con CUPO lugares y lanza COMPRAS compras simultáneas de 1 boleto.
Resultado esperado: exactamente CUPO respuestas 202, el resto 409, y 0 disponibles.

Uso:  python3 scripts/prueba_carga.py https://xxxx.execute-api.us-east-1.amazonaws.com [cupo] [compras]
Solo usa la biblioteca estándar de Python.
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone


def llamar(api, metodo, ruta, body=None):
    req = urllib.request.Request(f"{api}{ruta}", method=metodo,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    api = sys.argv[1].rstrip("/")
    cupo = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    compras = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    fecha = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    status, evento = llamar(api, "POST", "/eventos", {
        "nombre": f"Prueba de carga {datetime.now():%H:%M:%S}", "lugar": "Laboratorio", "fecha_inicio": fecha,
        "cupo": cupo, "precio": 0, "organizador_email": "prueba@example.com", "pin_staff": "1234"})
    assert status == 201, (status, evento)
    print(f"Evento creado: {evento['evento_id']} (cupo {cupo}). Lanzando {compras} compras simultáneas…")

    def comprar(i):
        return llamar(api, "POST", "/compras", {"compra_id": str(uuid.uuid4()), "evento_id": evento["evento_id"],
                                                "nombre": f"Comprador {i}", "email": f"comprador{i}@example.com",
                                                "cantidad": 1})[0]

    inicio = time.time()
    with ThreadPoolExecutor(max_workers=compras) as pool:
        codigos = Counter(pool.map(comprar, range(compras)))
    _, final = llamar(api, "GET", f"/eventos/{evento['evento_id']}")
    print(f"Tiempo: {time.time() - inicio:.1f} s · Respuestas: {dict(codigos)}")
    print(f"Vendidos: {final['vendidos']} / {final['cupo']} · Disponibles: {final['disponibles']}")
    ok = codigos[202] == cupo and final["vendidos"] == cupo
    print("RESULTADO:", "SIN SOBREVENTA ✔" if ok else "REVISAR ✘")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
