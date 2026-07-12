import os
import json
import uvicorn
import uuid  # Добавили импорт для уникальных ID
from datetime import datetime  # Добавили импорт для даты/времени
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

DB_FILE = "db.json"

class SimulationRequest(BaseModel):
    era: str
    original_event: str
    modified_event: str

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"scenarios": []}, f, ensure_ascii=False, indent=4)
            
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- HTTP GET-обработчики ---

@app.get("/")
async def get_index():
    return FileResponse("templates/index.html")

@app.get("/timeline")
async def get_timeline():
    return FileResponse("templates/timeline.html")

@app.get("/gallery")
async def get_gallery():
    return FileResponse("templates/gallery.html")


# --- HTTP POST-обработчик (Обновленный) ---

@app.post("/api/simulate")
async def simulate_butterfly_effect(request: SimulationRequest):
    # 1. Загружаем текущее состояние базы данных
    db = load_db()
    
    # 2. Генерируем ID и временную метку
    scenario_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # 3. Формируем структуру записи (пока с временными заглушками вместо ИИ)
    new_scenario = {
        "id": scenario_id,
        "era": request.era,
        "original_event": request.original_event,
        "modified_event": request.modified_event,
        "generated_text": "Альтернативный таймлайн находится в процессе расчета ИИ...", # Заглушка текста
        "image_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=600", # Заглушка картинки
        "created_at": created_at
    }
    
    # 4. Добавляем новую запись в список сценариев и сохраняем файл
    db["scenarios"].append(new_scenario)
    save_db(db)
    
    # 5. Возвращаем клиенту успешный статус и id созданной записи
    return {
        "status": "success",
        "message": "Сценарий успешно добавлен в базу!",
        "scenario_id": scenario_id
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)