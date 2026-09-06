import asyncio
import logging
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery

TOKEN = "8942208545:AAH0ZBJIzDYavifVzDKMt3dIPmialCn300g"
ADMIN_IDS = [8973160882]

# ===================== ФУНКЦИЯ МСК =====================
def get_msk_now():
    return datetime.now(timezone(timedelta(hours=3)))


# ===================== ДАННЫЕ =====================
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
    "💻 Платформа: http://olymponline.ru\n"
    "📝 Регистрация: с 3 сентября\n\n"
    "⚠️ Можно выбрать задания за старший класс!\n"
    "⚠️ Информатика - отдельно"
)

# ===================== НАСТРОЙКА ЛОГОВ =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S'
)
logger = logging.getLogger(__name__)
logging.getLogger('aiogram.event').setLevel(logging.WARNING)
logging.getLogger('aiogram.dispatcher').setLevel(logging.WARNING)

# ===================== БАЗА ДАННЫХ =====================
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

# ===================== КЛАВИАТУРЫ =====================
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

# ===================== FSM =====================
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

# ===================== ИНИЦИАЛИЗАЦИЯ =====================
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def log_user(message):
    logger.info(f"👤 [{message.from_user.id}] @{message.from_user.username or 'нет'} | {message.from_user.full_name} | {(message.text or '')[:50]}")

def log_callback(callback):
    logger.info(f"🔄 КОЛБЭК [{callback.from_user.id}] @{callback.from_user.username or 'нет'} | {callback.data}")

def days_until_birthday(birthday_str):
    try:
        birthday_str = birthday_str.replace(",", ".").replace(" ", "")
        birth_date = datetime.strptime(birthday_str, "%d.%m")
        today = get_msk_now().replace(tzinfo=None)
        birth_this_year = datetime(today.year, birth_date.month, birth_date.day)
        if birth_this_year.date() < today.date():
            birth_this_year = datetime(today.year + 1, birth_date.month, birth_date.day)
        days = (birth_this_year.date() - today.date()).days
        return days, birth_this_year
    except Exception as e:
        logger.error(f"Ошибка в days_until_birthday: {e}")
        return None, None

def get_current_lesson():
    try:
        now = get_msk_now().time()
        current_minutes = now.hour * 60 + now.minute
        lessons = [
            {"num": 1, "start": 8*60+0, "end": 8*60+45},
            {"num": 2, "start": 8*60+55, "end": 9*60+40},
            {"num": 3, "start": 9*60+55, "end": 10*60+40},
            {"num": 4, "start": 10*60+55, "end": 11*60+40},
            {"num": 5, "start": 11*60+50, "end": 12*60+35},
            {"num": 6, "start": 12*60+55, "end": 13*60+40},
            {"num": 7, "start": 13*60+50, "end": 14*60+35},
            {"num": 8, "start": 14*60+50, "end": 15*60+35}
        ]
        if current_minutes < lessons[0]["start"]:
            return None, "уроки еще не начались"
        for i, les in enumerate(lessons):
            if les["start"] <= current_minutes <= les["end"]:
                return les["num"], "идет"
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
    except Exception as e:
        logger.error(f"Error in get_current_lesson: {e}")
        return None, "уроков нет"

def get_next_holiday():
    today = get_msk_now().replace(tzinfo=None)
    holiday_dates = {}
    for name, date_str in HOLIDAYS.items():
        try:
            parts = date_str.split(' - ')
            if len(parts) == 2:
                start_str, end_str = parts[0].strip(), parts[1].strip()
                if any(m in start_str for m in ['октября', 'ноября', 'февраля', 'апреля']):
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
    await state.clear()
    welcome = (
        "Привет-привет! 🤗\n\n"
        "Это бот «Новое Поколение» — мы школьный парламент.\n\n"
        "Хочешь изменить школу к лучшему? Просто напиши мне свою идею!\n\n"
        "📌 Что я умею:\n"
        "• Принимать идеи\n"
        "• Отвечать на вопросы\n"
        "• Проводить опросы\n"
        "• Показывать расписание звонков\n"
        "• Рассказывать о каникулах\n"
        "• Показывать расписание питания\n"
        "• Информировать об олимпиаде\n"
        "• Считать дни до дня рождения\n"
        "• Принимать заявки на музыку"
    )
    await message.answer(welcome, reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


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
        "🎵 Для музыки:\n"
        "• Без матов\n"
        "• Исполнители не иноагентами\n"
        "• Только позитивные песни"
    )
    await message.answer(rules, reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


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
    text += "\n🔄 Перемены:\n   • 10 минут\n   • 15 минут / 20 минут (большие)"
    await message.answer(text, reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


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
        text += f"\n⏳ Ближайшие каникулы:\n   📌 {name}\n   Через {days} дней\n   {start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"
    await message.answer(text, reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


# ===================== ПИТАНИЕ =====================
@dp.message(F.text == "🍽 Расписание питания")
async def show_meals(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    text = "🍽 Расписание питания:\n\n"
    for item in MEAL_SCHEDULE:
        text += f"🕐 {item['time']}\n   🍲 {item['meal']}\n   📚 {item['classes']}\n\n"
    await message.answer(text, reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


# ===================== ОЛИМПИАДА =====================
@dp.message(F.text == "🏆 Олимпиада")
async def show_olympiad(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    text = OLYMPIAD_INFO + "\n\n📅 График олимпиады:\n\n"
    for item in OLYMPIAD_SCHEDULE:
        text += f"📌 {item['date']}: {item['subjects']}\n"
    await message.answer(text, reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


# ===================== ДЕНЬ РОЖДЕНИЯ =====================
@dp.message(F.text == "🎂 День рождения")
async def birthday_menu(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    cursor_check = conn.cursor()
    cursor_check.execute("SELECT birthday FROM users WHERE user_id = ?", (message.from_user.id,))
    result = cursor_check.fetchone()
    if result and result[0]:
        days, birth_date = days_until_birthday(result[0])
        if days is None:
            await message.answer("❌ Ошибка в сохраненной дате")
            return
        if days == 0:
            await message.answer(f"🎉 С ДНЁМ РОЖДЕНИЯ, {message.from_user.first_name}! 🥳")
        else:
            await message.answer(f"🎂 До твоего дня рождения осталось {days} дней")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить дату", callback_data="change_birthday")],
            [InlineKeyboardButton(text="🗑 Удалить дату", callback_data="delete_birthday")]
        ])
        await message.answer("Что хочешь сделать?", reply_markup=keyboard)
    else:
        await state.set_state(BirthdayStates.waiting_for_birthday)
        await message.answer("🎂 Введи дату рождения\nФормат: ДД.ММ (Пример: 15.06 или 15,06)\n\n❌ /cancel - отмена")


@dp.callback_query(F.data == "change_birthday")
async def change_birthday(callback: CallbackQuery, state: FSMContext):
    log_callback(callback)
    await state.set_state(BirthdayStates.waiting_for_birthday)
    await callback.message.answer("✏️ Введи новую дату рождения\nФормат: ДД.ММ\n❌ /cancel - отмена")
    await callback.answer()


@dp.callback_query(F.data == "delete_birthday")
async def delete_birthday(callback: CallbackQuery):
    log_callback(callback)
    cursor_del = conn.cursor()
    cursor_del.execute("DELETE FROM users WHERE user_id = ?", (callback.from_user.id,))
    conn.commit()
    await callback.message.answer("🗑 Дата удалена", reply_markup=admin_kb if is_admin(callback.from_user.id) else main_kb)
    await callback.answer()


@dp.message(BirthdayStates.waiting_for_birthday)
async def save_birthday(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return
    birthday_str = message.text.strip()
    days, birth_date = days_until_birthday(birthday_str)
    if days is None:
        await message.answer("❌ Неверный формат! Используй ДД.ММ (например: 15.06 или 15,06)")
        return
    normalized_str = birthday_str.replace(",", ".").replace(" ", "")
    cursor_ins = conn.cursor()
    cursor_ins.execute("INSERT OR REPLACE INTO users (user_id, birthday) VALUES (?, ?)", (message.from_user.id, normalized_str))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ Дата сохранена! До твоего дня рождения осталось {days} дней", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


# ===================== ИДЕИ =====================
@dp.message(F.text == "💡 Подать идею")
async def idea_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await state.set_state(IdeaStates.waiting_for_idea)
    await message.answer("💡 Опиши свою идею\n\n❌ /cancel - отмена")


@dp.message(IdeaStates.waiting_for_idea)
async def idea_receive(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return
    cursor.execute(
        "INSERT INTO ideas (user_id, username, text, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (message.from_user.id, message.from_user.username or "без юзернейма", message.text, "pending", get_msk_now().strftime("%d.%m.%Y %H:%M"))
    )
    conn.commit()
    await state.clear()
    await message.answer("✅ Идея отправлена на рассмотрение! Спасибо!", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"📩 Новая идея\nОт: @{message.from_user.username} (ID: {message.from_user.id})\n\n{message.text}")


# ===================== ВОПРОСЫ =====================
@dp.message(F.text == "❓ Задать вопрос")
async def question_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await state.set_state(QuestionStates.waiting_for_question)
    await message.answer("❓ Напиши свой вопрос\n\n❌ /cancel - отмена")


@dp.message(QuestionStates.waiting_for_question)
async def question_receive(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return
    cursor.execute(
        "INSERT INTO questions (user_id, username, text, is_anonymous, created_at) VALUES (?, ?, ?, ?, ?)",
        (message.from_user.id, message.from_user.username or "Аноним", message.text, 1, get_msk_now().strftime("%d.%m.%Y %H:%M"))
    )
    conn.commit()
    await state.clear()
    await message.answer("✅ Вопрос отправлен!", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"❓ Новый вопрос\nID: {message.from_user.id}\nОт: @{message.from_user.username}\n\n{message.text}")


# ===================== ОПРОСЫ =====================
@dp.message(F.text == "📊 Участвовать в опросе")
async def poll_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    cursor.execute("SELECT id, question, options, votes FROM polls WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    poll = cursor.fetchone()
    if not poll:
        await message.answer("😴 Активных опросов нет", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return
    poll_id, question, options_str, votes_str = poll
    options = options_str.split('|||')
    votes = votes_str.split('|||') if votes_str else ['0'] * len(options)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for i, opt in enumerate(options):
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"{opt} ({votes[i]})", callback_data=f"vote_{poll_id}_{i}")])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="📊 Результаты", callback_data=f"results_{poll_id}")])
    await message.answer(f"📊 Опрос:\n\n{question}", reply_markup=keyboard)


# ===================== МУЗЫКА =====================
@dp.message(F.text == "🎵 Заказать музыку")
async def music_start(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await state.set_state(MusicStates.waiting_for_song)
    await message.answer("🎵 Введи название песни\n\n❌ /cancel - отмена")


@dp.message(MusicStates.waiting_for_song)
async def music_get_song(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return
    await state.update_data(song=message.text)
    await state.set_state(MusicStates.waiting_for_artist)
    await message.answer("🎤 Введи исполнителя\n\n❌ /cancel - отмена")


@dp.message(MusicStates.waiting_for_artist)
async def music_get_artist(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return
    data = await state.get_data()
    song = data.get('song')
    cursor.execute(
        "INSERT INTO music_requests (user_id, username, song, artist, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (message.from_user.id, message.from_user.username or "без юзернейма", song, message.text, "pending", get_msk_now().strftime("%d.%m.%Y %H:%M"))
    )
    conn.commit()
    await state.clear()
    await message.answer(f"✅ Заявка отправлена!\n\n🎵 Песня: {song}\n🎤 Исполнитель: {message.text}", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"🎵 Новая музыка: {song} - {message.text}")


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
    await callback.message.answer(f"✏️ Введи ответ на вопрос #{q_id}\n\n❌ /cancel - отмена")
    await callback.answer()


@dp.message(AnswerStates.waiting_for_answer)
async def process_answer(message: Message, state: FSMContext):
    log_user(message)
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=admin_kb)
        return
    data = await state.get_data()
    q_id = data.get('answer_question_id')
    if not q_id:
        await state.clear()
        await message.answer("❌ Ошибка.")
        return
    cursor.execute("SELECT user_id, text FROM questions WHERE id = ?", (q_id,))
    result = cursor.fetchone()
    if not result:
        await message.answer("❌ Вопрос не найден")
        await state.clear()
        return
    user_id, question_text = result
    cursor.execute(
        "UPDATE questions SET answer = ?, answered_by = ?, answered_at = ? WHERE id = ?",
        (message.text, message.from_user.full_name or "Админ", get_msk_now().strftime("%d.%m.%Y %H:%M"), q_id)
    )
    conn.commit()
    await state.clear()
    try:
        await bot.send_message(user_id, f"📩 Ответ на ваш вопрос\n\n❓ Ваш вопрос:\n{question_text}\n\n💬 Ответ:\n{message.text}")
        await message.answer(f"✅ Ответ отправлен!", reply_markup=admin_kb)
    except:
        await message.answer(f"⚠️ Ответ сохранён, но не отправлен в ЛС.", reply_markup=admin_kb)


# ===================== ОТМЕНА =====================
@dp.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    log_user(message)
    await state.clear()
    await message.answer("❌ Отменено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)


# ===================== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК =====================
@dp.message()
async def handle_all_messages(message: Message, state: FSMContext):
    log_user(message)
    text = message.text.strip()
    current_state = await state.get_state()

    if current_state == PollStates.waiting_for_question.state:
        await state.update_data(question=text)
        await state.set_state(PollStates.waiting_for_options)
        await message.answer("📝 Напиши варианты через запятую\n❌ /cancel - отмена")
        return

    if current_state == PollStates.waiting_for_options.state:
        data = await state.get_data()
        question = data.get('question', 'Без вопроса')
        options = [opt.strip() for opt in text.split(',')]
        if len(options) < 2:
            await message.answer("❌ Нужно минимум 2 варианта")
            return
        cursor.execute(
            "INSERT INTO polls (question, options, votes, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
            (question, '|||'.join(options), '|||'.join(['0'] * len(options)), get_msk_now().strftime("%d.%m.%Y %H:%M"), 1)
        )
        conn.commit()
        await state.clear()
        await message.answer(f"✅ Опрос создан!", reply_markup=admin_kb)
        return

    if current_state is not None:
        await state.clear()
        await message.answer("🔄 Состояние сброшено", reply_markup=admin_kb if is_admin(message.from_user.id) else main_kb)
        return

    if not is_admin(message.from_user.id):
        await message.answer("🤔 Не понял. Используй кнопки", reply_markup=main_kb)
        return

    # --- АДМИН-КОМАНДЫ ---
    if "Новые идеи" in text:
        cursor.execute("SELECT id, user_id, username, text, created_at FROM ideas WHERE status = 'pending' ORDER BY id DESC")
        ideas = cursor.fetchall()
        if not ideas:
            await message.answer("✅ Новых идей нет", reply_markup=admin_kb)
            return
        for idea in ideas:
            idea_id, user_id, username, text_idea, created_at = idea
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_idea_{idea_id}"),
                 InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_idea_{idea_id}")]
            ])
            await message.answer(f"💡 Идея #{idea_id}\nОт: @{username}\n📅 {created_at}\n\n{text_idea}", reply_markup=keyboard)
        return

    if "Одобренные идеи" in text:
        cursor.execute("SELECT id, username, text, created_at FROM ideas WHERE status = 'accepted' ORDER BY id DESC")
        ideas = cursor.fetchall()
        if not ideas:
            await message.answer("✅ Одобренных идей нет", reply_markup=admin_kb)
            return
        text_out = "✅ Одобренные идеи:\n\n"
        for idea in ideas:
            text_out += f"#{idea[0]} от @{idea[1]} ({idea[3]}):\n{idea[2]}\n\n"
        await message.answer(text_out[:4000], reply_markup=admin_kb)
        return

    if "Вопросы без ответа" in text:
        cursor.execute("SELECT id, user_id, username, text, created_at FROM questions WHERE answer IS NULL ORDER BY id DESC")
        questions = cursor.fetchall()
        if not questions:
            await message.answer("✅ Вопросов без ответа нет", reply_markup=admin_kb)
            return
        for q in questions:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Ответить", callback_data=f"answer_question_{q[0]}")]
            ])
            await message.answer(f"❓ Вопрос #{q[0]}\nОт: @{q[2]}\n📅 {q[4]}\n\n{q[3]}", reply_markup=keyboard)
        return

    if "Создать опрос" in text:
        await state.set_state(PollStates.waiting_for_question)
        await message.answer("📝 Введи вопрос для опроса\n❌ /cancel - отмена")
        return

    if "Завершить опрос" in text:
        cursor.execute("UPDATE polls SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        await message.answer("✅ Опросы завершены", reply_markup=admin_kb)
        return

    if "Статистика" in text:
        cursor.execute("SELECT COUNT(*) FROM ideas")
        ideas_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM questions")
        questions_count = cursor.fetchone()[0]
        await message.answer(f"📊 Статистика:\n\n💡 Идей: {ideas_count}\n❓ Вопросов: {questions_count}", reply_markup=admin_kb)
        return

    if "Новые заявки" in text:
        cursor.execute("SELECT id, username, song, artist, created_at FROM music_requests WHERE status = 'pending' ORDER BY id DESC")
        requests = cursor.fetchall()
        if not requests:
            await message.answer("✅ Новых заявок нет", reply_markup=admin_kb)
            return
        for req in requests:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Добавить", callback_data=f"accept_music_{req[0]}"),
                 InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_music_{req[0]}")]
            ])
            await message.answer(f"🎵 Заявка #{req[0]}\nОт: @{req[1]}\nПесня: {req[2]} - {req[3]}", reply_markup=keyboard)
        return

    if "Одобренные песни" in text:
        cursor.execute("SELECT id, username, song, artist FROM music_requests WHERE status = 'accepted' ORDER BY id DESC")
        songs = cursor.fetchall()
        if not songs:
            await message.answer("🎵 Плейлист пуст", reply_markup=admin_kb)
            return
        text_out = "🎵 Одобренные песни:\n\n"
        for s in songs:
            text_out += f"#{s[0]} {s[2]} - {s[3]} (от @{s[1]})\n"
        await message.answer(text_out[:4000], reply_markup=admin_kb)
        return

    await message.answer("🤔 Не понял. Используй кнопки", reply_markup=admin_kb)


# ===================== КОЛБЭКИ =====================
@dp.callback_query(F.data.startswith("accept_idea_"))
async def accept_idea(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    idea_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, text FROM ideas WHERE id = ?", (idea_id,))
    r = cursor.fetchone()
    if r:
        cursor.execute("UPDATE ideas SET status = 'accepted' WHERE id = ?", (idea_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n✅ ПРИНЯТО")
        await callback.answer("Принято!")
        try:
            await bot.send_message(r[0], f"🎉 Твоя идея принята!\n\n📝 Идея:\n{r[1]}")
        except:
            pass


@dp.callback_query(F.data.startswith("reject_idea_"))
async def reject_idea(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    idea_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, text FROM ideas WHERE id = ?", (idea_id,))
    r = cursor.fetchone()
    if r:
        cursor.execute("UPDATE ideas SET status = 'rejected' WHERE id = ?", (idea_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n❌ ОТКАЗАНО")
        await callback.answer("Отклонено")
        try:
            await bot.send_message(r[0], f"❌ Твоя идея отклонена:\n\n{r[1]}")
        except:
            pass


@dp.callback_query(F.data.startswith("accept_music_"))
async def accept_music(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    req_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, song, artist FROM music_requests WHERE id = ?", (req_id,))
    r = cursor.fetchone()
    if r:
        cursor.execute("UPDATE music_requests SET status = 'accepted' WHERE id = ?", (req_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n✅ ДОБАВЛЕНО")
        await callback.answer("Добавлено!")
        try:
            await bot.send_message(r[0], f"🎉 Твой трек {r[1]} - {r[2]} добавлен в плейлист!")
        except:
            pass


@dp.callback_query(F.data.startswith("reject_music_"))
async def reject_music(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    req_id = callback.data.split('_')[2]
    cursor.execute("SELECT user_id, song, artist FROM music_requests WHERE id = ?", (req_id,))
    r = cursor.fetchone()
    if r:
        cursor.execute("UPDATE music_requests SET status = 'rejected' WHERE id = ?", (req_id,))
        conn.commit()
        await callback.message.edit_text(callback.message.text + "\n\n❌ ОТКАЗАНО")
        await callback.answer("Отклонено")
        try:
            await bot.send_message(r[0], f"❌ Твоя заявка на музыку {r[1]} отклонена")
        except:
            pass


@dp.callback_query(F.data.startswith("vote_"))
async def handle_vote(callback: CallbackQuery):
    try:
        _, poll_id, option_index = callback.data.split('_')
        poll_id = int(poll_id)
        option_index = int(option_index)
        cursor.execute("SELECT question, options, votes FROM polls WHERE id = ?", (poll_id,))
        r = cursor.fetchone()
        if not r:
            await callback.answer("Опрос завершён", show_alert=True)
            return
        question, options_str, votes_str = r
        options = options_str.split('|||')
        votes = votes_str.split('|||') if votes_str else ['0'] * len(options)
        if option_index >= len(votes):
            await callback.answer("Ошибка", show_alert=True)
            return
        votes[option_index] = str(int(votes[option_index]) + 1)
        new_votes_str = '|||'.join(votes)
        cursor.execute("UPDATE polls SET votes = ? WHERE id = ?", (new_votes_str, poll_id))
        conn.commit()
        await callback.answer("✅ Голос учтён", show_alert=True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i, opt in enumerate(options):
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"{opt} ({votes[i]})", callback_data=f"vote_{poll_id}_{i}")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="📊 Результаты", callback_data=f"results_{poll_id}")])
        await callback.message.edit_text(f"📊 Опрос:\n\n{question}", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Vote error: {e}")
        await callback.answer("Ошибка", show_alert=True)


@dp.callback_query(F.data.startswith("results_"))
async def show_results(callback: CallbackQuery):
    try:
        poll_id = int(callback.data.split('_')[1])
        cursor.execute("SELECT question, options, votes FROM polls WHERE id = ?", (poll_id,))
        r = cursor.fetchone()
        if not r:
            await callback.answer("Опрос не найден", show_alert=True)
            return
        question, options_str, votes_str = r
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
        logger.error(f"Results error: {e}")


# ===================== ЕЖЕДНЕВНЫЙ ТАЙМЕР =====================
async def check_birthdays_daily():
    while True:
        try:
            now = get_msk_now()
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target_time:
                target_time += timedelta(days=1)
            await asyncio.sleep((target_time - now).total_seconds())

            current_date_str = get_msk_now().strftime("%d.%m")
            cursor_check = conn.cursor()
            cursor_check.execute("SELECT user_id FROM users WHERE birthday = ?", (current_date_str,))
            for row in cursor_check.fetchall():
                try:
                    await bot.send_message(
                        row[0],
                        "🎉 С ДНЁМ РОЖДЕНИЯ! 🥳\n\n"
                        "Весь наш школьный парламент «Новое Поколение» поздравляет тебя! "
                        "Желаем крутого настроения, верных друзей и лёгкой учёбы! "
                        "Ты делаешь нашу школу лучше! 💖"
                    )
                except:
                    pass
        except Exception as e:
            logger.error(f"Error in birthday timer: {e}")
            await asyncio.sleep(60)


# ===================== ЗАПУСК =====================
async def main():
    logger.info("🚀 Бот парламента «Новое Поколение» запущен!")
    asyncio.create_task(check_birthdays_daily())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
