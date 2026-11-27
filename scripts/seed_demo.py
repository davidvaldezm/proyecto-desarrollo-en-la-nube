#!/usr/bin/env python3
"""Prueba de humo + datos de demo. Lo ejecuta deploy.sh al final de cada despliegue.

1. Verifica que la API responda (GET /eventos -> 200). Si no, termina con error y el
   pipeline falla.
2. Si no hay eventos (cuenta recién creada), crea eventos de ejemplo para el demo.

Uso: python3 scripts/seed_demo.py <API_URL>    (correo del organizador: DEMO_EMAIL)
"""
import json
import os
import sys
import urllib.error
import urllib.request
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
    status, data = llamar(api, "GET", "/eventos")
    if status != 200:
        print(f"Prueba de humo FALLÓ: GET /eventos -> {status} {data}")
        sys.exit(1)
    print(f"Prueba de humo OK: GET /eventos -> 200 ({len(data['eventos'])} eventos)")
    if data["eventos"]:
        return

    ahora = datetime.now(timezone.utc)
    correo = os.environ.get("DEMO_EMAIL") or "organizador@example.com"
    demo = [
        ("Concierto de bienvenida ITESO", "Bandas estudiantiles y DJ invitado.", "Auditorio Pedro Arrupe, ITESO", 7, 200, 150),
        ("Torneo de e-sports Otoño 2026", "Final de Smash y Rocket League.", "Biblioteca Dr. Jorge Villalobos, sala 3", 14, 60, 0),
        ("Conferencia: Arquitecturas serverless", "Charla técnica sobre AWS Lambda y DynamoDB.", "Edificio T, aula magna", 21, 120, 50),
    ]
    for nombre, desc, lugar, dias, cupo, precio in demo:
        fecha = (ahora + timedelta(days=dias)).replace(hour=2, minute=0, second=0, microsecond=0).isoformat()
        status, ev = llamar(api, "POST", "/eventos", {
            "nombre": nombre, "descripcion": desc, "lugar": lugar, "fecha_inicio": fecha, "cupo": cupo,
            "precio": precio, "organizador_email": correo, "pin_staff": "2468"})
        print(f"  evento demo {'creado' if status == 201 else f'ERROR {status}'}: {nombre}")


if __name__ == "__main__":
    main()
