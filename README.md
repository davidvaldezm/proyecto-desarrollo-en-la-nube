# PaseQR — Boletos digitales con QR en la nube

Proyecto Integrador · Desarrollo en la Nube · Otoño 2026 · ITESO (Prof. Marcela Rosales)

**PaseQR** es una plataforma serverless en AWS para que organizadores de eventos pequeños y medianos (conciertos universitarios, conferencias, torneos, fiestas) vendan o registren boletos, los entreguen como **PDF con código QR firmado** y validen la entrada en la puerta desde cualquier celular, sin sobreventa ni boletos duplicados.

## Problema

Muchos eventos se organizan con hojas de cálculo, transferencias y listas impresas. Eso provoca sobreventa, boletos falsificados o reutilizados (una captura de pantalla se puede compartir), filas lentas en la entrada y cero datos de asistencia al final. La demanda llega en picos (apertura de preventa, hora de entrada) y el resto del tiempo es casi nula, por eso una arquitectura serverless en la nube es la opción adecuada.

## Flujos end-to-end

| # | Flujo | Resultado observable |
|---|-------|----------------------|
| 1 | **Compra y emisión de boleto**: validación de datos y cupo → escritura condicional en DynamoDB → cola SQS → Lambda genera PDF con QR | Boleto PDF en S3 (descarga con URL prefirmada) + correo vía SNS |
| 2 | **Check-in con QR**: el staff escanea el QR → se valida la firma HMAC, el evento y que no se haya usado | Boleto marcado como `USADO` y contador de asistencia en vivo |
| 3 | **Recordatorios y reporte de asistencia**: EventBridge ejecuta un Lambda programado | Recordatorio 24 h antes por SNS y reporte CSV de asistencia en S3 para el organizador |

## Arquitectura

![Arquitectura](docs/arquitectura.png)

**Servicios de AWS:** Lambda, API Gateway, DynamoDB, S3, SQS, SNS y CloudWatch (más IAM, Secrets Manager y EventBridge Scheduler).

**Stack:** frontend React + Vite (sitio estático en S3) · backend Python 3.12 en Lambda · infraestructura con Terraform · CI/CD con GitHub Actions (pruebas con pytest) · monitoreo con CloudWatch (5 métricas, 2 alarmas, 1 dashboard).

## Equipo

| Integrante | Rol |
|------------|-----|
| David Valdez | Flujo 1 (compra y emisión) + Frontend |
| Vittorio Catino | Flujo 2 (check-in con QR) + CI/CD |
| Juan Pablo Gutiérrez | Flujo 3 (recordatorios y reporte) + Monitoreo |

## Estructura planeada del repositorio

```
frontend/         # React + Vite
backend/          # Lambdas en Python (un módulo por flujo)
  tests/          # pruebas unitarias (pytest)
infra/            # Terraform
.github/workflows # pipeline de CI/CD
docs/             # diagramas y reportes
```

## Estado

Fase 1 — Planteamiento del proyecto (septiembre 2026). Las instrucciones de despliegue se agregarán en la Fase 2.
