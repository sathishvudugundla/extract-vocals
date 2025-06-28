
import os
import shutil
import logging
import numpy as np
import librosa
import soundfile as sf
import gc
import psutil
import threading

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from starlette.concurrency import run_in_threadpool
import tensorflow as tf
from spleeter.separator import Separator
import whisper


# --- Setup ---
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "instrument_model_cleaned.h5")
VOCALS_OUTPUT_DIR = os.path.join(BASE_DIR, "vocals_output")

# --- Labels ---
labels = ["cel", "cla", "flu", "gac", "gel", "org", "pia", "sax", "tru", "vio", "voi"]
full_labels = {
    "cel": "Cello", "cla": "Clarinet", "flu": "Flute", "gac": "Acoustic Guitar",
    "gel": "Electric Guitar", "org": "Organ", "pia": "Piano", "sax": "Saxophone",
    "tru": "Trumpet", "vio": "Violin", "voi": "Voice"
}

# --- Model Wrapper ---
class ModelWrapper:
    _model = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls):
        with cls._lock:
            if cls._model is None:
                cls._model = tf.keras.models.load_model(MODEL_PATH, compile=False)
                logger.info("✅ Instrument model loaded.")
            return cls._model

# --- Load External Models ---
separator = Separator('spleeter:2stems')
logger.info("🎧 Spleeter loaded.")

whisper_model = whisper.load_model("medium")
logger.info("🗣️ Whisper model loaded.")

# --- Helpers ---
def extract_mfcc(file_path, sr=22050, n_mfcc=13, max_len=1300):
    audio, _ = librosa.load(file_path, sr=sr, mono=True)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)
    if mfcc.shape[1] < max_len:
        pad_width = max_len - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    else:
        mfcc = mfcc[:, :max_len]
    return mfcc

def log_memory_usage():
    mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    logger.info(f"📊 Memory usage: {mem:.2f} MB")

def cleanup_resources():
    gc.collect()
    log_memory_usage()

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "🎶 Multi-task audio server is running."}


@app.post("/predict-instrument")
async def predict_instrument(request: Request, file: UploadFile = File(...)):
    MAX_SIZE_MB = 10
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10MB)")

    temp_filename = os.path.join(BASE_DIR, "temp.wav")
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        log_memory_usage()
        mfcc = extract_mfcc(temp_filename)
        mfcc_flat = mfcc.flatten().reshape(1, -1)

        model = ModelWrapper.get_model()
        prediction = model.predict(mfcc_flat)[0]

        result = {
            full_labels[label]: float(score)
            for label, score in zip(labels, prediction)
            if score >= 0.10
        }

        return JSONResponse({"instruments": result})

    except Exception as e:
        logger.exception("🚨 Prediction error:")
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        cleanup_resources()

# @app.post("/extract-vocals")
# async def extract_vocals(file: UploadFile = File(...)):
#     input_path = os.path.join(BASE_DIR, "temp_input.mp3")
#     os.makedirs(VOCALS_OUTPUT_DIR, exist_ok=True)

#     try:
#         with open(input_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         separator.separate_to_file(input_path, VOCALS_OUTPUT_DIR, codec='wav')

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

@app.post("/extract-vocals")
async def extract_vocals(file: UploadFile = File(...)):
    input_path = os.path.join(BASE_DIR, "temp_input.mp3")
    os.makedirs(VOCALS_OUTPUT_DIR, exist_ok=True)

    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run blocking call in background thread
        await run_in_threadpool(
            separator.separate_to_file,
            input_path,
            VOCALS_OUTPUT_DIR,
            "wav"
        )

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

@app.post("/extract-lyrics")
async def extract_lyrics(file: UploadFile = File(...)):
    temp_wav = os.path.join(BASE_DIR, "temp_lyrics.wav")
    try:
        with open(temp_wav, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = whisper_model.transcribe(temp_wav, language="en")
        lyrics = result.get("text", "").strip()

        return JSONResponse({"lyrics": lyrics})

    except Exception as e:
        logger.exception("🚨 Lyrics extraction error:")
        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        cleanup_resources()
