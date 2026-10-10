# generate_news_excel.py
import pandas as pd

data = [
    {
        "title": "2026-yilgi pedagoglar attestatsiyasi namunaviy testlari e'lon qilindi",
        "hashtags": "#matematika #attestatsiya #MS",
        "category": "matematika",
        "summary": "Matematika fani bo'yicha yangi formatdagi test spetsifikatsiyalari va baholash mezonlari tasdiqlandi.",
        "content": "O'zbekiston Respublikasi Maktabgacha va maktab ta'limi vazirligi tomonidan 2026-yilgi attestatsiya sinovlariga oid namunaviy savollar banki taqdim etildi.\n\nUshbu yangi formatda amaliy topshiriqlar hamda fan metodikasiga doir savollar ulushi oshirilgan.",
        "image_url": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800",
        "source_url": "https://t.me/uztdi",
        "source_name": "Ta'lim nazorati rasmiy",
        "discussion_chat_id": -1001234567890  # Guruhingiz ID'si
    }
]

df = pd.DataFrame(data)
df.to_excel("news_template.xlsx", index=False)
print("news_template.xlsx muvaffaqiyatli yaratildi!")