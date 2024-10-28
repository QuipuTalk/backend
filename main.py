from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
from httpx import RequestError
from prompts import PROMPTS  # Importar el diccionario de prompts desde otro archivo

load_dotenv()

app = FastAPI()

# Define un modelo para recibir los datos que necesitas del cliente
class Message(BaseModel):
    role: str  # 'user' o 'assistant'
    content: str

class UserRequest(BaseModel):
    user_message: str
    style: str  # formal, informal, neutral
    chat_history: list[Message] = []  # Historial de mensajes para mantener el contexto

# Define una función para conectarse con GPT-4 y obtener las respuestas sugeridas
async def get_gpt4_responses(user_message: str, style: str, chat_history: list[Message]):
    openai_api_key = os.getenv("OPENAI_API_KEY")  # Obtén la API key desde las variables de entorno

    # Verificar si la API Key está presente
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="API Key not found")

    # Si el historial de chat está vacío, agregar el prompt inicial
    if not chat_history:
        prompt = PROMPTS.get(style, PROMPTS["neutral"])
        chat_history.append(Message(role="system", content=prompt))

    # Agregar el mensaje del usuario al historial
    chat_history.append(Message(role="user", content=user_message))

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

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
        )

    # Manejo de la respuesta de la API
    if response.status_code == 200:
        try:
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise HTTPException(status_code=500, detail="Unexpected response format from OpenAI API")
    else:
        raise HTTPException(status_code=response.status_code, detail="Error contacting OpenAI API")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


# Define una nueva ruta para procesar el mensaje del usuario y obtener respuestas sugeridas
@app.post("/get_suggested_replies/")
async def get_suggested_replies(user_request: UserRequest):
    try:
        responses = await get_gpt4_responses(user_request.user_message, user_request.style, user_request.chat_history)
        return {"suggested_replies": responses}
    except RequestError as e:
        raise HTTPException(status_code=503, detail="Service unavailable, could not reach OpenAI API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
