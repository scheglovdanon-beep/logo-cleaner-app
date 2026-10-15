FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p input output clean previews reports logs
ENV PORT=8000
EXPOSE 8000
# gunicorn serves the Flask app (src/server.py -> variable `app`)
CMD gunicorn --chdir src --bind 0.0.0.0:$PORT --timeout 120 server:app
