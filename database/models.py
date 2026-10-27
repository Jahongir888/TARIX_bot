from datetime import datetime, date
from sqlalchemy import (Column, Integer, BigInteger, String, Boolean, Float, Text, ForeignKey, DateTime, Date, UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


# ==========================================================
# 1. FOYDALANUVCHILAR JADVALI (USER)
# ==========================================================
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    phone_number = Column(String, unique=True, nullable=True)
    secondary_phone = Column(String, nullable=True)  # Bog'lanish uchun qo'shimcha raqam
    region = Column(String, nullable=True)  # Viloyat
    district = Column(String, nullable=True)  # Tuman
    avatar_url = Column(String, nullable=True)  # Profil rasmi / avatar
    birth_date = Column(String, nullable=True, default="Tanlanmagan")

    target = Column(String, nullable=True)  # Abituriyent, Attestatsiya, Noldan
    selected_subject = Column(String, default="tarix")  # Asosiy yo'nalish
    balance = Column(Integer, default=0)  # Balans (so'mda)
    coins = Column(Integer, default=0)  # Profil balansi (Coinlarda)
    is_paid = Column(Boolean, default=False)  # Obuna holati
    is_subscribed = Column(Boolean, default=False)  # Faol pullik obunasi bormi (ism yonidagi belgi uchun)

    device_count = Column(Integer, default=1)  # Faol qurilmalar soni
    status_abc = Column(String, default="CCC")  # 3 ta harf: [Sertifikat, Jang, Kurs]

    # Profil yangi funksiyalari
    invited_friends_count = Column(Integer, default=0)  # Do'stlarni taklif qilish (max 10 ta)
    oferta_accepted = Column(Boolean, default=False)  # Oferta imzolanganlik holati (+coin uchun)
    total_active_seconds = Column(Integer, default=0)  # Platformada o'tkazilgan jami soniyalar

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    progress = relationship("UserProgress", back_populates="user")
    orders = relationship("BookOrder", back_populates="user")
    news_reactions = relationship("NewsReaction", back_populates="user")
    news_comments = relationship("NewsComment", back_populates="user")
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    certificates = relationship("UserCertificate", back_populates="user", cascade="all, delete-orphan")
    mistakes = relationship("MistakeBank", back_populates="user", cascade="all, delete-orphan")
    referrals = relationship("ReferralEarning", back_populates="inviter", cascade="all, delete-orphan")

    # Yangi munosabatlar
    coin_transactions = relationship("CoinTransaction", back_populates="user", cascade="all, delete-orphan")
    daily_activities = relationship("UserDailyActivity", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    supervisors = relationship(
        "UserSupervisor",
        foreign_keys="UserSupervisor.student_tg_id",
        primaryjoin="User.telegram_id == UserSupervisor.student_tg_id",
        back_populates="student",
        cascade="all, delete-orphan"
    )


# ==========================================================
# 2. XAVFSIZLIK VA QURILMALAR NAZORATI
# ==========================================================
class UserDevice(Base):
    __tablename__ = 'user_devices'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    device_name = Column(String, nullable=False)  # iPhone 14, Samsung Galaxy S23, Chrome PC
    device_ip = Column(String, nullable=True)
    last_login = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")


# ==========================================================
# 3. BALANS VA TRANZAKSIYALAR TARIXI (COIN / SO'M)
# ==========================================================
class CoinTransaction(Base):
    __tablename__ = 'coin_transactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    amount = Column(Integer, nullable=False)  # +10 yoki -5
    tx_type = Column(String, nullable=False)  # "referral", "oferta", "buy", "topup"
    description = Column(String, nullable=False)  # Qisqa izoh
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="coin_transactions")


# ==========================================================
# 4. KUNLIK FAOLLIK DIAGRAMMASI
# ==========================================================
class UserDailyActivity(Base):
    __tablename__ = 'user_daily_activity'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    activity_date = Column(Date, default=date.today)
    seconds_spent = Column(Integer, default=0)  # Kun davomida sarflangan soniyalar

    user = relationship("User", back_populates="daily_activities")


# ==========================================================
# 5. ARIZA VA TAKLIFLAR (FEEDBACK)
# ==========================================================
class UserFeedback(Base):
    __tablename__ = 'user_feedbacks'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    category = Column(String, default="taklif")  # taklif, ariza, shikoyat
    message = Column(Text, nullable=False)
    admin_rewarded = Column(Boolean, default=False)  # Coin berilganmi
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedbacks")


# ==========================================================
# 6. DO'STLAR VA IJTIMOIY TIZIM
# ==========================================================
class UserFriend(Base):
    __tablename__ = 'user_friends'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    friend_telegram_id = Column(BigInteger, nullable=False)
    friend_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================================
# 7. SERTIFIKATLAR (PLATFORMA VA HAQIQIY)
# ==========================================================
class UserCertificate(Base):
    __tablename__ = 'user_certificates'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    cert_type = Column(String, default="platforma")  # "platforma" yoki "haqiqiy"
    title = Column(String, nullable=False)  # Kurs nomi yoki Milliy sertifikat
    pdf_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    score_or_level = Column(String, nullable=True)  # Masalan: "A+", "B2", "86%"
    is_verified = Column(Boolean, default=False)  # Admin tasdiqlaganmi
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="certificates")


# ==========================================================
# 8. DARSLAR VA INTERAKTIV VIDEO PLEYER
# ==========================================================
class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    subject = Column(String, default="tarix")
    class_level = Column(String, nullable=False)  # 6, 7, 8...
    order_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    is_free = Column(Boolean, default=False)

    summary_text = Column(Text, nullable=True)  # Ma'ruza matni (konspekt)
    timecodes = Column(Text, nullable=True)  # JSON/matn
    fill_blank_task = Column(Text, nullable=True)  # Bo'sh joylarni to'ldirish topshirig'i

    pause_questions = relationship("LessonPauseQuestion", back_populates="lesson", cascade="all, delete-orphan")


class LessonPauseQuestion(Base):
    __tablename__ = 'lesson_pause_questions'

    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    pause_second = Column(Integer, nullable=False)  # Video to'xtaydigan sekund
    question_text = Column(String, nullable=False)
    options = Column(Text, nullable=False)  # Variantlar
    correct_option = Column(Integer, nullable=False)  # Indeks (0, 1, 2, 3)
    feedback_text = Column(Text, nullable=True)  # Tushuntirish

    lesson = relationship("Lesson", back_populates="pause_questions")


# ==========================================================
# 9. HISTOMAP (TARIX FANIDAN INTERAKTIV XARITA)
# ==========================================================
class HistoMapCountry(Base):
    __tablename__ = 'histomap_countries'

    id = Column(Integer, primary_key=True)
    country_name = Column(String, nullable=False)
    era = Column(String, nullable=False)
    region = Column(String, nullable=True)
    map_coordinates = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)


# ==========================================================
# 10. OKTAGON / BATTLE (JONLI DUEL JANGI)
# ==========================================================
class Battle(Base):
    __tablename__ = 'battles'

    id = Column(Integer, primary_key=True)
    battle_code = Column(String, unique=True, nullable=False)
    subject = Column(String, default="tarix")
    topic = Column(String, nullable=True)
    is_against_bot = Column(Boolean, default=False)
    status = Column(String, default="kutish")

    winner_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship("BattleParticipant", back_populates="battle", cascade="all, delete-orphan")


class BattleParticipant(Base):
    __tablename__ = 'battle_participants'

    id = Column(Integer, primary_key=True)
    battle_id = Column(Integer, ForeignKey('battles.id'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    score = Column(Integer, default=0)
    reaction_sticker = Column(String, nullable=True)

    battle = relationship("Battle", back_populates="participants")


# ==========================================================
# 11. TEST NATIJALARI VA XATOLAR BANKI
# ==========================================================
class UserProgress(Base):
    __tablename__ = 'user_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    test_title = Column(String, nullable=False)
    raw_score = Column(Integer)
    percentage = Column(Float)
    theta_ability = Column(Float, nullable=True)  # Rasch bali
    completed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")


class MistakeBank(Base):
    __tablename__ = 'mistake_bank'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    subject = Column(String, default="tarix")
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)
    user_wrong_answer = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="mistakes")


# ==========================================================
# 12. KITOBLAR VA BUYURTMALAR
# ==========================================================
class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    subject = Column(String, default="tarix")
    title = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    book_type = Column(String, default="elektron")
    pdf_url = Column(String, nullable=True)
    cover_image_url = Column(String, nullable=True)
    has_attached_tests = Column(Boolean, default=False)


class BookOrder(Base):
    __tablename__ = 'book_orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    book_title = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    shipping_address = Column(String, nullable=False)
    status = Column(String, default="yangi")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")


# ==========================================================
# 13. REFERAL TIZIMI
# ==========================================================
class ReferralEarning(Base):
    __tablename__ = 'referral_earnings'

    id = Column(Integer, primary_key=True)
    inviter_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    referred_user_id = Column(BigInteger, nullable=False)
    bonus_amount = Column(Integer, default=0)
    is_paid_out = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inviter = relationship("User", back_populates="referrals")


# ==========================================================
# 14. YANGILIKLAR (NEWS) JADVALI (REAKSIYALAR HISOBI BILAN)
# ==========================================================
class News(Base):
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    hashtags = Column(String, nullable=False)
    category = Column(String, default="umumiy")
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    source_name = Column(String, default="Manba")
    views_count = Column(Integer, default=0)

    # Har bir reaksiya turining jami sonini hisoblab turuvchi ustunlar:
    likes_count = Column(Integer, default=0)              # 👍 soni
    hearts_count = Column(Integer, default=0)             # ❤️ soni
    fires_count = Column(Integer, default=0)              # 🔥 soni
    ideas_count = Column(Integer, default=0)              # 💡 soni

    discussion_chat_id = Column(BigInteger, nullable=True)
    telegram_post_msg_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reactions = relationship("NewsReaction", back_populates="news", cascade="all, delete-orphan")
    comments = relationship("NewsComment", back_populates="news", cascade="all, delete-orphan")


class NewsReaction(Base):
    __tablename__ = 'news_reactions'

    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, ForeignKey('news.id'))
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    reaction = Column(String, nullable=False)             # 'like', 'heart', 'fire', 'idea'

    news = relationship("News", back_populates="reactions")
    user = relationship("User", back_populates="news_reactions")


class NewsComment(Base):
    __tablename__ = 'news_comments'

    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, ForeignKey('news.id'))
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    user_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    news = relationship("News", back_populates="comments")
    user = relationship("User", back_populates="news_comments")

class ExamEvent(Base):
    __tablename__ = 'exam_events'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)                  # Masalan: "Tarix fanidan Milliy Sertifikat"
    subject = Column(String, default="tarix")              # tarix, umumiy
    target_date = Column(DateTime, nullable=False)          # Qolgan vaqt hisoblanadigan sana
    badge_label = Column(String, default="BMBA")           # BMBA, Attestatsiya
    action_url = Column(String, default="https://my.uzbmb.uz")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================================
# BILDIRISHNOMALAR MODELI (NOTIFICATIONS)
# ==========================================================
class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=True)             # Maxsus foydalanuvchi uchun (None bo'lsa - barchaga)
    source = Column(String, nullable=False)                 # oktagon, testlar, elonlar, kurslar, tolov, qurilmalar
    title = Column(String, nullable=False)                  # Masalan: "Oktagon: Yangi Jang Chaqirig'i!"
    message = Column(Text, nullable=False)                  # Xabar mazmuni
    target_tab = Column(String, default="home")             # Bosganda o'tadigan bo'lim: oktagon, tests, home, lessons, profile
    is_read = Column(Boolean, default=False)                # O'qilgan/o'qilmaganlik holati
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================================
# O'QUVCHI O'QUV SUR'ATI VA PROGRESSI (COURSE PACE)
# ==========================================================
class UserCoursePace(Base):
    __tablename__ = 'user_course_pace'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)  # Telegram ID
    course_code = Column(String, nullable=False)  # Masalan: "hist_7", "ms_hist"
    course_title = Column(String, nullable=False)  # "7-sinf O'zbekiston tarixi"
    target_tab = Column(String, default="lessons")  # Bosilganda o'tadigan tab

    # Progress foizlari (0 dan 100 gacha)
    actual_progress = Column(Integer, default=0)  # O'quvchi o'qigan qismi (Yashil)
    expected_progress = Column(Integer, default=0)  # Bugungi kunda bo'lishi kerak bo'lgan reja (Qizil chegara)

    # Status: Shogird (0-50%), Bilimdon (51-85%), Ustoz (86-100%)
    status_label = Column(String, default="Shogird")
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

# ==========================================================
# OKTAGON (PVP BELLASHUV) STATISTIKASI VA REYTINGI
# ==========================================================
class UserOctagonProfile(Base):
    __tablename__ = 'user_octagon_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)  # Telegram ID
    current_course = Column(String, default="7-sinf Tarix")   # Hozir o'qiyotgan kursi
    subject_focus = Column(String, default="tarix", index=True)  # Faol fan
    region = Column(String, nullable=True, index=True)        # Reyting filtri uchun hudud
    rank_position = Column(Integer, default=12)              # Shu kurs bo'yicha o'rni
    total_battles = Column(Integer, default=0)               # Umumiy janglar soni
    victories = Column(Integer, default=0)                   # G'alabalar soni
    rating_points = Column(Integer, default=1000)            # Reyting balli
    subscription_tier = Column(String, default="free")       # free | pro | premium (stikerlar)
    last_seen_at = Column(DateTime, nullable=True)           # Onlayn holat (heartbeat)
    updated_at = Column(DateTime, default=datetime.utcnow)

    created_battles = relationship(
        "OctagonBattle",
        foreign_keys="OctagonBattle.creator_id",
        primaryjoin="UserOctagonProfile.user_id == OctagonBattle.creator_id",
        viewonly=True,
    )
    joined_battles = relationship(
        "OctagonBattle",
        foreign_keys="OctagonBattle.opponent_id",
        primaryjoin="UserOctagonProfile.user_id == OctagonBattle.opponent_id",
        viewonly=True,
    )


# ==========================================================
# OKTAGON JANG XONALARI (DUEL / BOT / JONLI PVP)
# ==========================================================
class OctagonBattle(Base):
    __tablename__ = 'octagon_battles'

    id = Column(Integer, primary_key=True)
    room_code = Column(String, unique=True, nullable=False, index=True)
    creator_id = Column(BigInteger, nullable=False, index=True)
    opponent_id = Column(BigInteger, nullable=True, index=True)
    is_bot = Column(Boolean, default=False)

    subject = Column(String, default="tarix", index=True)
    level = Column(String, default="orta", index=True)       # oson | orta | qiyin
    topic = Column(String, nullable=True)

    # waiting | active | finished | expired | cancelled
    status = Column(String, default="waiting", index=True)
    expires_at = Column(DateTime, nullable=False)            # Taklif muddati (60 sekund)

    creator_score = Column(Integer, default=0)
    opponent_score = Column(Integer, default=0)
    creator_correct = Column(Integer, default=0)
    creator_wrong = Column(Integer, default=0)
    opponent_correct = Column(Integer, default=0)
    opponent_wrong = Column(Integer, default=0)
    winner_id = Column(BigInteger, nullable=True)            # None = durang; bot g'alabasi: 0

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    analyses = relationship(
        "OctagonBattleAnalysis",
        back_populates="battle",
        cascade="all, delete-orphan",
    )
    reactions = relationship(
        "OctagonBattleReaction",
        back_populates="battle",
        cascade="all, delete-orphan",
    )


class OctagonBattleAnalysis(Base):
    __tablename__ = 'octagon_battle_analyses'

    id = Column(Integer, primary_key=True)
    battle_id = Column(Integer, ForeignKey('octagon_battles.id'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)

    topic_name = Column(String, nullable=False)              # Xato qilingan mavzu
    questions_total = Column(Integer, default=0)
    mistakes_count = Column(Integer, default=0)
    mastery_percent = Column(Float, default=0.0)             # O'zlashtirish foizi

    recommended_course_id = Column(Integer, nullable=True)
    recommended_course_title = Column(String, nullable=True)
    recommended_course_link = Column(String, nullable=True)  # Mini App ichki havola / tab

    battle = relationship("OctagonBattle", back_populates="analyses")


class OctagonBattleReaction(Base):
    __tablename__ = 'octagon_battle_reactions'

    id = Column(Integer, primary_key=True)
    battle_id = Column(Integer, ForeignKey('octagon_battles.id'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    emoji = Column(String, nullable=False)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    battle = relationship("OctagonBattle", back_populates="reactions")

# ==========================================================
# REKLAMA VA AKSIYALAR MODELI (PROMOTIONS / BUNDLES)
# ==========================================================
class Promotion(Base):
    __tablename__ = 'promotions'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)                  # Masalan: "SUPER AKSIYA: 2 tasi 1 da!"
    subtitle = Column(String, nullable=True)                # "Tarix noldan + Harbiy psixologiya"
    badge_label = Column(String, default="AKSIYA -50%")     # Vidjet burchagidagi nishon
    original_price = Column(Integer, nullable=True)         # Asl narxi: 150 000
    discount_price = Column(Integer, nullable=False)        # Aksiya narxi: 50 000
    end_date = Column(DateTime, nullable=False)             # Aksiya tugash vaqti (taymer uchun)
    target_tab = Column(String, default="books")            # Bosilganda o'tadigan bo'lim: books, lessons, tests
    action_btn_text = Column(String, default="Xarid qilish") # Tugma matni
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================================
# PLATFORMA STATISTIKASI MODELI (PLATFORM METRICS)
# ==========================================================
class PlatformStats(Base):
    __tablename__ = 'platform_stats'

    id = Column(Integer, primary_key=True)
    students_count = Column(Integer, default=1250)      # Faol o'quvchilar soni
    lessons_count = Column(Integer, default=180)        # Jami darslar/kurslar
    questions_count = Column(Integer, default=3500)     # Savollar banki hajmi
    books_count = Column(Integer, default=14)           # Kitob va to'plamlar
    updated_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)  # Kurs yoki kitob nomi
    short_desc = Column(String, nullable=True)  # 1-2 ta reklama / tavsif jumlasi
    subject = Column(String, nullable=False, index=True)  # 'tarix', 'huquq', 'psixologiya'
    category = Column(String, nullable=False,
                      index=True)  # 'ms', 'attestatsiya', 'bmba_asosiy', 'kitoblar', 'paketlar', va h.k.
    item_type = Column(String, default="course")  # 'course', 'book', 'bundle', 'module'

    # Narx va chegirmalar (Coin hisobida)
    price_coin = Column(Integer, nullable=False)  # Amaldagi narxi (masalan: 120)
    old_price_coin = Column(Integer, default=0)  # Avvalgi chizilgan narxi (masalan: 200)

    # Ijtimoiy ko'rsatkichlar
    rating = Column(Float, default=5.0)  # O'rtacha baho (masalan: 4.9)
    buyers_count = Column(Integer, default=0)  # Sotib olganlar soni
    image_url = Column(String, nullable=True)  # Muqova rasmi
    is_active = Column(Boolean, default=True)

    # Modul sifatida alohida sotish (to'liq kursdan mustaqil)
    is_module = Column(Boolean, default=False)
    parent_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    subject_id = Column(Integer, nullable=True, index=True)  # Subject Hub bog'lanishi


class UserCourseAccess(Base):
    __tablename__ = "user_course_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Obuna tugash sanasi
    is_active = Column(Boolean, default=True)


class TargetInstitution(Base):
    __tablename__ = "target_institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "O'zbekiston Milliy Universiteti"
    short_name = Column(String, nullable=False)  # "O'zMU"
    inst_type = Column(String, nullable=False, index=True)  # 'otm', 'otm_harbiy', 'litsey', 'litsey_harbiy'
    region = Column(String, nullable=False, index=True)  # "Toshkent", "Samarqand", "Farg'ona", va h.k.
    logo_url = Column(String, nullable=True)  # Rasm / gerb havolasi
    gallery = Column(Text, nullable=True)  # Galereya: URL lar (\n yoki | bilan)
    video_review_url = Column(String, nullable=True)  # Videosharh ssilkasi
    overview_text = Column(Text, nullable=True)  # Umumiy tavsif
    admission_requirements = Column(Text, nullable=True)  # Qabul talablari (umumiy)
    eligibility_criteria = Column(Text, nullable=True)  # Kimlar qabul qilinadi
    admission_info = Column(Text, nullable=True)  # Qabul tartibi va joyi
    admission_date = Column(String, nullable=True)  # Hujjat topshirish muddati
    opportunities = Column(Text, nullable=True)  # Imkoniyatlar / imtiyozlar (career_opportunities)
    is_active = Column(Boolean, default=True)

    directions = relationship("TargetDirection", back_populates="institution", cascade="all, delete-orphan")


class TargetDirection(Base):
    __tablename__ = "target_directions"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("target_institutions.id"), nullable=False)
    title = Column(String, nullable=False, index=True)  # Yo'nalish nomi
    cipher = Column(String, nullable=True, index=True)  # Yo'nalish shifri
    edu_form = Column(String, nullable=True)  # Ta'lim shakli: Kunduzgi, Kechki, Masofaviy
    edu_lang = Column(String, nullable=True)  # Ta'lim tili
    education_lang = Column(String, default="O'zbek")  # Eski maydon (edu_lang bilan bir xil)

    subject_main = Column(String, nullable=False, index=True)  # 1-fan (asosiy)
    subject_second = Column(String, nullable=True)  # 2-fan
    subject_third = Column(String, nullable=True)  # 3-fan (harbiy litsey / subject3_exam)
    subject_secondary = Column(String, nullable=True)  # Eski maydon (subject_second bilan bir xil)
    mandatory_subjects = Column(String, nullable=True)  # Majburiy fanlar
    subject_block = Column(String, nullable=True, index=True)  # "1-fan - 2-fan - 3-fan"

    # Imtihon ballari va kvota statistikasi
    grant_score = Column(Float, default=0.0)
    contract_score = Column(Float, default=0.0)
    grant_ball = Column(Float, default=0.0)  # grant_score bilan bir xil qiymat
    contract_ball = Column(Float, default=0.0)  # contract_score bilan bir xil qiymat
    quota = Column(Integer, default=0)

    mock_quiz_id = Column(Integer, default=1)
    mock_test_url = Column(String, nullable=True)
    catalog_courses_url = Column(String, nullable=True)
    bundle_package_url = Column(String, nullable=True)
    subjects_table_image = Column(String, nullable=True)
    test_exam_date = Column(String, nullable=True)
    practical_mock_id = Column(String, nullable=True)
    practical_course_url = Column(String, nullable=True)
    # API/UI uchun yig'ma JSON (dates_timeline + practical_exams)
    dates_timeline_json = Column(Text, nullable=True)
    practical_exams_json = Column(Text, nullable=True)

    # Amaliy imtihonlar (exam1–exam5)
    exam1_date = Column(String, nullable=True)
    exam1_name = Column(String, nullable=True)
    exam1_criteria = Column(Text, nullable=True)
    exam1_mock_url = Column(String, nullable=True)
    exam1_course_url = Column(String, nullable=True)
    exam2_date = Column(String, nullable=True)
    exam2_name = Column(String, nullable=True)
    exam2_criteria = Column(Text, nullable=True)
    exam2_mock_url = Column(String, nullable=True)
    exam2_course_url = Column(String, nullable=True)
    exam3_date = Column(String, nullable=True)
    exam3_name = Column(String, nullable=True)
    exam3_criteria = Column(Text, nullable=True)
    exam3_mock_url = Column(String, nullable=True)
    exam3_course_url = Column(String, nullable=True)
    exam4_date = Column(String, nullable=True)
    exam4_name = Column(String, nullable=True)
    exam4_criteria = Column(Text, nullable=True)
    exam4_mock_url = Column(String, nullable=True)
    exam4_course_url = Column(String, nullable=True)
    exam5_date = Column(String, nullable=True)
    exam5_name = Column(String, nullable=True)
    exam5_criteria = Column(Text, nullable=True)
    exam5_mock_url = Column(String, nullable=True)
    exam5_course_url = Column(String, nullable=True)

    institution = relationship("TargetInstitution", back_populates="directions")


class UserCabinetItem(Base):
    __tablename__ = 'user_cabinet_items'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    product_id = Column(Integer, nullable=False)  # Product jadvali ID si
    item_type = Column(String, default="course")  # course, book
    title = Column(String, nullable=False)
    image_url = Column(String, nullable=True)

    # 4 ta holat filtri uchun: 'active', 'inactive', 'cart', 'archive'
    status = Column(String, default="active", index=True)

    # Status darajasi: "Shogird", "Bilimdon", "Ustoz"
    user_rank = Column(String, default="Shogird")

    # Obuna muddati
    expires_at = Column(DateTime, nullable=True)  # Tugash sanasi

    # 3 rangli progress ko'rsatkichlari (0-100%)
    actual_progress = Column(Integer, default=0)  # O'qilgan qism (Yashil)
    expected_progress = Column(Integer, default=0)  # Reja bo'yicha bo'lishi kerak bo'lgan (Qizil chegara)

    # Reyting ko'rsatkichi
    course_rank = Column(Integer, default=1)  # Kursdagi o'rni (masalan: 12-o'rin)

    # Davom etish manzili (dars yoki sahifa ID)
    last_lesson_id = Column(String, default="1")

    updated_at = Column(DateTime, default=datetime.utcnow)

# ==========================================================
# NAZORATCHI TIZIMI (SUPERVISOR / OTA-ONA NAZORATI)
# ==========================================================
class UserSupervisor(Base):
    __tablename__ = 'user_supervisors'

    id = Column(Integer, primary_key=True, index=True)
    student_tg_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False, index=True)
    supervisor_tg_id = Column(BigInteger, nullable=True, index=True)
    supervisor_name = Column(String, nullable=True)
    invite_token = Column(String, unique=True, index=True, nullable=False)
    terms_accepted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship(
        "User",
        primaryjoin="User.telegram_id == UserSupervisor.student_tg_id",
        foreign_keys=[student_tg_id],
        back_populates="supervisors"
    )


class SupervisorInvoice(Base):
    __tablename__ = 'supervisor_invoices'

    id = Column(Integer, primary_key=True, index=True)
    supervisor_tg_id = Column(BigInteger, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    check_image = Column(String, nullable=True)
    target_student_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=True, index=True)
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================================
# FAN TIZIMI VA O'QUV PANELI (SUBJECT HUB)
# ==========================================================
class SubjectCatalog(Base):
    """Platformadagi fanlar katalogi (Subject Hub asosi)."""
    __tablename__ = 'subject_catalog'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # tarix, huquq
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    community_chat_id = Column(BigInteger, nullable=True)  # Telegram community guruh
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SubjectModule(Base):
    """Fanning alohida sotiladigan moduli (masalan: 6-sinf O'zbekiston tarixi)."""
    __tablename__ = 'subject_modules'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)  # Katalog bog'lanishi
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    grade_level = Column(String, nullable=True)  # "6-sinf", "MS"
    order_num = Column(Integer, default=0)
    price_coin = Column(Integer, default=0)
    old_price_coin = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    is_standalone = Column(Boolean, default=True)  # To'liq kursdan tashqari sotiladi
    is_active = Column(Boolean, default=True)


class SubjectWiki(Base):
    """Fanga oid bilimlar bazasi (atama, shaxs, sana, qoida, nazariya)."""
    __tablename__ = 'subject_wiki'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    term = Column(String, nullable=False, index=True)
    definition = Column(Text, nullable=False)
    source_book = Column(String, nullable=True)  # Darslik / ma'lumotnoma
    grade_level = Column(String, nullable=True)  # "7-sinf", "Bob 3"
    topic_title = Column(String, nullable=True)  # Mavzu / bob
    concept_type = Column(String, default="atama", index=True)  # atama|shaxs|sana|qoida|nazariya
    created_at = Column(DateTime, default=datetime.utcnow)


class SubjectSchedule(Base):
    """Tematik-taqvimiy dars jadvali (mundarija va marshrut)."""
    __tablename__ = 'subject_schedules'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('subject_modules.id'), nullable=True, index=True)
    order_num = Column(Integer, default=0)
    topic_title = Column(String, nullable=False)
    planned_date = Column(Date, nullable=True)
    video_url = Column(String, nullable=True)
    test_score_avg = Column(Float, nullable=True)  # O'tgan mavzu test o'rtachasi (demo/seed)


class SubjectMistakeBank(Base):
    """Fan bo'yicha xatolar banki (Mistake Vault)."""
    __tablename__ = 'subject_mistake_bank'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram ID
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    question_text = Column(Text, nullable=True)
    options_json = Column(Text, nullable=True)  # JSON massiv
    correct_answer = Column(String, nullable=True)
    user_wrong_answer = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    mistake_count = Column(Integer, default=1)
    is_resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SubjectCommunityPost(Base):
    """Fan hamjamiyati forumi (#savol, #manba, #tushunmadim)."""
    __tablename__ = 'subject_community_posts'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    user_name = Column(String, nullable=True)
    hashtags = Column(String, nullable=True)  # "#savol #manba"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SubjectDiagnosticReport(Base):
    """Test diagnostikasi: videosharh, manbalar, kuchli/ojiz tahlil."""
    __tablename__ = 'subject_diagnostic_reports'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    quiz_id = Column(Integer, nullable=False, index=True)
    quiz_title = Column(String, nullable=True)
    video_review_url = Column(String, nullable=True)
    analysis_text = Column(Text, nullable=True)
    strengths_text = Column(Text, nullable=True)
    weaknesses_text = Column(Text, nullable=True)
    sources_json = Column(Text, nullable=True)  # [{"title":"...","url":"..."}]
    created_at = Column(DateTime, default=datetime.utcnow)


class SubjectBook(Base):
    """Elektron darslik / qo'llanma (faqat in-app viewer)."""
    __tablename__ = 'subject_books'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('subject_modules.id'), nullable=True)
    title = Column(String, nullable=False)
    book_type = Column(String, default="darslik")  # darslik|qollanma|malumotnoma|savolnoma
    cover_url = Column(String, nullable=True)
    viewer_url = Column(String, nullable=True)  # In-app ochiladigan manba
    is_downloadable = Column(Boolean, default=False)  # Har doim False (bloklangan)
    is_active = Column(Boolean, default=True)


class SubjectQuizLink(Base):
    """Bob / kitob / fan bo'yicha testlar majmuasi (Testlar bo'limiga yo'naltiradi)."""
    __tablename__ = 'subject_quiz_links'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('subject_modules.id'), nullable=True)
    title = Column(String, nullable=False)
    scope = Column(String, default="bob")  # bob|kitob|fan|modul
    quiz_id = Column(Integer, nullable=True)  # Testlar modulidagi ID
    is_paid = Column(Boolean, default=False)
    price_coin = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class UserSubjectEnrollment(Base):
    """O'quvchining fan bo'yicha yozilishi, statusi va sur'ati."""
    __tablename__ = 'user_subject_enrollments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram ID
    subject_id = Column(Integer, ForeignKey('subject_catalog.id'), nullable=False, index=True)
    status = Column(String, default="active", index=True)  # active|completed|paused
    rank_label = Column(String, default="Shogird")  # Shogird|Bilimdon|Ustoz|Grossmeyster
    actual_progress = Column(Integer, default=0)  # 0-100
    expected_progress = Column(Integer, default=0)  # 0-100 reja
    current_schedule_id = Column(Integer, nullable=True)  # Jadvaldagi joriy nuqta
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# ==========================================================
# TESTLAR BO'LIMI (IMTIHON KARTALARI, BAHOLASH, TOPSHIRIQLAR)
# ==========================================================
class ExamQuiz(Base):
    """Fan va imtihon turi bo'yicha e'lon qilingan test."""
    __tablename__ = "exam_quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False, index=True)  # tarix | huquq | psixologiya | ona_tili
    exam_type = Column(String, nullable=False, index=True)
    price = Column(Integer, default=0)  # so'm; 0 = bepul
    link = Column(String, nullable=True)  # to'liq / uzun havola
    pdf_url = Column(String, nullable=True)  # rasmiy DTM test varaqasi
    answer_sheet_url = Column(String, nullable=True)  # javoblar varaqasi (titul)
    analysis_text = Column(Text, nullable=True)  # admin umumiy tahlil matni
    duration_minutes = Column(Integer, default=20)
    announced_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    command_path = Column(String, index=True, nullable=True)  # Botdagi bo'lim (/ms/tarix, /kurs/1/namunaviy)
    visible_at = Column(DateTime, nullable=True)  # Botda va ro'yxatda e'lon chiqish vaqti
    starts_at = Column(DateTime, nullable=True)  # Test yechish ruxsati ochiladigan vaqt
    base_price = Column(Integer, default=0)  # Asosiy narx (0 bo'lsa tekin)
    free_for_courses = Column(String, default="")  # Kurs egalariga bepul ("101,102")
    share_discount_percent = Column(Integer, default=0)  # Referal ulashishdagi chegirma %
    full_analysis_video = Column(String, nullable=True)  # Barcha savollar tahlilining umumiy videosi

    questions = relationship("ExamQuestion", back_populates="quiz", cascade="all, delete-orphan")
    ratings = relationship("ExamRating", back_populates="quiz", cascade="all, delete-orphan")
    submissions = relationship("ExamSubmission", back_populates="quiz", cascade="all, delete-orphan")


class ExamQuestion(Base):
    """Test savoli: mavzu, yo'nalish, qiyinlik va kitob manbalari."""
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("exam_quizzes.id"), nullable=False, index=True)
    order_num = Column(Integer, default=1)
    question_text = Column(Text, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(Integer, nullable=False)  # 0=A, 1=B, 2=C, 3=D
    topic = Column(String, nullable=True)  # mavzu
    direction = Column(String, nullable=True)  # yo'nalish
    difficulty = Column(String, default="orta")  # oson | orta | qiyin
    book_links_json = Column(Text, nullable=True)  # {"A": "kitob, bet", ...}
    analysis_text = Column(Text, nullable=True)
    image_top = Column(String, nullable=True)  # Savol matnidan oldin chiqadigan rasm
    image_bottom = Column(String, nullable=True)  # Savol matnidan keyin chiqadigan rasm
    difficulty_beta = Column(Float, default=2.0)  # Rasch qiyinchilik parametri (1.1–3.2)
    option_sources = Column(Text, nullable=True)  # {"A": "7-sinf Tarix, 42-bet", ...}
    solution_text = Column(Text, nullable=True)  # Yozma uslubiy sharh va yechish yo'li
    video_solution_url = Column(String, nullable=True)  # Shu savolning video tahlil havolasi

    quiz = relationship("ExamQuiz", back_populates="questions")


class ExamRating(Base):
    """Foydalanuvchining 1-5 yulduz bahosi (har testda bitta ovoz)."""
    __tablename__ = "exam_ratings"
    __table_args__ = (
        UniqueConstraint("quiz_id", "user_id", name="uq_exam_rating_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("exam_quizzes.id"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    stars = Column(Integer, nullable=False)  # 1..5
    created_at = Column(DateTime, default=datetime.utcnow)

    quiz = relationship("ExamQuiz", back_populates="ratings")


class ExamSubmission(Base):
    """Elektron yoki skaner orqali topshirilgan javoblar va ball."""
    __tablename__ = "exam_submissions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("exam_quizzes.id"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    region = Column(String, nullable=True, index=True)
    district = Column(String, nullable=True, index=True)
    score = Column(Integer, default=0)  # to'g'ri javoblar soni
    total_questions = Column(Integer, default=0)
    percent = Column(Float, default=0.0)
    ability_theta = Column(Float, nullable=True)  # Rasch qobiliyat balli
    answers_json = Column(Text, nullable=True)  # {"question_id": option_index}
    mode = Column(String, default="elektron")  # elektron | qogoz | skaner
    level_label = Column(String, default="Boshlang'ich")  # Boshlang'ich | Bilimdon | Ustoz
    created_at = Column(DateTime, default=datetime.utcnow)

    quiz = relationship("ExamQuiz", back_populates="submissions")


# ==========================================================
# MASTER BAZA (master_baza.xlsx — fakt + savol-javob)
# ==========================================================
class MasterFactQuestion(Base):
    """master_baza.xlsx dagi faktlar, savollar va etalon javoblar."""
    __tablename__ = "master_fact_questions"

    id = Column(Integer, primary_key=True)
    fakt_id = Column(String, index=True, nullable=False)  # Masalan: '6_01_01'
    test_id = Column(String, index=True, nullable=True)  # Masalan: 'T_6_01_01'
    grade = Column(Integer, index=True, nullable=False)  # Fakt_ID dan: '6_01_01' -> 6
    topic_num = Column(Integer, index=True, nullable=False)  # Fakt_ID dan: '6_01_01' -> 1
    asl_gap = Column(Text, nullable=False)  # Nazariy matn / fakt
    fakt_kontekst = Column(Text, nullable=True)
    savol_matni = Column(Text, nullable=False)  # Savol
    test_matni = Column(Text, nullable=True)
    test_obyekt = Column(String, nullable=True)
    etalon_javob = Column(Text, nullable=False)  # To'g'ri javob
    variant_b = Column(Text, nullable=True)
    variant_c = Column(Text, nullable=True)
    variant_d = Column(Text, nullable=True)
    kalit_soz = Column(String, nullable=True)
    klass = Column(String, nullable=True)  # '[VHJ]', '[SAN]'
    yonalish = Column(String, nullable=True)  # '[IJT]', '[SIY]'
    tarkibiy_faktlar = Column(Text, nullable=True)
    tematik_teg = Column(String, nullable=True)  # '[DAVRLASHTIRISH]'
    mavzu_reja = Column(String, nullable=True)  # 'R_6_01_01'