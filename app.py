import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()

# 1. Главная страница (Форма ввода события)
@app.get("/")
async def get_index():
    return FileResponse("templates/index.html")

# 2. Страница отображения таймлайна (Результат)
@app.get("/timeline")
async def get_timeline():
    return FileResponse("templates/timeline.html")

# 3. Страница галереи (Архив созданных миров)
@app.get("/gallery")
async def get_gallery():
    return FileResponse("templates/gallery.html")

# Этот блок позволяет запускать сервер напрямую через запуск файла app.py
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)