from pydantic import BaseModel

# Define un modelo para recibir los datos que necesitas del cliente
class Message(BaseModel):
    role: str  # 'user' o 'assistant'
    content: str

class UserRequest(BaseModel):
    user_message: str
    style: str  # formal, informal, neutral
    session_id: str  # Identificador único para la sesión de chat

class ChangeStyleRequest(BaseModel):
    session_id: str
    new_style: str  # Nuevo estilo: formal, informal, neutral

# Modelo para la solicitud de corrección
class TextCorrectionRequest(BaseModel):
    text: str

