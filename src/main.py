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
    raise ValueError("¡ERROR! No encontré la GROQ_API_KEY en el archivo .env")

# 2. Configurar Clientes
app = FastAPI()
client = Groq(api_key=GROQ_API_KEY)

# 3. El Prompt del Sistema (La personalidad de tu IA)
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
                
                # Obtener el último mensaje del usuario
                user_text = transcript[-1]['content']
                print(f"Usuario dijo: {user_text}")

                # --- NUEVO: Log simple en archivo ---
                with open("call_logs.txt", "a", encoding="utf-8") as log_file:
                    log_file.write(f"[{call_id}] User: {user_text}\n")
                # ------------------------------------

                # Preparar la respuesta vacía inicial
                # (Esto le dice a Retell: "Espera, ya estoy pensando")
                await websocket.send_json({
                    "response_id": response_id,
                    "content": "",
                    "content_complete": False,
                    "end_call": False
                })

                # --- CONECTAR CON LLAMA3.3 (CEREBRO) ---

                stream = client.chat.completions.create(
                    # ANTES DECÍA: model="llama3-8b-8192",
                    # AHORA PON ESTE:
                    model="llama-3.3-70b-versatile", 
                    
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_text}
                    ],
                    stream=True,
                    temperature=0.7,
                    max_tokens=150
                )

                # Mandar cada palabra apenas llegue (Streaming)
                generated_text = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        word = chunk.choices[0].delta.content
                        generated_text += word
                        
                        # Enviar pedacito a Retell
                        await websocket.send_json({
                            "response_id": response_id,
                            "content": word,
                            "content_complete": False,
                            "end_call": False
                        })
                
                print(f"IA respondió: {generated_text}")

                with open("call_logs.txt", "a", encoding="utf-8") as log_file:
                    log_file.write(f"[{call_id}] AI:   {generated_text}\n")
                    log_file.write("-" * 50 + "\n") # Separador bonito

                # Avisar que terminamos de hablar
                await websocket.send_json({
                    "response_id": response_id,
                    "content": "",
                    "content_complete": True,
                    "end_call": False
                })

    except WebSocketDisconnect:
        print("Llamada finalizada por el usuario")
    except Exception as e:
        print(f"Error crítico: {e}")