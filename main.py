import telebot
import requests
import sqlite3
import re
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7573166092:AAFHN99hMgiuxWLEsuyQt5FQx7qRQNo1ywg"

# نام هوش مصنوعی
AI_NAME = "Hidro AI"

# لیست کلمات ممنوعه
FORBIDDEN_WORDS = ["اسم", "کلمه‌ممنوعه۲", "لینک", "Pollinations.AI", "Poly", "پلی", "2023"]

# مسیر فولدر موزیک
MUSIC_FOLDER = "Muzic"  # مسیر فولدر موزیک را تنظیم کنید

# دیکشنری برای ذخیره تاریخچه مکالمات هر کاربر
user_memory = {}

# ایجاد پایگاه داده برای حافظه
def init_db():
    conn = sqlite3.connect('bot_memory.db')
    c = conn.cursor()
    
    # ایجاد جدول memory اگر وجود نداشته باشد
    c.execute('''CREATE TABLE IF NOT EXISTS memory
                 (user_id INTEGER, chat_id INTEGER, mode TEXT, data TEXT)''')
    
    # بررسی وجود ستون‌های جدید و اضافه کردن آن‌ها در صورت نیاز
    c.execute("PRAGMA table_info(memory)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'mode' not in columns:
        c.execute("ALTER TABLE memory ADD COLUMN mode TEXT")
    if 'data' not in columns:
        c.execute("ALTER TABLE memory ADD COLUMN data TEXT")
    
    conn.commit()
    conn.close()

# ذخیره اطلاعات در پایگاه داده
def save_memory(user_id, chat_id, mode, data=None):
    conn = sqlite3.connect('bot_memory.db')
    c = conn.cursor()
    c.execute("INSERT INTO memory (user_id, chat_id, mode, data) VALUES (?, ?, ?, ?)", 
              (user_id, chat_id, mode, data))
    conn.commit()
    conn.close()

# بازیابی اطلاعات از پایگاه داده
def get_memory(user_id, chat_id):
    conn = sqlite3.connect('bot_memory.db')
    c = conn.cursor()
    c.execute("SELECT mode, data FROM memory WHERE user_id = ? AND chat_id = ? ORDER BY ROWID DESC LIMIT 1", 
              (user_id, chat_id))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None)

# ChatGPT 4.0
def ask_chatgpt(question):
    url = "https://open.wiki-api.ir/apis-1/ChatGPT-4o"
    params = {"q": question}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("status"):
            return data.get("results")
    return "متاسفانه مشکلی در دریافت پاسخ رخ داد."

# ساخت عکس با هوش مصنوعی (ساده)
def generate_photo(prompt):
    url = "https://open.wiki-api.ir/apis-1/MakePhotoAi"
    params = {"q": prompt}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("status"):
            return data.get("results").get("img")
    return None

# ساخت عکس پیشرفته (Pro)
def generate_pro_photo(prompt, width=768, height=768, model='flux', seed=None):
    url = f"https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true"
    response = requests.get(url)
    if response.status_code == 200:
        image_path = 'generated_image.jpg'
        with open(image_path, 'wb') as file:
            file.write(response.content)
        return image_path
    return None

# تبدیل متن به صدا
def text_to_voice(text, voice="male"):
    url = "https://open.wiki-api.ir/apis-1/TextToVoice"
    params = {"text": text, "voice": voice}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("status"):
            return data.get("results").get("url")
    return None

# جستجوی فیلم
def search_movies(query):
    url = "https://open.wiki-api.ir/apis-1/UptvsSearch"
    params = {"q": query}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("status"):
            return data.get("results")
    return None

# تحلیل تصویر با استفاده از Pollinations.ai
def analyze_image(image_url, user_question):
    response = requests.post('https://text.pollinations.ai/openai', json={
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_question},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ],
        "model": "openai"
    })
    return response.json()

# تابع برای بررسی محتوای پاسخ هوش مصنوعی
def contains_forbidden_content(text):
    # بررسی کلمات ممنوعه
    for word in FORBIDDEN_WORDS:
        if word.lower() in text.lower():
            return True

    # بررسی لینک‌ها (با استفاده از regex)
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.search(text):
        return True

    return False

# تابع برای ارسال درخواست به API هوش مصنوعی
def get_ai_response(user_id, message):
    # اگر کاربر قبلاً پیامی فرستاده باشد، تاریخچه مکالمه را اضافه کنید
    if user_id in user_memory:
        conversation = user_memory[user_id]
    else:
        conversation = []

    # اضافه کردن پیام جدید به تاریخچه مکالمه
    conversation.append({"role": "user", "content": message})

    # ارسال درخواست به API هوش مصنوعی
    url = "https://text.pollinations.ai/"  # آدرس API هوش مصنوعی را جایگزین کنید
    payload = {
        "messages": conversation
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY"  # کلید API خود را جایگزین کنید
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # بررسی خطاهای HTTP

        # بررسی نوع پاسخ (JSON یا متن ساده)
        if response.headers.get('Content-Type', '').startswith('application/json'):
            # اگر پاسخ JSON است
            response_json = response.json()
            ai_message = response_json.get("choices")[0].get("message").get("content")
        else:
            # اگر پاسخ متن ساده است
            ai_message = response.text

        # اضافه کردن پاسخ هوش مصنوعی به تاریخچه مکالمه
        conversation.append({"role": "assistant", "content": ai_message})
        user_memory[user_id] = conversation  # به‌روزرسانی تاریخچه مکالمه
        return ai_message
    except requests.exceptions.RequestException as e:
        # مدیریت خطاهای ارتباطی
        print(f"خطا در ارتباط با API: {e}")
        return "خطا در ارتباط با سرور. لطفاً بعداً تلاش کنید."
    except (KeyError, IndexError, ValueError) as e:
        # مدیریت خطاهای JSON یا ساختار پاسخ
        print(f"خطا در پردازش پاسخ API: {e}")
        return "خطا در پردازش پاسخ سرور."

# تابع برای بررسی سلام کاربر و پاسخ مناسب
def handle_greeting(message):
    greetings = ["hi", "سلام", "سازنده"]
    user_text = message.text.lower()  # متن پیام کاربر را به حروف کوچک تبدیل کنید

    # بررسی آیا پیام کاربر شامل سلام است
    for greeting in greetings:
        if greeting in user_text:
            return True
    return False

# تابع برای ارسال موزیک
def send_music(message):
    # مسیر فایل موزیک
    music_file = os.path.join(MUSIC_FOLDER, "Null.mp3")  # نام فایل موزیک را تنظیم کنید

    # بررسی وجود فایل موزیک
    if os.path.exists(music_file):
        try:
            # ارسال فایل موزیک
            with open(music_file, 'rb') as audio:
                bot.send_audio(message.chat.id, audio)
            print("موزیک با موفقیت ارسال شد.")
        except Exception as e:
            print(f"خطا در ارسال موزیک: {e}")
            bot.reply_to(message, "خطا در ارسال موزیک. لطفاً بعداً تلاش کنید.")
    else:
        print("فایل موزیک پیدا نشد.")
        bot.reply_to(message, "موزیک مورد نظر یافت نشد.")

# ایجاد ربات
bot = telebot.TeleBot(BOT_TOKEN)

# دستور شروع
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("پاسخ به سوالات", callback_data="ask_question"))
    markup.add(InlineKeyboardButton("ساخت عکس (ساده)", callback_data="generate_photo"))
    markup.add(InlineKeyboardButton("ساخت عکس (Pro)", callback_data="generate_pro_photo"))
    markup.add(InlineKeyboardButton("تبدیل متن به صدا", callback_data="text_to_voice"))
    markup.add(InlineKeyboardButton("جستجوی فیلم", callback_data="search_movies"))
    markup.add(InlineKeyboardButton("دریافت پاسخ با ارسال عکس", callback_data="analyze_image"))
    markup.add(InlineKeyboardButton("گفتگو با دستیار هوش مصنوعی (Normal)", callback_data="ai_chat"))
    bot.send_message(message.chat.id, "سلام! من ربات چندمنظوره هستم. می‌توانید از من برای:\n"
                                     "1. پاسخ به سوالات (ChatGPT)\n"
                                     "2. ساخت عکس ساده\n"
                                     "3. ساخت عکس پیشرفته (Pro)\n"
                                     "4. تبدیل متن به صدا\n"
                                     "5. جستجوی فیلم\n"
                                     "6. دریافت پاسخ با ارسال عکس\n"
                                     "7. گفتگو با دستیار هوش مصنوعی (Normal)\nاستفاده کنید.", reply_markup=markup)

# مدیریت کلیک روی دکمه‌ها
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if call.data == "ask_question":
        bot.send_message(chat_id, "لطفاً سوال خود را بپرسید:")
        save_memory(user_id, chat_id, "ask_question")
    elif call.data == "generate_photo":
        bot.send_message(chat_id, "لطفاً متنی برای ساخت عکس ساده وارد کنید:")
        save_memory(user_id, chat_id, "generate_photo")
    elif call.data == "generate_pro_photo":
        bot.send_message(chat_id, "لطفاً متنی برای ساخت عکس پیشرفته (Pro) وارد کنید:")
        save_memory(user_id, chat_id, "generate_pro_photo")
    elif call.data == "text_to_voice":
        bot.send_message(chat_id, "لطفاً متنی که می‌خواهید به صدا تبدیل شود را وارد کنید:")
        save_memory(user_id, chat_id, "text_to_voice_text")
    elif call.data == "search_movies":
        bot.send_message(chat_id, "لطفاً کلمه کلیدی برای جستجوی فیلم وارد کنید:")
        save_memory(user_id, chat_id, "search_movies")
    elif call.data == "analyze_image":
        bot.send_message(chat_id, "لطفاً سوال خود را بپرسید:")
        save_memory(user_id, chat_id, "analyze_image_question")
    elif call.data == "ai_chat":
        bot.send_message(chat_id, "شما در حال گفتگو با دستیار هوش مصنوعی (Normal) هستید. هر سوالی دارید بپرسید:")
        save_memory(user_id, chat_id, "ai_chat")

# پاسخ به پیام‌های کاربران
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    # بازیابی حالت فعلی کاربر
    mode, data = get_memory(user_id, chat_id)

    if mode == "ask_question":
        response = ask_chatgpt(text)
        bot.send_message(chat_id, response)
        # حالت را تغییر ندهید تا کاربر بتواند سوالات بیشتری بپرسد
    elif mode == "generate_photo":
        photo_url = generate_photo(text)
        if photo_url:
            bot.send_photo(chat_id, photo_url)
        else:
            bot.send_message(chat_id, "متاسفانه مشکلی در تولید عکس رخ داد.")
        # حالت را تغییر ندهید تا کاربر بتواند عکس‌های بیشتری بسازد
    elif mode == "generate_pro_photo":
        image_path = generate_pro_photo(text)
        if image_path:
            bot.send_photo(chat_id, photo=open(image_path, 'rb'))
        else:
            bot.send_message(chat_id, "متاسفانه مشکلی در تولید عکس پیشرفته رخ داد.")
        # حالت را تغییر ندهید تا کاربر بتواند عکس‌های بیشتری بسازد
    elif mode == "text_to_voice_text":
        save_memory(user_id, chat_id, "text_to_voice_voice", text)  # ذخیره متن و درخواست نوع صدا
        bot.send_message(chat_id, "لطفاً نوع صدا را وارد کنید (مثلاً male، female یا هر چیز دیگری):")
    elif mode == "text_to_voice_voice":
        audio_url = text_to_voice(data, text)  # استفاده از متن ذخیره‌شده و نوع صدا
        if audio_url:
            bot.send_audio(chat_id, audio_url)
        else:
            bot.send_message(chat_id, "متاسفانه مشکلی در تبدیل متن به صدا رخ داد.")
        # حالت را تغییر ندهید تا کاربر بتواند متن‌های بیشتری تبدیل کند
    elif mode == "search_movies":
        movies = search_movies(text)
        if movies:
            for movie in movies:
                response = (
                    f"**عنوان**: {movie['title']}\n"
                    f"**ژانرها**: {', '.join(movie['genres'])}\n"
                    f"**امتیاز**: {movie['rating']}\n"
                    f"**توضیحات**: {movie['description']}\n"
                    f"**لینک**: [مشاهده فیلم]({movie['url']})"
                )
                bot.send_message(chat_id, response, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "متاسفانه هیچ فیلمی یافت نشد.")
        # حالت را تغییر ندهید تا کاربر بتواند فیلم‌های بیشتری جستجو کند
    elif mode == "analyze_image_question":
        save_memory(user_id, chat_id, "analyze_image_image", text)  # ذخیره سوال و درخواست تصویر
        bot.send_message(chat_id, "لطفاً یک تصویر ارسال کنید.")
    elif mode == "ai_chat":
        # دریافت پاسخ از API هوش مصنوعی
        ai_response = get_ai_response(user_id, text)

        # بررسی پاسخ هوش مصنوعی
        if contains_forbidden_content(ai_response):
            bot.reply_to(message, "Hidro :)")
        else:
            # ارسال پاسخ به کاربر
            bot.reply_to(message, ai_response)
    else:
        bot.send_message(chat_id, "لطفاً یک گزینه از منو انتخاب کنید.")

# هندلر برای دریافت تصویر از کاربر
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # بازیابی حالت فعلی کاربر
    mode, data = get_memory(user_id, chat_id)

    if mode == "analyze_image_image":
        # دریافت اطلاعات تصویر
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        # تحلیل تصویر با استفاده از Pollinations.ai
        user_question = data
        try:
            result = analyze_image(file_url, user_question)
            analysis_result = result['choices'][0]['message']['content']
            bot.send_message(chat_id, analysis_result)  # ارسال نتیجه به کاربر
        except Exception as e:
            bot.send_message(chat_id, f"متأسفم، خطایی رخ داد: {e}")

        # بازگشت به حالت عادی
        save_memory(user_id, chat_id, "idle")
    else:
        bot.send_message(chat_id, "لطفاً ابتدا سوال خود را ارسال کنید.")

# اجرای ربات
print("ربات شروع به کار کرد...")
init_db()
bot.polling()