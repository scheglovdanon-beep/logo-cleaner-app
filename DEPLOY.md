# Деплой дашборда → постоянная ссылка (Render, бесплатно)

## Шаги (5 минут)
1. Залей содержимое этой папки в репозиторий GitHub:
   git init && git add . && git commit -m "logo cleaner"
   git branch -M main
   git remote add origin https://github.com/ТЫ/logo-cleaner.git
   git push -u origin main
2. https://render.com → New → Blueprint → подключить этот репозиторий.
   Render прочитает render.yaml и соберёт из Dockerfile.
3. Apply. Через ~3-5 мин получишь ссылку вида https://logo-cleaner.onrender.com
   — открывается с любого устройства.

## Важно
- Исходные PDF клади в input/.
- Подтверждённые чистые — в clean/ (диск 1 ГБ переживает рестарты).
- Free-план засыпает при простое — первый заход ~30 сек.

## Railway (альтернатива)
Тот же Dockerfile. railway.app → New Project → Deploy from GitHub repo.

## Локально
pip install -r requirements.txt && python src/server.py → http://localhost:8000
