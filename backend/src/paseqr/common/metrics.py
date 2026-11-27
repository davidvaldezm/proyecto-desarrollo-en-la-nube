"""Métricas personalizadas con CloudWatch Embedded Metric Format (EMF).

Se escribe un JSON en el log y CloudWatch lo convierte en métrica: no requiere llamadas
a la API ni permisos extra (importante en AWS Academy)."""
import json
import time

NAMESPACE = "PaseQR"


def _conjuntos(dims: list[str]) -> list[list[str]]:
    """Publica la métrica total (sin dimensiones), por cada dimensión distinta de evento_id
    (ej. resultado del check-in) y con todas las dimensiones (detalle por evento)."""
    conjuntos = [[]] + [[d] for d in dims if d != "evento_id"]
    if dims and dims not in conjuntos:
        conjuntos.append(dims)
    return conjuntos


def metrica(nombre: str, valor: float = 1, unidad: str = "Count", **dimensiones) -> None:
    dims = {k: str(v) for k, v in dimensiones.items()}
    print(json.dumps({
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": NAMESPACE,
                "Dimensions": _conjuntos(list(dims)),
                "Metrics": [{"Name": nombre, "Unit": unidad}],
            }],
        },
        nombre: valor,
        **dims,
    }))
