# models.py
from pydantic import BaseModel

class UserResponseRequest(BaseModel):
    user_response: str
    session_id: str
