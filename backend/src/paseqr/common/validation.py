"""Validaciones de entrada reutilizables. Acumulan errores para responderlos todos juntos."""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from .http import ApiError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Validador:
    def __init__(self, data: dict):
        self.data = data
        self.errores: dict[str, str] = {}
        self.limpio: dict = {}

    def texto(self, campo, min_len=1, max_len=200, requerido=True):
        valor = self.data.get(campo)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            if requerido:
                self.errores[campo] = "Es obligatorio"
            return self
        if not isinstance(valor, str):
            self.errores[campo] = "Debe ser texto"
            return self
        valor = valor.strip()
        if not min_len <= len(valor) <= max_len:
            self.errores[campo] = f"Debe tener entre {min_len} y {max_len} caracteres"
        else:
            self.limpio[campo] = valor
        return self

    def email(self, campo):
        valor = self.data.get(campo)
        if not isinstance(valor, str) or not EMAIL_RE.match(valor.strip()):
            self.errores[campo] = "Debe ser un correo válido"
        else:
            self.limpio[campo] = valor.strip().lower()
        return self

    def entero(self, campo, minimo, maximo):
        valor = self.data.get(campo)
        if isinstance(valor, bool) or not isinstance(valor, int):
            self.errores[campo] = "Debe ser un número entero"
        elif not minimo <= valor <= maximo:
            self.errores[campo] = f"Debe estar entre {minimo} y {maximo}"
        else:
            self.limpio[campo] = valor
        return self

    def dinero(self, campo, minimo=Decimal("0"), maximo=Decimal("100000")):
        valor = self.data.get(campo)
        try:
            if isinstance(valor, bool):
                raise InvalidOperation
            dec = Decimal(str(valor)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            self.errores[campo] = "Debe ser un monto numérico"
            return self
        if not minimo <= dec <= maximo:
            self.errores[campo] = f"Debe estar entre {minimo} y {maximo}"
        else:
            self.limpio[campo] = dec
        return self

    def fecha_futura(self, campo, ahora: datetime | None = None):
        valor = self.data.get(campo)
        try:
            fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError:
            self.errores[campo] = "Debe ser fecha ISO 8601, ej. 2026-11-20T20:00:00-06:00"
            return self
        if fecha.tzinfo is None:
            self.errores[campo] = "Debe incluir zona horaria"
            return self
        if fecha <= (ahora or datetime.now(timezone.utc)):
            self.errores[campo] = "Debe ser una fecha futura"
            return self
        self.limpio[campo] = fecha.astimezone(timezone.utc).isoformat()
        return self

    def regex(self, campo, patron: str, mensaje: str):
        valor = self.data.get(campo)
        if not isinstance(valor, str) or not re.fullmatch(patron, valor):
            self.errores[campo] = mensaje
        else:
            self.limpio[campo] = valor
        return self

    def resultado(self) -> dict:
        if self.errores:
            raise ApiError(400, "Datos inválidos", self.errores)
        return self.limpio
