from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from httpx import RequestError
from utils import get_gpt4_responses, chat_sessions, create_new_session, update_session_style
import logging
from models import UserResponseRequest  # Necesitarás crear este modelo

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logging.info("FastAPI app is running")

# Define un modelo para recibir los datos que necesitas del cliente
class Message(BaseModel):
    role: str  # 'user' o 'assistant'
    content: str

class UserRequest(BaseModel):
    user_message: str
    style: str  # formal, informal, neutral
    session_id: str  # Identificador único para la sesión de chat
    user_response: str = None  # Respuesta seleccionada o personalizada por el usuario (opcional)

class ChangeStyleRequest(BaseModel):
    session_id: str
    new_style: str  # Nuevo estilo: formal, informal, neutral


@app.get("/")
def read_root():
    return {"message": "Server is up and running!"}

@app.get("/hello_world/")
async def hello_world():
    return {"message": "Hello World"}

@app.get("/start_session/")
async def start_session():
    session_id = create_new_session()
    return {"session_id": session_id}

# Define una nueva ruta para procesar el mensaje del usuario y obtener respuestas sugeridas
from fastapi.responses import JSONResponse

@app.post("/get_suggested_replies/")
async def get_suggested_replies(user_request: UserRequest):
    try:
        responses = await get_gpt4_responses(user_request.user_message, user_request.style, user_request.session_id)
        return JSONResponse(
            content={"suggested_replies": responses},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except RequestError:
        raise HTTPException(status_code=503, detail="Service unavailable, could not reach OpenAI API")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/send_user_response/")
async def send_user_response(user_response_request: UserResponseRequest):
    try:
        await handle_user_response(user_response_request.user_response, user_response_request.session_id)
        return JSONResponse(
            content={"status": "success"},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Endpoint para obtener el historial de la conversación
@app.get("/get_chat_history/{session_id}")
async def get_chat_history(session_id: str):
    if session_id not in chat_sessions:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    return {"chat_history": [message.dict() for message in chat_sessions[session_id]]}

# Endpoint para cambiar el estilo de una sesión activa
@app.post("/change_style/")
async def change_style(request: ChangeStyleRequest):
    try:
        update_session_style(request.session_id, request.new_style)
        return {"message": f"Style updated to {request.new_style} for session {request.session_id}"}
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

