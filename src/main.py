import json
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from groq import Groq
from dotenv import load_dotenv
from .database import create_db_and_tables, save_log

# 1. Cargar variables de entorno
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("ERROR: No se encontro GROQ_API_KEY en el archivo .env")

# 2. Configuracion del ciclo de vida de la aplicacion
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: Crear tablas de base de datos
    create_db_and_tables()
    print("[SISTEMA] Base de datos inicializada correctamente.")
    yield
    # Cierre: (Aqui podrias cerrar conexiones si fuera necesario)

# Inicializar FastAPI con el lifespan configurado
app = FastAPI(lifespan=lifespan)
client = Groq(api_key=GROQ_API_KEY)

# --- Definicion de Herramientas (Tools) ---
def create_ticket(issue_type: str, description: str):
    """
    Simula la creacion de un ticket en el sistema (Jira/ServiceNow).
    """
    print(f"\n[SISTEMA] CREANDO TICKET: {issue_type} - {description}")
    
    # Simulacion de ID de ticket
    ticket_id = f"TICKET-{os.urandom(2).hex().upper()}"
    
    return json.dumps({"ticket_id": ticket_id, "status": "created"})

tools = [
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Crea un ticket de soporte tecnico cuando el usuario reporta un incidente confirmado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "description": "El tipo de problema (ej. 'Server Error', 'Database Down')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripcion breve del problema reportado por el usuario",
                    },
                },
                "required": ["issue_type", "description"],
            },
        },
    }
]

# Prompt del Sistema
SYSTEM_PROMPT = """
Eres el 'Comandante de Incidentes' de una empresa tecnológica.
Tu rol es gestionar reportes de fallos en servidores.
- Eres profesional, calmado y eficiente.
- Tus respuestas deben ser BREVES (máximo 2 oraciones) para conversación telefónica.
- Primero saluda y pregunta cuál es la emergencia.
- Si reportan un error, pregunta por el código de error o la región afectada.
- Al final, di que estás abriendo un ticket en Jira.
"""

@app.websocket("/llm-websocket/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"[CONEXION] Llamada conectada ID: {call_id}")
    
    try:
        while True:
            # Recibir datos de Retell AI
            data = await websocket.receive_text()
            event = json.loads(data)

            # Verificar si se requiere respuesta
            if event["interaction_type"] == "response_required":
                response_id = event["response_id"]
                transcript = event["transcript"]
                
                # Obtener ultimo mensaje del usuario
                user_text = transcript[-1]['content']
                print(f"[USUARIO] {user_text}")

                # Guardar en Base de Datos (Usuario)
                save_log(call_id=call_id, role="user", content=user_text)

                # Enviar respuesta vacia inicial para mantener latencia baja
                await websocket.send_json({
                    "response_id": response_id,
                    "content": "",
                    "content_complete": False,
                    "end_call": False
                })

                # Llamada a Groq (Inferencia)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_text}
                    ],
                    tools=tools,
                    tool_choice="auto", 
                    max_tokens=150
                )

                response_message = completion.choices[0].message
                tool_calls = response_message.tool_calls

                if tool_calls:
                    # Caso A: Uso de Herramienta
                    print("[IA] Ejecutando herramienta...")
                    
                    for tool_call in tool_calls:
                        if tool_call.function.name == "create_ticket":
                            args = json.loads(tool_call.function.arguments)
                            
                            # Ejecucion de la funcion local
                            tool_result = create_ticket(
                                issue_type=args.get("issue_type"), 
                                description=args.get("description")
                            )
                            
                            ticket_data = json.loads(tool_result)
                            final_response = f"Entendido. He generado el reporte con ID {ticket_data['ticket_id']}. El equipo de soporte ya fue notificado."
                            
                            # Guardar en Base de Datos (Herramienta)
                            save_log(call_id=call_id, role="ai_tool", content=final_response)

                            # Enviar audio al usuario
                            await websocket.send_json({
                                "response_id": response_id,
                                "content": final_response,
                                "content_complete": True,
                                "end_call": False
                            })
                            print(f"[IA - TOOL] {final_response}")

                else:
                    # Caso B: Respuesta Conversacional
                    generated_text = response_message.content
                    
                    # Guardar en Base de Datos (IA)
                    save_log(call_id=call_id, role="ai", content=generated_text)

                    # Enviar audio al usuario
                    await websocket.send_json({
                        "response_id": response_id,
                        "content": generated_text,
                        "content_complete": True,
                        "end_call": False
                    })
                    print(f"[IA] {generated_text}")

    except WebSocketDisconnect:
        print("[CONEXION] Llamada finalizada por el usuario")
    except Exception as e:
        print(f"[ERROR] Error critico: {e}")