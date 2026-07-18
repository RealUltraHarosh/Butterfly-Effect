import os
import json
import uuid
import base64
import requests
import uvicorn
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DEEPSEEK_KEY = ""

app = FastAPI()

DB_FILE = "db.json"
STATIC_DIR = "static"

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Обновленная модель запроса от фронтенда
class SimulationRequest(BaseModel):
    history_query: str
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


# --- 1. Сбор контекста из Википедии ---

def get_wikipedia_summary(query: str) -> str:
    """Ищет статью в Википедии и возвращает введение (extract)"""
    search_url = "https://ru.wikipedia.org/w/api.php"
    
    # РЕШЕНИЕ: Википедия требует уникальный User-Agent, иначе блокирует запросы
    headers = {
        "User-Agent": "ButterflyEffectSimulator/1.0 (myproject@example.com)"
    }
    
    # Сначала ищем наиболее точное название статьи
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }
    
    try:
        response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        if response.status_code == 200:
            search_results = response.json()
            search_list = search_results.get("query", {}).get("search", [])
            
            if not search_list:
                return "Исторический факт не найден в базе Википедии."
                
            page_title = search_list[0]["title"]
            
            # Запрашиваем краткое содержание этой статьи
            content_params = {
                "action": "query",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "titles": page_title,
                "format": "json"
            }
            
            content_response = requests.get(search_url, params=content_params, headers=headers, timeout=10)
            if content_response.status_code == 200:
                pages = content_response.json().get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    return page_data.get("extract", "Исторический контекст пуст.")
                    
        print(f"Wikipedia Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Wikipedia Connection Exception: {e}")
        
    return "Не удалось автоматически загрузить историческую справку."


# --- 2. Генерация текста (DeepSeek V4 Flash) ---

def generate_alternative_history(original_context: str, modified: str) -> str:
    """Генерация таймлайна через DeepSeek на основе контекста Википедии"""
    if not DEEPSEEK_KEY:
        return "Ошибка: API-ключ DeepSeek не обнаружен."
        
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_KEY}"
    }
    
    prompt = (
        f"Реальный исторический факт из Википедии:\n{original_context}\n\n"
        f"Вмешательство пользователя в историю: {modified}.\n\n"
        f"На основе этих данных напиши альтернативную историю. Текст должен строго состоять из 4 абзацев, разделенных пустой строкой (без заголовков и нумерации):\n"
        f"Абзац 1: Краткая суть изменений (буквально 1-2 предложения — интрига).\n"
        f"Абзац 2: Кратко о том, что произошло сразу в первые годы после события.\n"
        f"Абзац 3: Кратко о том, как изменился мир через десятилетия.\n"
        f"Абзац 4: Кратко о том, к какому альтернативному настоящему это привело сегодня.\n"
        f"Будь лаконичен, пиши интересно на русском языке."
    )
    
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "Ты — профессиональный историк и футуролог."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"DeepSeek Error: {response.status_code} - {response.text}")
            return "Не удалось сгенерировать историю из-за сбоя API DeepSeek."
    except Exception as e:
        print(f"DeepSeek Exception: {e}")
        return "Произошла непредвиденная ошибка при подключении к ИИ."

def generate_image_prompt_with_deepseek(story_text: str, history_query: str) -> str:
    """Просит DeepSeek написать детальный промпт для картинки на основе истории"""
    if not DEEPSEEK_KEY:
        return f"A cinematic digital painting about {history_query}."
        
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_KEY}"
    }
    
    # Даем ИИ жесткую инструкцию по избеганию бород и созданию кинематографичности
    prompt = (
        f"Based on this alternate history query '{history_query}' and the story: '{story_text}', "
        f"write a highly detailed visual prompt for an AI image generator (like FLUX) in English. "
        f"Describe one key dramatic scene in detail (composition, camera angle, atmospheric lighting, colors). "
        f"CRITICAL INSTRUCTION: If there are men in the scene, explicitly describe them as 'clean-shaven, young/modern look' "
        f"to avoid the AI's default bias towards giving everyone historical beards, unless a beard is strictly historically accurate. "
        f"Style: Cinematic film still, highly realistic, dramatic volumetric lighting. "
        f"Keep the prompt strictly to a single paragraph under 70 words. Do not write any introduction, markdown, or chat, just the prompt itself."
    )
    
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "You are an expert AI prompt engineer for Midjourney and FLUX. You only output the raw English prompt string."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            ai_prompt = response.json()["choices"][0]["message"]["content"]
            print(f"=== СГЕНЕРИРОВАННЫЙ ИИ ПРОМПТ ===\n{ai_prompt}\n=================================")
            return ai_prompt.strip()
    except Exception as e:
        print(f"Ошибка при генерации промпта через DeepSeek: {e}")
        
    # Запасной простой промпт, если ИИ сбоит
    return f"Cinematic historical drama photograph, depicting {history_query}, realistic, dramatic lighting."

# --- 3. Генерация картинки (Nano Banana 2 / Gemini 3.1 Flash Image) ---
        
import urllib.parse  # Убедитесь, что этот импорт есть в самом верху app.py

def generate_nano_banana_image(scenario_id: str, ai_generated_prompt: str) -> str:
    """Генерация картинки по готовому промпту от DeepSeek"""
    encoded_prompt = urllib.parse.quote(ai_generated_prompt)
    
    # Делаем запрос к FLUX с промптом от DeepSeek
    url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=768&seed=42&nologo=true&model=flux"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            file_name = f"{scenario_id}.png"
            file_path = os.path.join(STATIC_DIR, file_name)
            
            with open(file_path, "wb") as f:
                f.write(response.content)
                
            print(f"Картинка успешно сохранена: {file_path}")
            return f"/static/{file_name}"
    except Exception as e:
        print(f"Ошибка при работе с FLUX: {e}")
        
    return "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=600"


# --- HTTP GET-ОБРАБОТЧИКИ ---

@app.get("/")
async def get_index():
    return FileResponse("templates/index.html")

@app.get("/timeline")
async def get_timeline():
    return FileResponse("templates/timeline.html")

@app.get("/gallery")
async def get_gallery():
    return FileResponse("templates/gallery.html")


# --- API ЭНДПОИНТЫ ---

@app.post("/api/simulate")
async def simulate_butterfly_effect(request: SimulationRequest):
    db = load_db()
    scenario_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # 1. Поиск в Википедии
    wiki_context = get_wikipedia_summary(request.history_query)
    
    # 2. Генерация истории (DeepSeek)
    generated_text = generate_alternative_history(
        original_context=wiki_context, 
        modified=request.modified_event
    )
    
    # 3. НОВОЕ: Просим DeepSeek написать идеальный промпт для картинки на основе истории
    ai_image_prompt = generate_image_prompt_with_deepseek(
        story_text=generated_text, 
        history_query=request.history_query
    )
    
    # 4. Передаем этот ИИ-промпт во FLUX
    image_url = generate_nano_banana_image(
        scenario_id=scenario_id,
        ai_generated_prompt=ai_image_prompt # Передаем сгенерированный промпт
    )
    
    # 5. Сохраняем в базу данных
    new_scenario = {
        "id": scenario_id,
        "era": request.history_query,
        "original_event": wiki_context,
        "modified_event": request.modified_event,
        "generated_text": generated_text,
        "image_url": image_url,
        "created_at": created_at
    }
    
    db["scenarios"].append(new_scenario)
    save_db(db)
    
    return {
        "status": "success",
        "message": "Временная линия успешно изменена!",
        "scenario_id": scenario_id
    }

@app.get("/api/scenario/{scenario_id}")
async def get_scenario(scenario_id: str):
    db = load_db()
    for scenario in db["scenarios"]:
        if scenario["id"] == scenario_id:
            return scenario
    raise HTTPException(status_code=404, detail="Сценарий не найден")

# --- API эндпоинт для получения ВСЕХ сценариев ---
@app.get("/api/scenarios")
async def get_all_scenarios():
    db = load_db()
    # Возвращаем список сценариев в обратном порядке (новые сверху)
    return db.get("scenarios", [])[::-1]


# --- API эндпоинт для удаления сценария по ID ---
@app.delete("/api/scenario/{scenario_id}")
async def delete_scenario(scenario_id: str):
    db = load_db()
    scenarios = db.get("scenarios", [])
    
    # Фильтруем список, оставляя все сценарии, кроме удаляемого
    updated_scenarios = [s for s in scenarios if s["id"] != scenario_id]
    
    # Если размер списка не изменился, значит сценарий не был найден
    if len(scenarios) == len(updated_scenarios):
        raise HTTPException(status_code=404, detail="Сценарий для удаления не найден")
        
    db["scenarios"] = updated_scenarios
    save_db(db)
    
    return {"status": "success", "message": "Сценарий успешно удален из хроник"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)