from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from httpx import RequestError
from utils import (
    get_gpt4_responses,
    chat_sessions,
    create_new_session,
    update_session_style,
    handle_user_response,
    get_corrected_text
)
#from translation_utils import (
#    image_process,
#    keypoint_extraction
#)

from request_utils import (
    UserRequest,
    ChangeStyleRequest,
    Message,
    TextCorrectionRequest
)

import logging
from models import UserResponseRequest  # Necesitarás crear este modelo

#Importaciones para el modelo
#import mediapipe as mp
#import cv2
#import numpy as np
#import tempfile
#import shutil
#from keras.api.models import load_model
#import os

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logging.info("FastAPI app is running")



#Caragar el modelo al iniciar la aplicación
#model = load_model('eight_words_good.h5')
#actions = np.array(['kilogramo', 'pagar', 'por favor','querer','tomate','uno','yape','yo'])  # Reemplaza con tus acciones reales
#mp_holistic = mp.solutions.holistic
#holistic = mp_holistic.Holistic(min_detection_confidence=0.75, min_tracking_confidence=0.75)



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

# main.py

from prompts import CORRECTION_GRAMMAR_PROMPT  # Asegúrate de importar el prompt


# Nuevo endpoint para corregir el texto
@app.post("/get_text_correction/")
async def get_text_correction(request: TextCorrectionRequest):
    try:
        corrected_text = await get_corrected_text(request.text)
        return JSONResponse(
            content={"corrected_text": corrected_text},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error al procesar la corrección de texto: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

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



# Nuevo endpoint para traducir el video
#@app.post("/translate_video/")
#async def translate_video(video: UploadFile = File(...)):
#    # Guardar el video temporalmente
#    try:
#        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
#            shutil.copyfileobj(video.file, tmp)
#            tmp_path = tmp.name
#
#        # Abrir el video con OpenCV
#        cap = cv2.VideoCapture(tmp_path)
#        if not cap.isOpened():
#            return {"error": "No se puede procesar el video."}
#
#        sentence, keypoints_sequence, last_prediction = [], [], ''
#        while True:
#            ret, frame = cap.read()
#            if not ret:
#                break
#
#            # Procesar el frame
#            results = image_process(frame, holistic)
#            keypoints = keypoint_extraction(results)
#            keypoints_sequence.append(keypoints)
#
#            if len(keypoints_sequence) == 10:
#                keypoints_array = np.array(keypoints_sequence)
#                prediction = model.predict(keypoints_array[np.newaxis, :, :])
#                keypoints_sequence = []
#
#                if np.amax(prediction) > 0.9:
#                    predicted_action = actions[np.argmax(prediction)]
#                    if last_prediction != predicted_action:
#                        sentence.append(predicted_action)
#                        last_prediction = predicted_action
#
#                if len(sentence) > 7:
#                    sentence = sentence[-7:]
#
#        cap.release()
#        os.remove(tmp_path)  # Eliminar el archivo temporal
#
#        translation = ' '.join(sentence)
#        return {"translation": translation}
#
#    except Exception as e:
#        logging.error(f"Error al procesar el video: {e}")
#        raise HTTPException(status_code=500, detail="Error al procesar el video")