import os
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel
import logging
from prompts import PROMPTS# Importar el diccionario de prompts desde otro archivo
from typing import Dict, List
import uuid

load_dotenv()

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

# Diccionario para almacenar los historiales de chat por sesión
chat_sessions: Dict[str, List[BaseModel]] = {}

# Define un modelo para los mensajes del historial de chat
class Message(BaseModel):
    role: str  # 'user' o 'assistant'
    content: str

# Define una función para conectarse con GPT-4 y obtener las respuestas sugeridas
async def get_gpt4_responses(user_message: str, style: str, session_id: str):
    openai_api_key = os.getenv("OPENAI_API_KEY")  # Obtén la API key desde las variables de entorno

    # Verificar si la API Key está presente
    if not openai_api_key:
        logging.error("API Key not found")
        raise HTTPException(status_code=500, detail="API Key not found")

    # Verificar si el session_id es válido
    if session_id not in chat_sessions:
        logging.error(f"Invalid session_id: {session_id}")
        raise HTTPException(status_code=400, detail="Invalid session_id")

    # Obtener el historial de la sesión
    chat_history = chat_sessions.get(session_id, [])

    # Si el historial de chat está vacío, agregar el prompt inicial solo la primera vez
    if not chat_history:
        prompt = PROMPTS.get(style, PROMPTS["neutral"])
        chat_history.append(Message(role="system", content=prompt))

    # Agregar el mensaje del usuario actual al historial
    chat_history.append(Message(role="user", content=f"[Input]: {user_message}"))

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    # Convertir el historial de mensajes a diccionarios
    messages = [message.dict() for message in chat_history]

    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 300,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
            )
    except httpx.RequestError as exc:
        logging.error(f"An error occurred while requesting OpenAI API: {exc}")
        raise HTTPException(status_code=503, detail="Service unavailable, could not reach OpenAI API")

    # Manejo de la respuesta de la API
    if response.status_code == 200:
        try:
            response_data = response.json()
            assistant_response = response_data["choices"][0]["message"]["content"]
            # Agregar la respuesta del asistente al historial
            chat_history.append(Message(role="assistant", content=assistant_response))
            # Actualizar el historial de la sesión
            chat_sessions[session_id] = chat_history
            return assistant_response
        except (KeyError, IndexError) as e:
            logging.error("Unexpected response format from OpenAI API")
            raise HTTPException(status_code=500, detail="Unexpected response format from OpenAI API")
    else:
        logging.error(f"Error contacting OpenAI API: {response.status_code} {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error contacting OpenAI API")

# utils.py
async def handle_user_response(user_response: str, session_id: str):
    # Verificar si el session_id es válido
    if session_id not in chat_sessions:
        logging.error(f"Invalid session_id: {session_id}")
        raise HTTPException(status_code=400, detail="Invalid session_id")

    # Obtener el historial de la sesión
    chat_history = chat_sessions.get(session_id, [])

    # Agregar la respuesta del usuario al historial
    response_content = f"[El oyente ha respondido/seleccionado]: {user_response}"
    chat_history.append(Message(role="user", content=response_content))

    # Actualizar el historial de la sesión
    chat_sessions[session_id] = chat_history


# Función para crear un nuevo session_id
def create_new_session() -> str:
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = []  # Inicializar la sesión vacía
    return session_id

def update_session_style(session_id: str, new_style: str):
    if session_id not in chat_sessions:
        raise KeyError(f"Session ID {session_id} not found")

    # Obtener el historial de la sesión y modificar el prompt inicial al nuevo estilo
    chat_history = chat_sessions[session_id]

    # Si el historial ya tiene el mensaje del sistema, actualizarlo con el nuevo prompt
    if chat_history and chat_history[0].role == "system":
        new_prompt = PROMPTS.get(new_style, PROMPTS["neutral"])
        chat_history[0] = Message(role="system", content=new_prompt)

    # Actualizar el historial de la sesión
    chat_sessions[session_id] = chat_history
