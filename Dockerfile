# FROM python:3.10

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     libsndfile1 \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --upgrade pip && pip install -r requirements.txt

# COPY . .

# ENV PORT=8000
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", $PORT]

# FROM python:3.10-slim

# WORKDIR /app

# # # Install system dependencies
# # RUN apt-get update && apt-get install -y \
# #     ffmpeg \
# #     libsndfile1 \
# #     libglib2.0-0 \
# #     libsm6 \
# #     libxrender1 \
# #     libxext6 \
# #     build-essential \
# #     && rm -rf /var/lib/apt/lists/*

# # # Upgrade pip and install numpy before requirements to avoid numba error
# # COPY requirements.txt .
# # RUN pip install --upgrade pip && pip install numpy==1.24.3
# # RUN pip install -r requirements.txt

# # COPY . .

# # ENV PORT=8000

# # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", $PORT]
# FROM tensorflow/tensorflow:2.13.0

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     libsndfile1 \
#     libglib2.0-0 \
#     libsm6 \
#     libxrender1 \
#     libxext6 \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --upgrade pip && pip install -r requirements.txt

# COPY . .

# # ENV PORT=8000

# CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]



FROM python:3.10

WORKDIR /app

# Copy requirements and install dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the app directory
COPY ./app ./app

# Expose the port your FastAPI app is running on
EXPOSE 8080

# Start FastAPI app using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]