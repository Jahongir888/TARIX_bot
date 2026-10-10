from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# ==========================================================
# 1. FOYDALANUVCHILAR JADVALI
# ==========================================================
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False) # Katta ID larni sig'dirish uchun BigInteger
    full_name = Column(String, nullable=True)
    phone_number = Column(String, unique=True, nullable=True)
    region = Column(String, nullable=True)
    target = Column(String, nullable=True)              # Abituriyent, Attestatsiya, Noldan
    selected_subject = Column(String, default="tarix")  # Tarix, Huquq
    balance = Column(Integer, default=0)                # Ichki balans (so'mda)
    is_paid = Column(Boolean, default=False)            # Umumiy obuna holati
    created_at = Column(DateTime, default=datetime.utcnow)

    progress = relationship("UserProgress", back_populates="user")
    orders = relationship("BookOrder", back_populates="user")
    news_reactions = relationship("NewsReaction", back_populates="user")
    news_comments = relationship("NewsComment", back_populates="user")


# ==========================================================
# 2. DARSLAR JADVALI
# ==========================================================
class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    subject = Column(String, default="tarix")
    class_level = Column(String, nullable=False)
    order_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    is_free = Column(Boolean, default=False)


# ==========================================================
# 3. TEST NATIJALARI VA RASCH TAHLILI
# ==========================================================
class UserProgress(Base):
    __tablename__ = 'user_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    test_title = Column(String, nullable=False)
    raw_score = Column(Integer)
    percentage = Column(Float)
    theta_ability = Column(Float, nullable=True)
    completed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")


# ==========================================================
# 4. KITOBLAR BUYURTMASI
# ==========================================================
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
# 5. YANGILIKLAR (NEWS) JADVALI
# ==========================================================
class News(Base):
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    hashtags = Column(String, nullable=False)                # Masalan: "#matematika #MS"
    category = Column(String, default="umumiy")              # matematika, tarix, huquq...
    summary = Column(Text, nullable=True)                    # Kartochkadagi qisqa tavsif
    content = Column(Text, nullable=False)                   # To'liq maqola matni
    image_url = Column(String, nullable=False)               # Asosiy rasm (xira fon va ichki rasm)
    source_url = Column(String, nullable=True)               # Asl manba havolasi
    source_name = Column(String, default="Manba")            # Havola yozuvi
    views_count = Column(Integer, default=0)                 # Ko'rishlar soni
    discussion_chat_id = Column(BigInteger, nullable=True)   # Bog'langan guruh ID'si
    telegram_post_msg_id = Column(BigInteger, nullable=True) # Reply qilish uchun post xabari ID'si
    created_at = Column(DateTime, default=datetime.utcnow)

    reactions = relationship("NewsReaction", back_populates="news", cascade="all, delete-orphan")
    comments = relationship("NewsComment", back_populates="news", cascade="all, delete-orphan")


# ==========================================================
# 6. YANGILIK REAKSIYALARI
# ==========================================================
class NewsReaction(Base):
    __tablename__ = 'news_reactions'

    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, ForeignKey('news.id'))
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    reaction = Column(String, nullable=False)                # '👍', '❤️', '🔥', '💡'

    news = relationship("News", back_populates="reactions")
    user = relationship("User", back_populates="news_reactions")


# ==========================================================
# 7. YANGILIK IZOHLARI (COMMENTS)
# ==========================================================
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