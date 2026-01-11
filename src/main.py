import json
from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar la aplicacion FastAPI
app = FastAPI()

@app.get("/")
def health_check():
    # Endpoint basico para verificar que el servidor responde
    return {"status": "running", "service": "AI Incident Commander"}

@app.websocket("/llm-websocket/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    # Aceptar la conexion entrante de Retell AI
    await websocket.accept()
    
    try:
        # 1. Enviar mensaje de configuracion inicial
        # Esto le dice a Retell que nosotros controlamos la respuesta
        first_event = {
            "response_type": "response",
            "response_id": "initial_greeting",
            "content": "Hola, sistema de incidentes en linea. Esperando instrucciones.",
            "content_complete": True,
            "end_call": False
        }
        await websocket.send_json(first_event)

        # 2. Ciclo principal de la llamada
        # Mantiene la conexion abierta escuchando eventos
        while True:
            data = await websocket.receive_json()
            
            # Si es solo una actualizacion de estado, la ignoramos por ahora
            if data.get("interaction_type") == "update_only":
                continue
            
            # Aqui imprimimos en consola lo que Retell nos envia
            # (Util para depurar y ver que esta pasando)
            print(f"Evento recibido: {data}")

    except Exception as e:
        # Captura cualquier error de desconexion o logica
        print(f"Error en la conexion: {e}")
    finally:
        # Asegura que se reporte el cierre de la llamada
        print("Llamada finalizada")