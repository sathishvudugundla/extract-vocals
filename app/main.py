# import os
# import shutil
# import logging
# import gc
# import psutil

# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse, FileResponse
# from starlette.concurrency import run_in_threadpool

# from spleeter.separator import Separator
# import whisper

# # --- Setup ---
# app = FastAPI()

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# VOCALS_OUTPUT_DIR = os.path.join(BASE_DIR, "vocals_output")

# # --- Load Models ---
# separator = Separator('spleeter:2stems')
# logger.info("🎧 Spleeter loaded.")

# whisper_model = whisper.load_model("medium")
# logger.info("🗣️ Whisper model loaded.")

# # --- Helpers ---
# def log_memory_usage():
#     mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
#     logger.info(f"📊 Memory usage: {mem:.2f} MB")

# def cleanup_resources():
#     gc.collect()
#     log_memory_usage()

# # --- Endpoints ---

# @app.get("/")
# def read_root():
#     return {"message": "🎶 Audio service for vocals and lyrics is running."}

# @app.get("/healthz")
# def health():
#     return {"status": "ok"}

# @app.post("/extract-vocals")
# async def extract_vocals(file: UploadFile = File(...)):
#     input_path = os.path.join(BASE_DIR, "temp_input.mp3")
#     os.makedirs(VOCALS_OUTPUT_DIR, exist_ok=True)

#     try:
#         with open(input_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         await run_in_threadpool(
#             separator.separate_to_file,
#             input_path, VOCALS_OUTPUT_DIR, "wav"
#         )

#         vocals_path = os.path.join(VOCALS_OUTPUT_DIR, "temp_input", "vocals.wav")
#         if not os.path.exists(vocals_path):
#             raise FileNotFoundError("Vocals not found after separation")

#         return FileResponse(vocals_path, media_type="audio/wav", filename="vocals.wav")

#     except Exception as e:
#         logger.exception("🚨 Vocal extraction error:")
#         return JSONResponse(status_code=500, content={"error": str(e)})

#     finally:
#         if os.path.exists(input_path):
#             os.remove(input_path)
#         cleanup_resources()

# @app.post("/extract-lyrics")
# async def extract_lyrics(file: UploadFile = File(...)):
#     temp_wav = os.path.join(BASE_DIR, "temp_lyrics.wav")
#     try:
#         with open(temp_wav, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         result = whisper_model.transcribe(temp_wav, language="en")
#         lyrics = result.get("text", "").strip()

#         return JSONResponse({"lyrics": lyrics})

#     except Exception as e:
#         logger.exception("🚨 Lyrics extraction error:")
#         return JSONResponse(status_code=500, content={"error": str(e)})

#     finally:
#         if os.path.exists(temp_wav):
#             os.remove(temp_wav)
#         cleanup_resources()

import os
import shutil
import logging
import gc
import psutil

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from spleeter.separator import Separator
from starlette.concurrency import run_in_threadpool
import whisper

# --- Setup ---
app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOCALS_OUTPUT_DIR = os.path.join(BASE_DIR, "vocals_output")

# --- Load Models ---
separator = Separator('spleeter:2stems')
logger.info("🎧 Spleeter loaded.")

# whisper_model = whisper.load_model("medium")
# whisper_model = whisper.load_model("medium")
whisper_model = whisper.load_model("base")
logger.info("🗣️ Whisper model loaded.")

# --- Helpers ---
def log_memory_usage():
    mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    logger.info(f"📊 Memory usage: {mem:.2f} MB")

def cleanup_resources():
    gc.collect()
    log_memory_usage()

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"message": "🎶 Vocal and lyric extraction service is running."}

@app.get("/healthz")
def health():
    return {"status": "ok"}

@app.post("/extract-vocals")
async def extract_vocals(file: UploadFile = File(...)):
    input_path = os.path.join(BASE_DIR, "temp_input.mp3")
    os.makedirs(VOCALS_OUTPUT_DIR, exist_ok=True)

    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        separator.separate_to_file(input_path, VOCALS_OUTPUT_DIR, codec='wav')

        vocals_path = os.path.join(VOCALS_OUTPUT_DIR, "temp_input", "vocals.wav")
        if not os.path.exists(vocals_path):
            raise FileNotFoundError("Vocals not found after separation")

        return FileResponse(vocals_path, media_type="audio/wav", filename="vocals.wav")

    except Exception as e:
        logger.exception("🚨 Vocal extraction error:")
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        cleanup_resources()

# @app.post("/extract-lyrics")
# async def extract_lyrics(file: UploadFile = File(...)):
#     temp_wav = os.path.join(BASE_DIR, "temp_lyrics.wav")
#     try:
#         with open(temp_wav, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         result = whisper_model.transcribe(temp_wav, language="en")
#         lyrics = result.get("text", "").strip()

#         return JSONResponse({"lyrics": lyrics})

#     except Exception as e:
#         logger.exception("🚨 Lyrics extraction error:")
#         return JSONResponse(status_code=500, content={"error": str(e)})

#     finally:
#         if os.path.exists(temp_wav):
#             os.remove(temp_wav)
#         cleanup_resources()

@app.post("/extract-lyrics")
async def extract_lyrics(file: UploadFile = File(...)):
    temp_wav = os.path.join(BASE_DIR, "temp_lyrics.wav")
    try:
        with open(temp_wav, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run whisper transcription in threadpool
        result = await run_in_threadpool(whisper_model.transcribe, temp_wav, language="en")
        lyrics = result.get("text", "").strip()

        return JSONResponse({"lyrics": lyrics})

    except Exception as e:
        logger.exception("🚨 Lyrics extraction error:")
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        cleanup_resources()