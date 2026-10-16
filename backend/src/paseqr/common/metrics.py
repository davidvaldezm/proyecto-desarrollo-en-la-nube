"""Métricas personalizadas con CloudWatch Embedded Metric Format (EMF).

Se escribe un JSON en el log y CloudWatch lo convierte en métrica: no requiere llamadas
a la API ni permisos extra (importante en AWS Academy)."""
import json
import time

NAMESPACE = "PaseQR"


def metrica(nombre: str, valor: float = 1, unidad: str = "Count", **dimensiones) -> None:
    dims = {k: str(v) for k, v in dimensiones.items()}
    print(json.dumps({
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": NAMESPACE,
                "Dimensions": [list(dims)] if dims else [[]],
                "Metrics": [{"Name": nombre, "Unit": unidad}],
            }],
        },
        nombre: valor,
        **dims,
    }))
