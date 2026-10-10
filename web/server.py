import os
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# 1. Avval FastAPI obyektini yaratamiz
app = FastAPI()

# 2. Statik fayllar (home.js va boshqalar) uchun papkani ulaymiz
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# index.html fayliga aniq manzil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(CURRENT_DIR, "templates", "index.html")

# 3. Dinamik yangiliklar bazasi
SAMPLE_NEWS = [
    {
        "id": 1,
        "tag": "Attestatsiya",
        "tag_color": "emerald",
        "date": "10-oktabr",
        "title": "2026-yilgi pedagoglar attestatsiyasi namunaviy testlari yuklandi",
        "desc": "Mutaxassislik fanlari va pedagogik mahorat bo'yicha yangi formatdagi testlar bilan tanishing.",
        "action_tab": "tests",
        "action_text": "Testni ishlash →"
    },
    {
        "id": 2,
        "tag": "Yangi dars",
        "tag_color": "amber",
        "date": "Bugun",
        "title": "7-sinf O'zbekiston tarixi: Yangi videodarslar joylandi",
        "desc": "Amir Temur davlati va harbiy islohotlar mavzusi tushuntirilgan darslar to'plami.",
        "action_tab": "lessons",
        "action_text": "Darslarga o'tish →"
    },
    {
        "id": 3,
        "tag": "Kutubxona",
        "tag_color": "blue",
        "date": "Kecha",
        "title": "Rasmiy attestatsiya qo'llanmasi elektron shaklda",
        "desc": "6-11 sinflar bo'yicha jamlangan to'liq savollar banki nashri chiqdi.",
        "action_tab": "books",
        "action_text": "Kitoblarni ko'rish →"
    }
]

# 4. Sinov uchun savollar to'plami
SAMPLE_QUIZ = {
    "topic": "7-sinf Tarix: Amir Temur davlati",
    "duration_minutes": 15,
    "questions": [
        {
            "id": 1,
            "text": "Amir Temur nechanchi yilda tavallud topgan?",
            "options": ["1336-yil", "1342-yil", "1350-yil", "1370-yil"],
            "correct": 0
        },
        {
            "id": 2,
            "text": "Sohibqiron Amir Temurning otasi kim bo'lgan?",
            "options": ["Amir Qazag'on", "Amir Tarag'ay", "Hoji Barlos", "Mirzo Ulug'bek"],
            "correct": 1
        },
        {
            "id": 3,
            "text": "Amir Temur davlatining dastlabki poytaxti qaysi shahar bo'lgan?",
            "options": ["Buxoro", "Hirot", "Kesh (Shahrisabz)", "Samarqand"],
            "correct": 3
        },
        {
            "id": 4,
            "text": "Amir Temur qachon Movarounnahrning yagona hukmdori deb e'lon qilindi?",
            "options": ["1360-yil", "1370-yil", "1380-yil", "1395-yil"],
            "correct": 1
        },
        {
            "id": 5,
            "text": "Loy jangi qaysi yilda bo'lib o'tgan?",
            "options": ["1365-yil", "1368-yil", "1372-yil", "1390-yil"],
            "correct": 0
        }
    ]
}

# 5. Darslar ro'yxati
SAMPLE_LESSONS = {
    "6": [
        {"id": 601, "title": "1-dars. Qadimgi tosh davri (Paleolit)", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Eng qadimgi odamlar, ilk mehnat qurollari va olovning kashf etilishi haqida umumiy tushuncha."},
        {"id": 602, "title": "2-dars. O'rta tosh davri (Mezolit)", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Kamon va o'qning ixtiro qilinishi, hayvonlarni xonakilashtirishning boshlanishi."}
    ],
    "7": [
        {"id": 701, "title": "1-dars. Amir Temur davlatining tashkil topishi", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Movarounnahr XIV asr o'rtalarida, Amir Temurning hokimiyat tepasiga kelishi."},
        {"id": 702, "title": "2-dars. Amir Temurning harbiy yurishlari", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Amir Temurning davlat chegaralarini mustahkamlashga qaratilgan harbiy yurishlari."}
    ],
    "8": [], "9": [], "10": [], "11": []
}

# 6. Asosiy sahifa (index.html)
@app.get("/", response_class=HTMLResponse)
async def read_root(response: Response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h3>Shablon fayli topilmadi: {TEMPLATE_PATH}</h3>"

# 7. Yangiliklar API
@app.get("/api/news")
async def get_news():
    return SAMPLE_NEWS

# 8. Test API
@app.get("/api/test-data")
async def get_test_data():
    return SAMPLE_QUIZ

# 9. Darslar API
@app.get("/api/lessons/{class_id}")
async def get_lessons_by_class(class_id: str):
    return SAMPLE_LESSONS.get(class_id, [])

# 10. Ishga tushirish bloki (har doim eng oxirida turadi)
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)