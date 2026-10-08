from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# 1. Foydalanuvchilar jadvali
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
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

# 2. Darslar jadvali
class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True)
    subject = Column(String, default="tarix")
    class_level = Column(String, nullable=False)
    order_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    is_free = Column(Boolean, default=False)

# 3. Test natijalari va Rasch tahlili
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

# 4. Kitoblar buyurtmasi
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