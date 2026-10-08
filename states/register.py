from aiogram.fsm.state import StatesGroup, State


class RegisterState(StatesGroup):
    full_name = State()   # 1. Ism-familiya kutish
    contact = State()     # 2. Telefon raqami (kontakt tugmasi) kutish
    region = State()      # 3. Viloyatni tugmadan tanlash
    target = State()      # 4. O'qish maqsadini tugmadan tanlash


class PaymentState(StatesGroup):
    receipt = State()     # To'lov cheki (rasm) kutish holati