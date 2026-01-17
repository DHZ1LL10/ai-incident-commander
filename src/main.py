import json
import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from groq import Groq
from dotenv import load_dotenv

# 1. Cargar la llave secreta
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("ERROR: No encontre la GROQ_API_KEY en el archivo .env")

# 2. Configurar Clientes
app = FastAPI()
client = Groq(api_key=GROQ_API_KEY)

# --- NUEVA FUNCION (HERRAMIENTA) ---
def create_ticket(issue_type: str, description: str):
    """
    Simula la creacion de un ticket en el sistema (Jira/ServiceNow).
    Devuelve un ID de ticket falso.
    """
    print(f"\n[SISTEMA] CREANDO TICKET: {issue_type} - {description}")
    
    # Aqui iria la conexion real a Jira
    ticket_id = f"TICKET-{os.urandom(2).hex().upper()}"
    
    return json.dumps({"ticket_id": ticket_id, "status": "created"})

# 3. El Prompt del Sistema
SYSTEM_PROMPT = """
Eres el 'Comandante de Incidentes' de una empresa tecnológica.
Tu rol es gestionar reportes de fallos en servidores.
- Eres profesional, calmado y eficiente.
- Tus respuestas deben ser BREVES (máximo 2 oraciones) para conversación telefónica.
- Primero saluda y pregunta cuál es la emergencia.
- Si reportan un error, pregunta por el código de error o la región afectada.
- Al final, di que estás abriendo un ticket en Jira.
"""

# --- DEFINICION DE LA HERRAMIENTA PARA GROQ ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Crea un ticket de soporte técnico cuando el usuario reporta un incidente confirmado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "description": "El tipo de problema (ej. 'Server Error', 'Database Down')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripción breve del problema reportado por el usuario",
                    },
                },
                "required": ["issue_type", "description"],
            },
        },
    }
]

@app.websocket("/llm-websocket/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    print(f"Llamada conectada! ID: {call_id}")
    try:
        while True:
            # Recibir mensaje de Retell
            data = await websocket.receive_text()
            event = json.loads(data)

            # Verificar si Retell quiere una respuesta
            if event["interaction_type"] == "response_required":
                response_id = event["response_id"]
                transcript = event["transcript"]
                
                # Obtener el ultimo mensaje del usuario
                user_text = transcript[-1]['content']
                print(f"Usuario dijo: {user_text}")

                # Log simple en archivo
                with open("call_logs.txt", "a", encoding="utf-8") as log_file:
                    log_file.write(f"[{call_id}] User: {user_text}\n")

                # Preparar la respuesta vacia inicial
                await websocket.send_json({
                    "response_id": response_id,
                    "content": "",
                    "content_complete": False,
                    "end_call": False
                })

                # CONECTAR CON LLAMA3.3 (CON TOOLS)
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

                # Verificar si la IA quiere usar una herramienta
                response_message = completion.choices[0].message
                tool_calls = response_message.tool_calls

                if tool_calls:
                    # CASO A: La IA decidio EJECUTAR una funcion
                    print("IA decidio usar una herramienta...")
                    
                    for tool_call in tool_calls:
                        if tool_call.function.name == "create_ticket":
                            # 1. Extraer argumentos
                            args = json.loads(tool_call.function.arguments)
                            
                            # 2. Ejecutar funcion Python
                            tool_result = create_ticket(
                                issue_type=args.get("issue_type"), 
                                description=args.get("description")
                            )
                            
                            # 3. Crear respuesta para el usuario
                            ticket_data = json.loads(tool_result)
                            final_response = f"Entendido. He generado el reporte con ID {ticket_data['ticket_id']}. El equipo de soporte ya fue notificado."
                            
                            # Guardar log de la herramienta
                            with open("call_logs.txt", "a", encoding="utf-8") as log_file:
                                log_file.write(f"[{call_id}] AI (Tool): {final_response}\n")
                                log_file.write("-" * 50 + "\n")

                            # Enviar respuesta de voz
                            await websocket.send_json({
                                "response_id": response_id,
                                "content": final_response,
                                "content_complete": True,
                                "end_call": False
                            })
                            print(f"IA respondio (Tool): {final_response}")

                else:
                    # CASO B: Respuesta normal (Conversacion)
                    generated_text = response_message.content
                    
                    # Guardar log normal
                    with open("call_logs.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(f"[{call_id}] AI: {generated_text}\n")
                        log_file.write("-" * 50 + "\n")

                    # Enviar respuesta de voz
                    await websocket.send_json({
                        "response_id": response_id,
                        "content": generated_text,
                        "content_complete": True,
                        "end_call": False
                    })
                    print(f"IA respondio: {generated_text}")

    except WebSocketDisconnect:
        print("Llamada finalizada por el usuario")
    except Exception as e:
        print(f"Error critico: {e}")