import asyncio
import logging
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery

TOKEN = "8942208545:AAH0ZBJIzDYavifVzDKMt3dIPmialCn300g"
ADMIN_IDS = [8973160882]

BELLS_SCHEDULE = {
    "1": "8:00 - 8:45",
    "2": "8:55 - 9:40",
    "3": "9:55 - 10:40",
    "4": "10:55 - 11:40",
    "5": "11:50 - 12:35",
    "6": "12:55 - 13:40",
    "7": "13:50 - 14:35",
    "8": "14:50 - 15:35"
}

HOLIDAYS = {
    "Осенние (первые)": "5 октября - 11 октября 2026",
    "Осенние (вторые)": "16 ноября - 22 ноября 2026",
    "Новогодние": "31 декабря 2026 - 10 января 2027",
    "Весенние": "22 февраля - 28 февраля 2027",
    "Весенние (вторые)": "5 апреля - 11 апреля 2027",
    "Летние": "1 июня - 31 августа 2027"
}

MEAL_SCHEDULE = [
    {"time": "8:40 - 8:55", "meal": "Завтрак", "classes": "1а, 1б, 1М, 3Б, 3В"},
    {"time": "9:40 - 9:55", "meal": "Завтрак", "classes": "3г, 3д, 4а, 4в"},
    {"time": "10:40 - 10:50", "meal": "Завтрак", "classes": "Льготное питание 5-11 классы и платное питание"},
    {"time": "11:00 - 11:10", "meal": "Завтрак", "classes": "ГПД (во время урока)"},
    {"time": "11:40 - 11:50", "meal": "Обед", "classes": "1 смена начальные классы"},
    {"time": "12:35 - 12:55", "meal": "Обед", "classes": "Льготное и платное питание 5-8 классы"},
    {"time": "13:15 - 13:30", "meal": "Обед", "classes": "ГПД 1-ые классы"},
    {"time": "13:40 - 13:50", "meal": "Обед", "classes": "Льготное питание 9-11 классы и платное питание"},
    {"time": "14:35 - 14:50", "meal": "Обед", "classes": "Начальные классы 2 смена"},
    {"time": "15:35 - 15:50", "meal": "Полдник", "classes": "2а, 2б, 2в, 2г"},
    {"time": "16:35 - 16:45", "meal": "Полдник", "classes": "3а, 3аэш, 4б, 4г"}
]

OLYMPIAD_SCHEDULE = [
    {"date": "7 сентября", "subjects": "Немецкий язык, ОБЗР"},
    {"date": "12 сентября", "subjects": "Китайский язык, Итальянский язык, Литература"},
    {"date": "14 сентября", "subjects": "Экология, Испанский язык"},
    {"date": "19 сентября", "subjects": "Русский язык"},
    {"date": "21 сентября", "subjects": "Русский язык, Экономика"},
    {"date": "26 сентября", "subjects": "Математика"},
    {"date": "28 сентября", "subjects": "Математика, Химия"},
    {"date": "3 октября", "subjects": "Обществознание"},
    {"date": "12 октября", "subjects": "Информатика (робототехника, искусственный интеллект)"}
]

OLYMPIAD_INFO = (
    "💡 Школьный этап Всероссийской олимпиады\n"
    "Московская область 2026/2027\n\n"
    "📅 Сроки: 8 сентября - 17 октября\n"
    "📚 24 предмета\n"
    "👥 5-11 классы (4 классы: математика и русский)\n"
    "💻 Платформа: http://mo.olymponline.ru\n"
    "📝 Регистрация: с 3 сентября\n\n"
    "⚠️ Можно выбрать задания за старший класс!\n"
    "⚠️ Информатика - отдельно"
)

# ===================== НАСТРОЙКА ЛОГИРОВАНИЯ =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Отключаем шумные логи aiogram
logging.getLogger('aiogram.event').setLevel(logging.WARNING)
logging.getLogger('aiogram.dispatcher').setLevel(logging.WARNING)

conn = sqlite3.connect('parlament.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        text TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        text TEXT,
        is_anonymous INTEGER DEFAULT 1,
        answer TEXT,
        answered_by TEXT,
        answered_at TEXT,
        created_at TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS polls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        options TEXT,
        votes TEXT,
        created_at TEXT,
        is_active INTEGER DEFAULT 1
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        birthday TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS music_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        song TEXT,
        artist TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
''')
conn.commit()

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💡 Подать идею")],
        [KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="📊 Участвовать в опросе")],
        [KeyboardButton(text="📜 Наши правила")],
        [KeyboardButton(text="🕐 Расписание звонков")],
        [KeyboardButton(text="📅 Каникулы")],
        [KeyboardButton(text="🍽 Расписание питания")],
        [KeyboardButton(text="🏆 Олимпиада")],
        [KeyboardButton(text="🎂 День рождения")],
        [KeyboardButton(text="🎵 Заказать музыку")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 Новые идеи")],
        [KeyboardButton(text="✅ Одобренные идеи")],
        [KeyboardButton(text="❓ Вопросы без ответа")],
        [KeyboardButton(text="📊 Создать опрос")],
        [KeyboardButton(text="⏹ Завершить опрос")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🕐 Расписание звонков")],
        [KeyboardButton(text="📅 Каникулы")],
        [KeyboardButton(text="🍽 Расписание питания")],
        [KeyboardButton(text="🏆 Олимпиада")],
        [KeyboardButton(text="🎂 День рождения")],
        [KeyboardButton(text="🎵 Новые заявки")],
        [KeyboardButton(text="✅ Одобренные песни")],
        [KeyboardButton(text="🎵 Заказать музыку")]
    ],
    resize_keyboard=True
)

class IdeaStates(StatesGroup):
    waiting_for_idea = State()

class QuestionStates(StatesGroup):
    waiting_for_question = State()

class PollStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_options = State()

class BirthdayStates(StatesGroup):
    waiting_for_birthday = State()

class MusicStates(StatesGroup):
    waiting_for_song = State()
    waiting_for_artist = State()

class AnswerStates(StatesGroup):
    waiting_for_answer = State()

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def log_user(message):
    """Логирует информацию о пользователе"""
    user = message.from_user
    text = message.text or "[НЕТ ТЕКСТА]"
    logger.info(f"👤 [{user.id}] @{user.username or 'нет'} | {user.full_name} | {text[:50]}")

def log_callback(callback):
    """Логирует callback-запросы"""
    user = callback.from_user
    logger.info(f"🔄 КОЛБЭК [{user.id}] @{user.username or 'нет'} | {callback.data}")

def days_until_birthday(birthday_str):
    try:
        birth_date = datetime.strptime(birthday_str, "%d.%m")
        today = datetime.now()
        birth_this_year = datetime(today.year, birth_date.month, birth_date.day)
        if birth_this_year < today:
            birth_this_year = datetime(today.year + 1, birth_date.month, birth_date.day)
        days = (birth_this_year - today).days
        return days, birth_this_year
    except:
        return None, None

def get_current_lesson():
    from datetime import timezone, timedelta
    # Получаем точное время по МСК (UTC+3)
    now = datetime.now(timezone(timedelta(hours=3))).time()
    current_minutes = now.hour * 60 + now.minute

    # Точное расписание уроков (переведено в минуты от начала дня)
    lessons = [
        {"num": 1, "start": 8*60+0,  "end": 8*60+45},   # 8:00 - 8:45
        {"num": 2, "start": 8*60+55, "end": 9*60+40},   # 8:55 - 9:40
        {"num": 3, "start": 9*60+55, "end": 10*60+40},  # 9:55 - 10:40
        {"num": 4, "start": 10*60+55, "end": 11*60+40}, # 10:55 - 11:40
        {"num": 5, "start": 11*60+50, "end": 12*60+35}, # 11:50 - 12:35
        {"num": 6, "start": 12*60+55, "end": 13*60+40}, # 12:55 - 13:40
        {"num": 7, "start": 13*60+50, "end": 14*60+35}, # 13:50 - 14:35
        {"num": 8, "start": 14*60+50, "end": 15*60+35}  # 14:50 - 15:35
    ]

    # Если уроки еще вообще не начались
    if current_minutes < lessons[0]["start"]:
        return None, "уроки еще не начались"

    # Проверяем каждый урок и перемену
    for i, les in enumerate(lessons):
        # Если время попадает в интервал урока
        if les["start"] <= current_minutes <= les["end"]:
            return les["num"], "идет"
        
        # Если время между текущим и следующим уроком (перемена)
        if i < len(lessons) - 1:
            next_les = lessons[i+1]
            if les["end"] < current_minutes < next_les["start"]:
                break_len = next_les["start"] - les["end"]
                if break_len == 20:
                    return les["num"], "перемена (большая, 20 минут)"
                elif break_len == 15:
                    return les["num"], "перемена (15 минут)"
                else:
                    return les["num"], "перемена (10 минут)"

    return None, "уроки закончились"


def get_next_holiday():
    today = datetime.now()
    holiday_dates = {}
    for name, date_str in HOLIDAYS.items():
        try:
            parts = date_str.split(' - ')
            if len(parts) == 2:
                start_str = parts[0].strip()
                end_str = parts[1].strip()
                if 'октября' in start_str or 'ноября' in start_str or 'февраля' in start_str or 'апреля' in start_str:
                    start_date = datetime.strptime(start_str + f" {today.year}", "%d %B %Y")
                    end_date = datetime.strptime(end_str + f" {today.year}", "%d %B %Y")
                elif 'декабря' in start_str:
                    start_date = datetime.strptime(start_str + f" {today.year}", "%d %B %Y")
                    end_date = datetime.strptime(end_str + f" {today.year + 1}", "%d %B %Y")
                elif 'июня' in start_str:
                    start_date = datetime.strptime(start_str + f" {today.year}", "%d %B %Y")
                    end_date = datetime.strptime(end_str + f" {today.year}", "%d %B %Y")
                else:
                    continue
                holiday_dates[name] = (start_date, end_date)
        except:
            pass
    nearest = None
    nearest_days = None
    for name, (start, end) in holiday_dates.items():
        if start > today:
            days = (start - today).days
            if nearest_days is None or days < nearest_days:
                nearest_days = days
                nearest = (name, start, end, days)
    return nearest

# ===================== СТАРТ =====================
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    log_user(message)
    logger.info(f"🚀 СТАРТ от [{message.from_user.id}]")
    await state.clear()
    welcome = (
        "Привет-привет! 🤗\n\n"
        "Это бот «Новое Поколение» — мы школьный парламент.\n\n"
        "Хочешь изменить школу к лучшему? Просто напиши мне свою идею!\n\n"
        "Вместе мы сделаем школу круче!\n\n"
        "📌 Что я умею:\n"
        "• Принимать идеи\n"
        "• Отвечать на вопросы\n"
        "• Проводить опросы\n"
        "• Показывать расписание звонков\n"
        "• Рассказывать о каникулах\n"
        "• Показывать расписание питания\n"
        "• Информировать об олимпиаде\n"
        "• Считать дни до дня рождения\n"
        "• Принимать заявки на музыку\n\n"
        "Пиши — мы слушаем! 🎯"
    )
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(welcome, reply_markup=kb)

# ===================== ПРАВИЛА =====================
@dp.message(F.text == "📜 Наши правила")
async def rules_cmd(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    rules = (
        "📜 Правила парламента «Новое Поколение»:\n\n"
        "1️⃣ Уважение — слушаем всех\n"
        "2️⃣ Анонимность — данные не светятся\n"
        "3️⃣ Конструктив — критика с решением\n"
        "4️⃣ Активность — чем больше идей, тем круче школа\n\n"
        "🎵 Правила для заказа музыки:\n"
        "• Без матов и нецензурной лексики\n"
        "• Исполнители не должны быть иноагентами\n"
        "• Только позитивные и школьные песни"
    )
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(rules, reply_markup=kb)

# ===================== РАСПИСАНИЕ ЗВОНКОВ =====================
@dp.message(F.text == "🕐 Расписание звонков")
async def show_bells(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    lesson_num, status = get_current_lesson()
    text = "🕐 Расписание звонков:\n\n"
    for num, time in BELLS_SCHEDULE.items():
        if lesson_num and int(num) == lesson_num:
            text += f"🔴 {num} урок: {time}  ← {status}\n"
        else:
            text += f"   {num} урок: {time}\n"
    text += "\n🔄 Перемены:\n"
    text += "   • 5 минут (1-2, 2-3, 4-5, 5-6, 6-7, 7-8)\n"
    text += "   • 15 минут (после 3 урока)"
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(text, reply_markup=kb)

# ===================== КАНИКУЛЫ =====================
@dp.message(F.text == "📅 Каникулы")
async def show_holidays(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    text = "📅 Каникулы 2026-2027:\n\n"
    for name, dates in HOLIDAYS.items():
        text += f"• {name}: {dates}\n"
    nearest = get_next_holiday()
    if nearest:
        name, start, end, days = nearest
        text += f"\n⏳ Ближайшие каникулы:\n"
        text += f"   📌 {name}\n"
        text += f"   Через {days} дней\n"
        text += f"   {start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(text, reply_markup=kb)

# ===================== РАСПИСАНИЕ ПИТАНИЯ =====================
@dp.message(F.text == "🍽 Расписание питания")
async def show_meals(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    text = "🍽 Расписание питания:\n\n"
    for item in MEAL_SCHEDULE:
        text += f"🕐 {item['time']}\n"
        text += f"   🍲 {item['meal']}\n"
        text += f"   📚 {item['classes']}\n\n"
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(text, reply_markup=kb)

# ===================== ОЛИМПИАДА =====================
@dp.message(F.text == "🏆 Олимпиада")
async def show_olympiad(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    text = OLYMPIAD_INFO + "\n\n"
    text += "📅 График олимпиады:\n\n"
    for item in OLYMPIAD_SCHEDULE:
        text += f"📌 {item['date']}: {item['subjects']}\n"
    text += "\n\n⚠️ Практический тур по физкультуре - отдельно"
    text += "\n📝 Результаты: olymp.informatics.ru"
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(text, reply_markup=kb)

# ===================== ДЕНЬ РОЖДЕНИЯ =====================
@dp.message(F.text == "🎂 День рождения")
async def birthday_menu(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    cursor.execute("SELECT birthday FROM users WHERE user_id = ?", (message.from_user.id,))
    result = cursor.fetchone()
    if result and result[0]:
        birthday_str = result[0]
        days, birth_date = days_until_birthday(birthday_str)
        if days is None:
            await message.answer("❌ Ошибка в дате")
            return
        if days == 0:
            await message.answer(f"🎉 С ДНЁМ РОЖДЕНИЯ, {message.from_user.first_name}! 🥳")
        else:
            await message.answer(f"🎂 До дня рождения осталось {days} дней")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить дату", callback_data="change_birthday")],
            [InlineKeyboardButton(text="🗑 Удалить дату", callback_data="delete_birthday")]
        ])
        await message.answer("Что хочешь сделать?", reply_markup=keyboard)
    else:
        await state.set_state(BirthdayStates.waiting_for_birthday)
        await message.answer(
            "🎂 Введи дату рождения\n"
            "Формат: ДД.ММ\n"
            "Пример: 15.06\n\n"
            "❌ /cancel - отмена"
        )

@dp.callback_query(F.data == "change_birthday")
async def change_birthday(callback: CallbackQuery, state: FSMContext):
    log_callback(callback)
    await state.set_state(BirthdayStates.waiting_for_birthday)
    await callback.message.answer(
        "✏️ Введи новую дату рождения\n"
        "Формат: ДД.ММ\n"
        "❌ /cancel - отмена"
    )
    await callback.answer()

@dp.callback_query(F.data == "delete_birthday")
async def delete_birthday(callback: CallbackQuery):
    log_callback(callback)
    cursor.execute("DELETE FROM users WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    kb = admin_kb if is_admin(callback.from_user.id) else main_kb
    await callback.message.answer("🗑 Дата удалена", reply_markup=kb)
    await callback.answer()

@dp.message(BirthdayStates.waiting_for_birthday)
async def save_birthday(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("❌ Отменено", reply_markup=kb)
        return
    birthday_str = message.text.strip()
    days, birth_date = days_until_birthday(birthday_str)
    if days is None:
        await message.answer("❌ Неверный формат. Используй ДД.ММ")
        return
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, birthday) VALUES (?, ?)",
        (message.from_user.id, birthday_str)
    )
    conn.commit()
    await state.clear()
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(f"✅ Дата сохранена! До дня рождения {days} дней", reply_markup=kb)

# ===================== ИДЕИ =====================
@dp.message(F.text == "💡 Подать идею")
async def idea_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await state.set_state(IdeaStates.waiting_for_idea)
    await message.answer(
        "💡 Опиши свою идею\n\n"
        "❌ /cancel - отмена"
    )

@dp.message(IdeaStates.waiting_for_idea)
async def idea_receive(message: Message, state: FSMContext):
    log_user(message)
    logger.info(f"💡 ИДЕЯ от [{message.from_user.id}]: {message.text[:50]}")
    if message.text == "/cancel":
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("❌ Отменено", reply_markup=kb)
        return
    user_id = message.from_user.id
    username = message.from_user.username or "без юзернейма"
    text = message.text
    cursor.execute(
        "INSERT INTO ideas (user_id, username, text, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, text, "pending", datetime.now().strftime("%d.%m.%Y %H:%M"))
    )
    conn.commit()
    await state.clear()
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer("✅ Идея отправлена на рассмотрение! Спасибо!", reply_markup=kb)
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"📩 Новая идея\nОт: @{username} (ID: {user_id})\n\n{text}\n\nИспользуй 'Новые идеи' для модерации"
        )

# ===================== ВОПРОСЫ =====================
@dp.message(F.text == "❓ Задать вопрос")
async def question_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await state.set_state(QuestionStates.waiting_for_question)
    await message.answer(
        "❓ Напиши свой вопрос\n\n"
        "❌ /cancel - отмена"
    )

@dp.message(QuestionStates.waiting_for_question)
async def question_receive(message: Message, state: FSMContext):
    log_user(message)
    logger.info(f"❓ ВОПРОС от [{message.from_user.id}]: {message.text[:50]}")
    if message.text == "/cancel":
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("❌ Отменено", reply_markup=kb)
        return
    user_id = message.from_user.id
    username = message.from_user.username or "Аноним"
    text = message.text
    cursor.execute(
        "INSERT INTO questions (user_id, username, text, is_anonymous, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, text, 1, datetime.now().strftime("%d.%m.%Y %H:%M"))
    )
    conn.commit()
    await state.clear()
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer("✅ Вопрос отправлен!", reply_markup=kb)
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"❓ Новый вопрос\nID: {user_id}\nОт: @{username}\n\n{text}"
        )

# ===================== ОПРОСЫ =====================
@dp.message(F.text == "📊 Участвовать в опросе")
async def poll_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    cursor.execute("SELECT id, question, options, votes FROM polls WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    poll = cursor.fetchone()
    if not poll:
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("😴 Активных опросов нет", reply_markup=kb)
        return
    poll_id, question, options_str, votes_str = poll
    options = options_str.split('|||')
    votes = votes_str.split('|||') if votes_str else ['0'] * len(options)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for i, opt in enumerate(options):
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{opt} ({votes[i]})",
                callback_data=f"vote_{poll_id}_{i}"
            )
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="📊 Результаты", callback_data=f"results_{poll_id}")
    ])
    await message.answer(
        f"📊 Опрос:\n\n{question}",
        reply_markup=keyboard
    )

# ===================== МУЗЫКА =====================
@dp.message(F.text == "🎵 Заказать музыку")
async def music_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await state.set_state(MusicStates.waiting_for_song)
    await message.answer(
        "🎵 Введи название песни\n\n"
        "⚠️ Правила:\n"
        "• Без матов\n"
        "• Исполнитель не должен быть иноагентом\n\n"
        "❌ /cancel - отмена"
    )

@dp.message(MusicStates.waiting_for_song)
async def music_get_song(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("❌ Отменено", reply_markup=kb)
        return
    await state.update_data(song=message.text)
    await state.set_state(MusicStates.waiting_for_artist)
    await message.answer(
        "🎤 Введи исполнителя\n\n"
        "❌ /cancel - отмена"
    )

@dp.message(MusicStates.waiting_for_artist)
async def music_get_artist(message: Message, state: FSMContext):
    log_user(message)
    logger.info(f"🎵 МУЗЫКА от [{message.from_user.id}]: {message.text[:50]}")
    if message.text == "/cancel":
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("❌ Отменено", reply_markup=kb)
        return
    data = await state.get_data()
    song = data.get('song')
    artist = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "без юзернейма"
    cursor.execute(
        "INSERT INTO music_requests (user_id, username, song, artist, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, song, artist, "pending", datetime.now().strftime("%d.%m.%Y %H:%M"))
    )
    conn.commit()
    await state.clear()
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer(
        f"✅ Заявка отправлена на модерацию!\n\n"
        f"🎵 Песня: {song}\n"
        f"🎤 Исполнитель: {artist}\n\n"
        f"Мы проверим трек и добавим в плейлист, если он подходит по правилам 🎶",
        reply_markup=kb
    )
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"🎵 Новая заявка на музыку\n"
            f"От: @{username} (ID: {user_id})\n"
            f"Песня: {song}\n"
            f"Исполнитель: {artist}"
        )

# ===================== ОТВЕТ НА ВОПРОС =====================
@dp.callback_query(F.data.startswith("answer_question_"))
async def start_answer(callback: CallbackQuery, state: FSMContext):
    log_callback(callback)
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    q_id = callback.data.split('_')[2]
    await state.update_data(answer_question_id=q_id)
    await state.set_state(AnswerStates.waiting_for_answer)
    await callback.message.answer(
        f"✏️ Введи ответ на вопрос #{q_id}\n\n"
        "❌ /cancel - отмена"
    )
    await callback.answer()

@dp.message(AnswerStates.waiting_for_answer)
async def process_answer(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("❌ Отменено", reply_markup=kb)
        return
    data = await state.get_data()
    q_id = data.get('answer_question_id')
    if not q_id:
        await state.clear()
        await message.answer("❌ Ошибка. Попробуй снова")
        return
    answer_text = message.text
    admin_name = message.from_user.full_name or "Админ"
    cursor.execute("SELECT user_id, text FROM questions WHERE id = ?", (q_id,))
    result = cursor.fetchone()
    if not result:
        await message.answer("❌ Вопрос не найден")
        await state.clear()
        return
    user_id, question_text = result
    cursor.execute(
        "UPDATE questions SET answer = ?, answered_by = ?, answered_at = ? WHERE id = ?",
        (answer_text, admin_name, datetime.now().strftime("%d.%m.%Y %H:%M"), q_id)
    )
    conn.commit()
    await state.clear()
    try:
        await bot.send_message(
            user_id,
            f"📩 **Ответ на ваш вопрос**\n\n"
            f"❓ Ваш вопрос:\n{question_text}\n\n"
            f"💬 Ответ от {admin_name}:\n{answer_text}\n\n"
            f"Спасибо за обращение! 🙌"
        )
        await message.answer(
            f"✅ Ответ на вопрос #{q_id} отправлен пользователю!",
            reply_markup=admin_kb
        )
    except Exception as e:
        await message.answer(
            f"⚠️ Ответ сохранён, но не удалось отправить пользователю.\n"
            f"Возможно, он заблокировал бота.\n\n"
            f"Текст ответа:\n{answer_text}",
            reply_markup=admin_kb
        )

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    kb = admin_kb if is_admin(message.from_user.id) else main_kb
    await message.answer("❌ Отменено", reply_markup=kb)

# ===================== АДМИН-КОМАНДЫ =====================
@dp.message()
async def handle_all_messages(message: Message, state: FSMContext):
    log_user(message)
    text = message.text.strip()
    current_state = await state.get_state()
    
    if current_state == PollStates.waiting_for_question.state:
        await state.update_data(question=text)
        await state.set_state(PollStates.waiting_for_options)
        await message.answer(
            "📝 Напиши варианты через запятую\n"
            "Пример: Да, Нет, Воздержусь\n\n"
            "❌ /cancel - отмена"
        )
        return
    
    if current_state == PollStates.waiting_for_options.state:
        data = await state.get_data()
        question = data.get('question', 'Без вопроса')
        options = [opt.strip() for opt in text.split(',')]
        if len(options) < 2:
            await message.answer("❌ Нужно минимум 2 варианта")
            return
        options_str = '|||'.join(options)
        votes_str = '|||'.join(['0'] * len(options))
        cursor.execute(
            "INSERT INTO polls (question, options, votes, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
            (question, options_str, votes_str, datetime.now().strftime("%d.%m.%Y %H:%M"), 1)
        )
        conn.commit()
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer(
            f"✅ Опрос создан!\n\n{question}\n{', '.join(options)}",
            reply_markup=kb
        )
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"📊 Создан новый опрос: {question}")
        return
    
    if current_state is not None:
        await state.clear()
        kb = admin_kb if is_admin(message.from_user.id) else main_kb
        await message.answer("🔄 Состояние сброшено", reply_markup=kb)
        return
    
    if not is_admin(message.from_user.id):
        kb = main_kb
        await message.answer("🤔 Не понял. Используй кнопки", reply_markup=kb)
        return
    
    # --- НОВЫЕ ИДЕИ ---
    if "Новые идеи" in text:
        cursor.execute("SELECT id, user_id, username, text, created_at FROM ideas WHERE status = 'pending' ORDER BY id DESC")
        ideas = cursor.fetchall()
        if not ideas:
            await message.answer("✅ Новых идей нет", reply_markup=admin_kb)
            return
        for idea in ideas:
            idea_id, user_id, username, text_idea, created_at = idea
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_idea_{idea_id}"),
                    InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_idea_{idea_id}")
                ]
            ])
            await message.answer(
                f"💡 Идея #{idea_id}\n"
                f"От: @{username} (ID: {user_id})\n"
                f"📅 {created_at}\n\n"
                f"{text_idea}",
                reply_markup=keyboard
            )
        return
    
    # --- ОДОБРЕННЫЕ ИДЕИ ---
    if "Одобренные идеи" in text:
        cursor.execute("SELECT id, username, text, created_at FROM ideas WHERE status = 'accepted' ORDER BY id DESC")
        ideas = cursor.fetchall()
        if not ideas:
            await message.answer("✅ Одобренных идей пока нет", reply_markup=admin_kb)
            return
        text_out = "✅ Одобренные идеи:\n\n"
        for idea in ideas:
            idea_id, username, text_idea, created_at = idea
            text_out += f"#{idea_id} от @{username} ({created_at}):\n{text_idea}\n\n"
        await message.answer(text_out[:4000], reply_markup=admin_kb)
        return
    
    # --- ВОПРОСЫ БЕЗ ОТВЕТА ---
    if "Вопросы без ответа" in text:
        cursor.execute("SELECT id, user_id, username, text, created_at FROM questions WHERE answer IS NULL ORDER BY id DESC")
        questions = cursor.fetchall()
        if not questions:
            await message.answer("✅ Вопросов без ответа нет", reply_markup=admin_kb)
            return
        for q in questions:
            q_id, user_id, username, text_q, created_at = q
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Ответить", callback_data=f"answer_question_{q_id}")]
            ])
            await message.answer(
                f"❓ Вопрос #{q_id}\n"
                f"От: @{username} (ID: {user_id})\n"
                f"📅 {created_at}\n\n"
                f"{text_q}",
                reply_markup=keyboard
            )
        return
    
    # --- СОЗДАТЬ ОПРОС ---
    if "Создать опрос" in text:
        await state.set_state(PollStates.waiting_for_question)
        await message.answer(
            "📝 Введи вопрос для опроса\n\n"
            "❌ /cancel - отмена"
        )
        return
    
    # --- ЗАВЕРШИТЬ ОПРОС ---
    if "Завершить опрос" in text:
        cursor.execute("UPDATE polls SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        await message.answer("✅ Все активные опросы завершены", reply_markup=admin_kb)
        return
    
    # --- СТАТИСТИКА ---
    if "Статистика" in text:
        cursor.execute("SELECT COUNT(*) FROM ideas")
        ideas_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ideas WHERE status = 'pending'")
        pending_ideas = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ideas WHERE status = 'accepted'")
        accepted_ideas = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM questions")
        questions_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM questions WHERE answer IS NULL")
        unanswered_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM polls WHERE is_active = 1")
        active_polls = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM music_requests WHERE status = 'pending'")
        pending_music = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM music_requests WHERE status = 'accepted'")
        accepted_music = cursor.fetchone()[0]
        stats_text = (
            f"📊 Статистика:\n\n"
            f"💡 Идей всего: {ideas_count}\n"
            f"   ⏳ На рассмотрении: {pending_ideas}\n"
            f"   ✅ Одобрено: {accepted_ideas}\n"
            f"❓ Вопросов всего: {questions_count}\n"
            f"   ⏳ Без ответа: {unanswered_count}\n"
            f"📊 Активных опросов: {active_polls}\n"
            f"🎵 Заявок на музыку: {pending_music}\n"
            f"   ✅ В плейлисте: {accepted_music}"
        )
        await message.answer(stats_text, reply_markup=admin_kb)
        return
    
    # --- НОВЫЕ ЗАЯВКИ НА МУЗЫКУ ---
    if "Новые заявки" in text:
        cursor.execute("SELECT id, username, song, artist, created_at FROM music_requests WHERE status = 'pending' ORDER BY id DESC")
        requests = cursor.fetchall()
        if not requests:
            await message.answer("✅ Новых заявок нет", reply_markup=admin_kb)
            return
        for req in requests:
            req_id, username, song, artist, created_at = req
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Добавить", callback_data=f"accept_music_{req_id}"),
                    InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_music_{req_id}")
                ]
            ])
            await message.answer(
                f"🎵 Заявка #{req_id}\n"
                f"От: @{username}\n"
                f"Песня: {song}\n"
                f"Исполнитель: {artist}\n"
                f"📅 {created_at}",
                reply_markup=keyboard
            )
        return
    
    # --- ОДОБРЕННЫЕ ПЕСНИ ---
    if "Одобренные песни" in text:
        cursor.execute("SELECT id, username, song, artist, created_at FROM music_requests WHERE status = 'accepted' ORDER BY id DESC")
        songs = cursor.fetchall()
        if not songs:
            await message.answer("🎵 В плейлисте пока нет песен", reply_markup=admin_kb)
            return
        text_out = "🎵 Плейлист (одобренные песни):\n\n"
        for song in songs:
            song_id, username, song_name, artist, created_at = song
            text_out += f"#{song_id} {song_name} - {artist} (от @{username}, {created_at})\n"
        await message.answer(text_out[:4000], reply_markup=admin_kb)
        return
    
    # --- ЕСЛИ НИЧЕГО НЕ ПОДОШЛО ---
    await message.answer("🤔 Не понял. Используй кнопки", reply_markup=admin_kb)

# ===================== КОЛБЭКИ =====================

@dp.callback_query(F.data.startswith("accept_idea_"))
async def accept_idea(callback: CallbackQuery):
    log_callback(callback)
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    idea_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, text FROM ideas WHERE id = ?", (idea_id,))
    result = cursor.fetchone()
    if result:
        user_id, text = result
        cursor.execute("UPDATE ideas SET status = 'accepted' WHERE id = ?", (idea_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n✅ ПРИНЯТО")
        await callback.answer("Идея принята!")
        try:
            await bot.send_message(
                user_id,
                f"🎉 Твоя идея принята!\n\n"
                f"📝 Твоя идея:\n{text}\n\n"
                f"Спасибо за вклад в развитие школы! 🙌"
            )
        except:
            pass

@dp.callback_query(F.data.startswith("reject_idea_"))
async def reject_idea(callback: CallbackQuery):
    log_callback(callback)
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    idea_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, text FROM ideas WHERE id = ?", (idea_id,))
    result = cursor.fetchone()
    if result:
        user_id, text = result
        cursor.execute("UPDATE ideas SET status = 'rejected' WHERE id = ?", (idea_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n❌ ОТКАЗАНО")
        await callback.answer("Идея отклонена")
        try:
            await bot.send_message(
                user_id,
                f"❌ Твоя идея отклонена\n\n"
                f"📝 Твоя идея:\n{text}\n\n"
                f"Попробуй предложить другую! 💡"
            )
        except:
            pass

@dp.callback_query(F.data.startswith("accept_music_"))
async def accept_music(callback: CallbackQuery):
    log_callback(callback)
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    req_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, song, artist FROM music_requests WHERE id = ?", (req_id,))
    result = cursor.fetchone()
    if result:
        user_id, song, artist = result
        cursor.execute("UPDATE music_requests SET status = 'accepted' WHERE id = ?", (req_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n✅ ДОБАВЛЕНО В ПЛЕЙЛИСТ")
        await callback.answer("Трек добавлен!")
        try:
            await bot.send_message(
                user_id,
                f"🎉 Твой трек добавлен в плейлист!\n\n"
                f"🎵 Песня: {song}\n"
                f"🎤 Исполнитель: {artist}\n\n"
                f"Скоро услышишь на перемене! 🎶"
            )
        except:
            pass

@dp.callback_query(F.data.startswith("reject_music_"))
async def reject_music(callback: CallbackQuery):
    log_callback(callback)
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    req_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, song, artist FROM music_requests WHERE id = ?", (req_id,))
    result = cursor.fetchone()
    if result:
        user_id, song, artist = result
        cursor.execute("UPDATE music_requests SET status = 'rejected' WHERE id = ?", (req_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n❌ ОТКАЗАНО")
        await callback.answer("Заявка отклонена")
        try:
            await bot.send_message(
                user_id,
                f"❌ Твоя заявка на музыку отклонена\n\n"
                f"🎵 Песня: {song}\n"
                f"🎤 Исполнитель: {artist}\n\n"
                f"Попробуй другую песню! 🎶"
            )
        except:
            pass

@dp.callback_query(F.data.startswith("vote_"))
async def handle_vote(callback: CallbackQuery):
    log_callback(callback)
    try:
        _, poll_id, option_index = callback.data.split('_')
        poll_id = int(poll_id)
        option_index = int(option_index)
        cursor.execute("SELECT votes FROM polls WHERE id = ?", (poll_id,))
        result = cursor.fetchone()
        if not result:
            await callback.answer("Опрос завершён", show_alert=True)
            return
        votes = result[0].split('|||') if result[0] else []
        if option_index >= len(votes):
            await callback.answer("Ошибка", show_alert=True)
            return
        votes[option_index] = str(int(votes[option_index]) + 1)
        new_votes_str = '|||'.join(votes)
        cursor.execute("UPDATE polls SET votes = ? WHERE id = ?", (new_votes_str, poll_id))
        conn.commit()
        await callback.answer("✅ Голос учтён", show_alert=True)
        cursor.execute("SELECT question, options FROM polls WHERE id = ?", (poll_id,))
        poll_data = cursor.fetchone()
        if not poll_data:
            await callback.answer("Опрос не найден", show_alert=True)
            return
        question, options_str = poll_data
        options = options_str.split('|||')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i, opt in enumerate(options):
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{opt} ({votes[i]})",
                    callback_data=f"vote_{poll_id}_{i}"
                )
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="📊 Результаты", callback_data=f"results_{poll_id}")
        ])
        await callback.message.edit_text(
            f"📊 Опрос:\n\n{question}",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Vote error [{callback.from_user.id}]: {e}")
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("results_"))
async def show_results(callback: CallbackQuery):
    log_callback(callback)
    try:
        _, poll_id = callback.data.split('_')
        poll_id = int(poll_id)
        cursor.execute("SELECT question, options, votes FROM polls WHERE id = ?", (poll_id,))
        result = cursor.fetchone()
        if not result:
            await callback.answer("Опрос не найден", show_alert=True)
            return
        question, options_str, votes_str = result
        options = options_str.split('|||')
        votes = votes_str.split('|||') if votes_str else ['0'] * len(options)
        results_text = f"📊 Результаты:\n\n{question}\n\n"
        total = sum(int(v) for v in votes)
        for i, opt in enumerate(options):
            percent = (int(votes[i]) / total * 100) if total > 0 else 0
            results_text += f"{opt}: {votes[i]} ({percent:.1f}%)\n"
        await callback.message.answer(results_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Results error [{callback.from_user.id}]: {e}")
        await callback.answer("Ошибка", show_alert=True)

async def main():
    logger.info("🚀 Бот парламента «Новое Поколение» запущен!")
    logger.info(f"📊 Администраторы: {ADMIN_IDS}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
        input()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        traceback.print_exc()
        input()
