# AI Incident Commander

Un sistema de respuesta a incidentes automatizado que utiliza IA de voz para gestionar alertas críticas de infraestructura.

## Arquitectura (Fase 1)

```mermaid
graph LR
    User(Tu Celular) --Voz--> Retell[Retell AI]
    Retell --Webhook--> Ngrok[Ngrok Tunnel]
    Ngrok --> LocalAPI[Tu API Python Local]
    LocalAPI --Respuesta--> Retell