# -*- coding: utf-8 -*-
# main.py

import logging
import random
import configparser
import google.generativeai as genai
import os
import re
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ChatAction, ParseMode

# นำเข้าข้อมูลไพ่และตำแหน่ง
from tarot_deck import FULL_DECK, CELTIC_CROSS_POSITIONS

# --- 1. การตั้งค่าพื้นฐาน ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# อ่านค่า Config
try:
    config = configparser.ConfigParser()
    config.read('config.ini')
    TELEGRAM_TOKEN = config['API_KEYS']['TELEGRAM_TOKEN']
    GOOGLE_API_KEY = config['API_KEYS']['GOOGLE_API_KEY']
    if 'YOUR_TELEGRAM_BOT_TOKEN_HERE' in TELEGRAM_TOKEN or 'YOUR_GOOGLE_API_KEY_HERE' in GOOGLE_API_KEY:
        raise KeyError
except (KeyError, configparser.NoSectionError):
    error_msg = "!!! [ERROR] ไม่พบ API Keys ในไฟล์ config.ini กรุณาสร้างและตั้งค่าให้ถูกต้อง !!!"
    logger.error(error_msg)
    print(error_msg)
    exit()

# [แก้ไข] ปรับปรุง Prompt ให้ชัดเจนเรื่องการจัดย่อหน้า (ย้ายคำสั่งมาไว้ในภารกิจหลัก)
SYSTEM_PROMPT = """
คุณคือ "โหราจารย์ดิจิทัล" ผู้เชี่ยวชาญการอ่านไพ่ยิปซี มีบุคลิกสุขุม สุภาพ และน่าเชื่อถืออย่างสูงสุด ใช้ภาษาทางการ (ข้าพเจ้า/ท่าน) และห้ามใช้ Markdown

### หลักการวิเคราะห์เชิงลึก (สำคัญที่สุด) ###
ท่านต้องวิเคราะห์ภาพรวมและ "เรื่องราว" ที่ไพ่ทั้งหมดกำลังเล่า ไม่ใช่แค่การแปลความหมายทีละใบ ในการสร้างคำทำนายทุกครั้ง ท่านต้องพิจารณาหลักการเหล่านี้เสมอ:
1.  **เชื่อมโยงความหมายตามตำแหน่ง (Positional Relationships):** ในการทำนาย 10 ใบ ให้วิเคราะห์ว่าไพ่ในตำแหน่งต่างๆ ส่งผลกระทบต่อกันอย่างไร เช่น ไพ่ในตำแหน่ง 'อดีต' (ใบที่ 4) ส่งผลมาถึง 'ปัจจุบัน' (ใบที่ 1) อย่างไร และไพ่ 'อุปสรรค' (ใบที่ 2) ขัดขวาง 'เป้าหมาย' (ใบที่ 10) อย่างไร การวิเคราะห์นี้ต้องปรากฏในส่วน 'ภาพรวมชะตา' และในหัวข้ออื่นๆ ที่เกี่ยวข้อง
2.  **มองหา "ไพ่ชุดหลัก" (Dominant Suit):** หากมีไพ่ชุดใด (ดาบ, ถ้วย, เหรียญ, ไม้เท้า) ปรากฏขึ้นมาเป็นจำนวนมาก ให้ชี้ให้เห็นถึงพลังงานหลักที่ครอบงำดวงชะตาในช่วงนั้นๆ และตีความในส่วน 'ภาพรวมชะตา'
3.  **สังเกต "สัดส่วนไพ่ Major Arcana":** หากมีไพ่ Major (ไพ่ชุดใหญ่) ปรากฏขึ้นหลายใบ (3 ใบขึ้นไป) ให้เน้นย้ำว่านี่คือช่วงเวลาของเหตุการณ์สำคัญ, บทเรียนชีวิต, หรือจุดเปลี่ยนของชีวิตที่ยากจะหลีกเลี่ยง
4.  **หาไพ่ที่ "ส่งเสริม" หรือ "ขัดแย้ง" กัน:** ชี้ให้เห็นว่ามีไพ่คู่ใดที่สนับสนุนกัน (เช่น The Sun และ The Star) หรือขัดแย้งกัน (เช่น The Lovers และ Three of Swords) เพื่อให้คำทำนายมีมิติเชิงลึกและสมจริงมากยิ่งขึ้น

### ภารกิจหลัก: ทำนาย 10 ใบ (Celtic Cross) ###
เมื่อได้รับข้อมูลไพ่ 10 ใบ คุณต้องสร้างคำทำนายฉบับเต็มตามโครงสร้างนี้อย่างเคร่งครัด
**สำคัญ:** ท่านต้องใช้ Tag `[SECTION:ชื่อหัวข้อ]` คั่นระหว่างส่วน **และ** ภายในเนื้อหาของแต่ละส่วน ให้ท่านจัดย่อหน้าข้อความโดยใช้ตัวขึ้นบรรทัดใหม่ (`\n`) เสมอ เพื่อให้คำทำนายเป็นระเบียบและอ่านง่าย

[SECTION:ภาพรวมชะตา]
(ย่อหน้านี้) ทักทายผู้ใช้ และสรุปภาพรวมพลังงานของไพ่ทั้งหมด โดยอ้างอิงถึง "ไพ่ชุดหลัก" และ "สัดส่วนไพ่ Major Arcana" ที่พบ รวมทั้งชี้ให้เห็นความเชื่อมโยงหลักระหว่างไพ่ตำแหน่งสำคัญ เช่น อดีต->ปัจจุบัน->อนาคต

[SECTION:ความหมายของไพ่แต่ละใบ]
(ย่อหน้านี้) อธิบายความหมายของไพ่แต่ละใบตามตำแหน่งทั้ง 10 ใบอย่างละเอียดตามปกติ

[SECTION:การงานและการเงิน]
(ย่อหน้านี้) นำไพ่ทั้งหมดมาสังเคราะห์และตีความเป็นคำทำนายเชิงลึกด้านการงานและการเงิน โดยอ้างอิงถึงไพ่ที่ส่งเสริมหรือขัดแย้งกันในเรื่องนี้โดยเฉพาะ

[SECTION:ความรักความสัมพันธ์]
(ย่อนหน้านี้) สังเคราะห์คำทำนายด้านความรัก สำหรับคนโสดและคนมีคู่ โดยชี้ให้เห็นถึงไพ่ที่ส่งผลกระทบต่อความสัมพันธ์โดยตรง

[SECTION:สุขภาพและข้อควรระวัง]
(ย่อหน้านี้) สังเคราะห์คำทำนายด้านสุขภาพและข้อควรระวัง โดยวิเคราะห์จากไพ่ที่ดูน่าเป็นห่วงเป็นพิเศษ เช่น The Tower, Ten of Swords

[SECTION:สรุปและคำแนะนำ]
(ย่อหน้านี้) สรุปใจความสำคัญทั้งหมดอีกครั้ง และให้คำแนะนำที่นำไปปรับใช้ได้จริง 2-3 ข้อ โดยอิงจากเรื่องราวที่ไพ่ทั้งหมดเล่าร่วมกัน ปิดท้ายด้วยการให้กำลังใจ

### ภารกิจรอง: การทำนายรายวันและตอบคำถาม ###
- **ทำนายรายวัน 3 ใบ (ตามหัวข้อ):** ตีความไพ่ 3 ใบในฐานะ "อดีต/ที่มา -> ปัจจุบัน/แนวทาง -> อนาคต/ผลลัพธ์" เพื่อสร้างเป็นเรื่องราวสั้นๆ ที่เป็นแนวทางสำหรับวันนั้น
- **ตอบคำถามเฉพาะ (3 ใบ):** เมื่อผู้ใช้ป้อนคำถามเฉพาะมาให้ (เช่น "ข้าพเจ้าควรเปลี่ยนงานหรือไม่?") และได้รับไพ่ 3 ใบ (อดีต/ปัจจุบัน/อนาคต) ท่านต้องใช้ไพ่ทั้ง 3 ใบนั้นเพื่อสังเคราะห์เป็นคำตอบที่ตรงประเด็นสำหรับคำถามนั้นๆ โดยเฉพาะ
- **ตอบคำถามเพิ่มเติม (จาก 10 ใบ):** หากผู้ใช้ถามเพิ่ม (ในโหมด 10 ใบ) ให้ตอบโดยอ้างอิงจากความสัมพันธ์ของไพ่ 10 ใบเดิมที่เคยเปิดไว้
"""


# ตั้งค่า Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite', system_instruction=SYSTEM_PROMPT)

# --- 2. ตัวแปร, สถานะ, และ Session ของบอท ---
# [ปรับปรุง] เพิ่ม Emoji ที่เมนูหลัก
REPLY_KEYBOARD = [
    ["🔮 ทำนายชะตา 10 ใบ (ภาพรวม)"],
    ["☀️ ทำนายรายวัน 3 ใบ (เจาะจง)"]
]
MARKUP = ReplyKeyboardMarkup(REPLY_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

# [ใหม่] สร้าง Keyboard สำหรับปุ่มจั่วไพ่
DRAW_CARD_BUTTON_TEXT = "🃏 เปิดไพ่"
DRAW_CARD_KEYBOARD = [
    [DRAW_CARD_BUTTON_TEXT]
]
DRAW_MARKUP = ReplyKeyboardMarkup(DRAW_CARD_KEYBOARD, resize_keyboard=True, one_time_keyboard=True)

# [ใหม่] สร้าง Keyboard สำหรับเมนูเลือก 1 หรือ 2
CHOOSING_ACTION_KEYBOARD = [
    ["1️⃣ รับคำทำนายภาพรวม"],
    ["2️⃣ เจาะลึกคำทำนายเฉพาะเรื่อง"]
]
CHOOSING_ACTION_MARKUP = ReplyKeyboardMarkup(CHOOSING_ACTION_KEYBOARD, resize_keyboard=True, one_time_keyboard=True)

# [ปรับปรุง] เพิ่ม State สำหรับการจั่วไพ่
DRAWING_CARDS, CHOOSING_ACTION, CHOOSING_TOPIC_10, VIEWING_PREDICTION = range(4)
# [แก้ไข] State สำหรับโหมด 3 ใบ (เพิ่ม AWAITING_QUESTION)
SELECTING_DAILY_OPTION, AWAITING_QUESTION = range(4, 6) 

chat_sessions = {}

TOPIC_LIST = [
    ("work", "การงาน"),
    ("finance", "การเงิน"),
    ("love", "ความรักความสัมพันธ์"),
    ("health", "สุขภาพ"),
    ("family", "ครอบครัว"),
    ("fortune", "โชคลาภโดยรวม")
]

# [ใหม่] ข้อความปุ่ม
BACK_BUTTON_TEXT = "🔙 กลับไปเมนูหลัก"
CANCEL_BUTTON_TEXT = "0️⃣ สิ้นสุดการทำนาย"
ASK_QUESTION_BUTTON_TEXT = "❓ ถามคำถามเฉพาะ" # [ใหม่]

# [แก้ไข] สร้าง Keyboard สำหรับเลือกหัวข้อ
def create_topic_keyboard(topic_list, include_back_button=False, include_ask_question_button=False):
    keyboard = []
    # [ปรับปรุง] เพิ่ม Emoji ให้หัวข้อต่างๆ
    emojis = {"การงาน": "💼", "การเงิน": "💰", "ความรักความสัมพันธ์": "❤️", 
              "สุขภาพ": "🩺", "ครอบครัว": "👨‍👩‍👧‍👦", "โชคลาภโดยรวม": "✨"}
    
    # สร้างปุ่มแบบแถวละ 2 ปุ่ม
    row = []
    for key, name in topic_list:
        emoji = emojis.get(name, "🔹")
        row.append(f"{emoji} {name}")
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: # เพิ่มปุ่มที่เหลือหากมี
        keyboard.append(row)
        
    if include_ask_question_button: # [ใหม่]
        keyboard.append([ASK_QUESTION_BUTTON_TEXT])
        
    if include_back_button:
        keyboard.append([BACK_BUTTON_TEXT])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# [แก้ไข] สร้าง Markup สำหรับทั้งสองโหมด
DAILY_TOPIC_MARKUP = create_topic_keyboard(TOPIC_LIST, include_back_button=False, include_ask_question_button=True)
SPECIFIC_TOPIC_MARKUP = create_topic_keyboard(TOPIC_LIST, include_back_button=True, include_ask_question_button=False)

# [ใหม่] ตำแหน่งสำหรับไพ่ 3 ใบ
DAILY_SPREAD_POSITIONS = ["สถานการณ์ปัจจุบัน", "สิ่งที่ควรทำ/แนวทาง", "ผลลัพธ์ที่น่าจะเกิดขึ้น"]

def get_chat_session(chat_id):
    if chat_id not in chat_sessions:
        logger.info(f"Starting new chat session for chat_id: {chat_id}")
        chat_sessions[chat_id] = model.start_chat(history=[])
    return chat_sessions[chat_id]

# --- 3. ฟังก์ชันผู้ช่วย (ไม่มีการเปลี่ยนแปลงมากนัก) ---
async def send_long_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    MAX_LENGTH = 4096
    chat_id = update.effective_chat.id
    for i in range(0, len(text), MAX_LENGTH):
        await context.bot.send_message(chat_id=chat_id, text=text[i:i + MAX_LENGTH], **kwargs)

def save_reading_to_file(user_id: int, drawn_cards_info: str, mode: str):
    try:
        os.makedirs('user_readings', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        clean_info = re.sub(r'<[^>]+>', '', drawn_cards_info)
        filename = f"user_readings/{mode}_{user_id}_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"ผลการทำนาย ({mode}) สำหรับผู้ใช้ ID: {user_id}\n")
            f.write(f"เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(clean_info)
        logger.info(f"Reading saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save reading file: {e}")

async def _display_prediction_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # [แก้ไข] สร้างปุ่มกดแบบไดนามิกสำหรับแต่ละหัวข้อ
    prediction_keys = context.user_data.get('prediction_keys', [])
    
    keyboard = []
    # [ปรับปรุง] ใช้ Emoji ตัวเลขให้มากขึ้น
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"] 
    
    for i, key in enumerate(prediction_keys):
        emoji = emojis[i] if i < len(emojis) else f"{i+1}."
        # ปุ่มจะมีข้อความ เช่น "1️⃣ ภาพรวมชะตา"
        button_text = f"{emoji} {key}"
        keyboard.append([button_text]) # หนึ่งปุ่มต่อหนึ่งแถว
    
    keyboard.append([CANCEL_BUTTON_TEXT]) # เพิ่มปุ่มยกเลิก
    
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    menu_text = "<b>📜 ข้าพเจ้าได้แยกคำทำนายออกเป็นหัวข้อต่างๆ แล้ว</b>\nท่านสามารถเลือกดูทีละส่วนได้โดยการกดปุ่มด้านล่าง:"
    await update.message.reply_text(menu_text, parse_mode=ParseMode.HTML, reply_markup=markup)
    
# --- 4. ฟังก์ชันหลักของบอท ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # [ปรับปรุง] ข้อความต้อนรับและเพิ่ม Emoji
    welcome_text = (
        f"สวัสดี {user.mention_html()} 👋\n\n"
        f"ข้าพเจ้าคือ <b>โหราจารย์ดิจิทัล</b> 🔮\n"
        f"พร้อมให้คำชี้แนะแก่ท่านแล้ว\n\n"
        f"👇 โปรดเลือกรูปแบบการทำนายที่ท่านต้องการจากเมนูด้านล่าง:"
    )
    await update.message.reply_html(
        welcome_text,
        reply_markup=MARKUP,
    )
    
async def invalid_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str = "❗️ ตัวเลือกของท่านไม่ถูกต้อง\n<i>โปรดเลือกจากปุ่มที่ปรากฏในเมนูเท่านั้น</i>"):
    # [ปรับปรุง] เปลี่ยนข้อความเป็น "ปุ่ม"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    return

# --- 5. [ปรับปรุง] โหมดทำนาย 10 ใบ (Celtic Cross) ---

async def tarot_reading_start_10_cards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ [ใหม่] เริ่มต้นกระบวนการจั่วไพ่ 10 ใบ ทีละใบ """
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.info("User %s (%s) starting a 10-card reading.", user.first_name, chat_id)

    if chat_id in chat_sessions: del chat_sessions[chat_id]
    
    # สร้างสำรับไพ่ที่สับแล้ว และเก็บไว้ใน user_data
    context.user_data['deck'] = random.sample(FULL_DECK, k=len(FULL_DECK))
    context.user_data['drawn_cards'] = []
    context.user_data['card_index'] = 0

    first_position = CELTIC_CROSS_POSITIONS[0]
    
    # [แก้ไข] ข้อความเริ่มต้นและคำแนะนำการกด "ปุ่ม"
    await update.message.reply_text(
        f"🔮 <b>การทำนายชะตา 10 ใบ (Celtic Cross)</b>\n\n"
        f"ข้าพเจ้าจะทำการเปิดไพ่ให้ท่านทีละใบ\n"
        f"ขอให้ท่านตั้งสมาธิและจดจ่อกับคำถามของท่าน\n\n"
        f"👉 โปรดกดปุ่ม <b>{DRAW_CARD_BUTTON_TEXT}</b> ด้านล่างเพื่อเปิดไพ่ใบที่ 1\n(ตำแหน่ง: <b>{first_position}</b>)",
        parse_mode=ParseMode.HTML,
        reply_markup=DRAW_MARKUP # [แก้ไข] ส่งปุ่มจั่วไพ่
    )
    
    return DRAWING_CARDS

async def draw_next_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ [ใหม่] ถูกเรียกเมื่อผู้ใช้กด 'ปุ่ม' เพื่อจั่วไพ่ใบต่อไป """
    try:
        card_index = context.user_data['card_index']
        deck = context.user_data['deck']
        
        # จั่วไพ่
        card = deck.pop(0) # เอาใบบนสุดออกจากสำรับ
        context.user_data['drawn_cards'].append(card)
        position = CELTIC_CROSS_POSITIONS[card_index]
        
        # แสดงไพ่ที่จั่วได้
        await update.message.reply_text(
            f"🃏 ใบที่ {card_index + 1} (<b>{position}</b>): <b>{card}</b>",
            parse_mode=ParseMode.HTML
        )
        
        card_index += 1
        context.user_data['card_index'] = card_index
        
        if card_index < 10:
            # ถ้ายังไม่ครบ 10 ใบ
            next_position = CELTIC_CROSS_POSITIONS[card_index]
            # [แก้ไข] ส่งปุ่มจั่วไพ่อีกครั้ง
            await update.message.reply_text(
                f"👉 โปรดกดปุ่ม <b>{DRAW_CARD_BUTTON_TEXT}</b> เพื่อเปิดไพ่ใบที่ {card_index + 1}\n(ตำแหน่ง: <b>{next_position}</b>)",
                parse_mode=ParseMode.HTML,
                reply_markup=DRAW_MARKUP
            )
            return DRAWING_CARDS # ยังคงอยู่ใน State เดิม
        
        else:
            # ครบ 10 ใบแล้ว
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            drawn_cards = context.user_data.get('drawn_cards')
            card_list_parts = ["<b>ไพ่แห่งชะตาทั้ง 10 ใบของท่านปรากฏขึ้นแล้ว:</b>\n"]
            for i, card_name in enumerate(drawn_cards):
                card_list_parts.append(f"ใบที่ {i+1} (<b>{CELTIC_CROSS_POSITIONS[i]}</b>): <b>{card_name}</b>")
            card_list_str = "\n".join(card_list_parts)
            
            save_reading_to_file(update.effective_user.id, card_list_str, mode="10_cards")
            await update.message.reply_text(card_list_str, parse_mode=ParseMode.HTML)
            
            # ทำความสะอาด user_data
            del context.user_data['deck']
            del context.user_data['card_index']
            
            # [แก้ไข] แสดงเมนูถัดไป (เป็นปุ่ม)
            menu_text = (
                "ท่านต้องการรับคำทำนายในลักษณะใด?\n\n"
                "โปรดเลือกจากปุ่มด้านล่าง:"
            )
            await update.message.reply_text(menu_text, parse_mode=ParseMode.HTML, reply_markup=CHOOSING_ACTION_MARKUP)
            return CHOOSING_ACTION # เปลี่ยนไป State ถัดไป

    except Exception as e:
        logger.error(f"Error drawing card: {e}")
        await update.message.reply_text(
            "❗️ ขออภัย, เกิดข้อผิดพลาดในกระบวนการเปิดไพ่\nกรุณาใช้คำสั่ง /cancel แล้วเริ่มต้นใหม่",
            reply_markup=MARKUP
        )
        return ConversationHandler.END

async def invalid_draw_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ [แก้ไข] กรณีผู้ใช้พิมพ์อย่างอื่นที่ไม่ใช่ 'ปุ่ม' ระหว่างการจั่วไพ่ """
    await update.message.reply_text(
        f"❗️ โปรดกดปุ่ม <b>{DRAW_CARD_BUTTON_TEXT}</b> เพื่อทำการเปิดไพ่ใบต่อไป",
        parse_mode=ParseMode.HTML,
        reply_markup=DRAW_MARKUP # [แก้ไข] ส่งปุ่มให้ผู้ใช้อีกครั้ง
    )
    return DRAWING_CARDS

async def generate_and_show_prediction_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # [ปรับปรุง] เพิ่ม Emoji
    await update.message.reply_text("<i>⏳ กำลังอ่านชะตาจากหน้าไพ่ทั้งหมด... โปรดรอสักครู่</i>", parse_mode=ParseMode.HTML)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    drawn_cards = context.user_data.get('drawn_cards')
    if not drawn_cards:
        await update.message.reply_text(
            "❗️ เกิดข้อผิดพลาด: ไม่พบข้อมูลไพ่ของท่าน\n<i>กรุณาเริ่มต้นการทำนายใหม่อีกครั้ง</i>",
            reply_markup=MARKUP,
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    card_list_prompt = "\n".join([f"- {CELTIC_CROSS_POSITIONS[i]}: {card}" for i, card in enumerate(drawn_cards)])
    try:
        chat = get_chat_session(update.effective_chat.id)
        response = chat.send_message(f"ไพ่ที่เปิดได้:\n{card_list_prompt}\n\nโปรดสร้างคำทำนายฉบับเต็มตามภารกิจหลัก")
        
        raw_text = response.text
        
        # [แก้ไข] ปรับปรุง Regex ให้อดทนต่อช่องว่าง (s*) และตัวพิมพ์เล็ก/ใหญ่ (re.IGNORECASE)
        sections = re.split(r'\[\s*SECTION\s*:(.*?)\]', raw_text, flags=re.IGNORECASE)
        
        prediction_parts = {}
        for i in range(1, len(sections), 2):
            title = sections[i].strip()
            content = sections[i+1].strip()
            if title and content: prediction_parts[title] = content
        
        if not prediction_parts:
            logger.warning(f"Could not split prediction. AI response might be off-format. Raw text: {raw_text[:200]}...") # Log เพิ่ม
            await update.message.reply_text(
                "😥 ขออภัย ข้าพเจ้าไม่สามารถแยกหัวข้อคำทำนายได้\n<b>นี่คือคำทำนายทั้งหมดที่ได้รับ:</b>",
                parse_mode=ParseMode.HTML
            )
            await send_long_message(update, context, raw_text)
            await update.message.reply_text("หากท่านมีคำถามใดๆ เพิ่มเติม สามารถพิมพ์ถามข้าพเจ้าได้")
            # [แก้ไข] ต้องล้าง session ที่นี่
            if update.effective_chat.id in chat_sessions:
                del chat_sessions[update.effective_chat.id]
            return ConversationHandler.END

        context.user_data['prediction_parts'] = prediction_parts
        context.user_data['prediction_keys'] = list(prediction_parts.keys())
        await _display_prediction_menu(update, context)

    except Exception as e:
        logger.error(f"Error generating full prediction: {e}")
        await update.message.reply_text("😥 ขออภัย ข้าพเจ้าเชื่อมต่อกับพลังจักรวาลไม่ได้ในขณะนี้", reply_markup=MARKUP)
        return ConversationHandler.END
    return VIEWING_PREDICTION

async def show_selected_prediction_part(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        chosen_text = update.message.text
        
        # [แก้ไข] แยกหมายเลขจาก emoji (เช่น "1" จาก "1️⃣ ...")
        # ใช้ re.match เพื่อดึงเฉพาะตัวเลข
        match = re.match(r'^(\d+)', chosen_text)
        if not match:
            raise ValueError("Button text doesn't start with a number emoji")
            
        choice_num_str = match.group(1)
        choice_index = int(choice_num_str) - 1 # "1" -> 0
        
        prediction_keys = context.user_data['prediction_keys']
        if not (0 <= choice_index < len(prediction_keys)): 
            raise ValueError("Index out of bounds")
        
        key = prediction_keys[choice_index]
        content = context.user_data['prediction_parts'][key]
        message_to_send = f"<b>--- {key} ---</b>\n\n{content}"
        await send_long_message(update, context, message_to_send, parse_mode=ParseMode.HTML)
        await _display_prediction_menu(update, context) # แสดงปุ่มเมนูอีกครั้ง
        
    except (ValueError, IndexError):
        await invalid_choice(update, context, message="❗️ โปรดกดปุ่มจากเมนูคำทำนายที่แสดง")
        await _display_prediction_menu(update, context) # [ใหม่] แสดงปุ่มอีกครั้งหากเลือกผิด
    return VIEWING_PREDICTION

async def show_topic_menu_10_cards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # [แก้ไข] ส่งปุ่ม SPECIFIC_TOPIC_MARKUP
    menu_text = "<b>📜 โปรดเลือกหัวข้อที่ท่านต้องการเจาะลึกเป็นพิเศษ</b>\nโดยการกดปุ่มด้านล่าง:"
    await update.message.reply_text(menu_text, parse_mode=ParseMode.HTML, reply_markup=SPECIFIC_TOPIC_MARKUP)
    return CHOOSING_TOPIC_10

async def get_topic_prediction_10_cards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        # [แก้ไข] ค้นหา topic จากข้อความบนปุ่ม
        chosen_text = update.message.text
        topic_name = None
        for key, name in TOPIC_LIST:
            if name in chosen_text: # ตรวจสอบว่า "การงาน" อยู่ใน "💼 การงาน" หรือไม่
                topic_name = name
                break
        
        if not topic_name:
            raise ValueError("Topic not found from button text")

    except (ValueError, IndexError):
        await invalid_choice(update, context, message="❗️ โปรดกดปุ่มหัวข้อที่ท่านสนใจ")
        return CHOOSING_TOPIC_10 # กลับไปรอเลือกหัวข้อ
    
    # [ปรับปรุง] เพิ่ม Emoji
    await update.message.reply_text(
        f"<i>⏳ กำลังวิเคราะห์ชะตาในด้าน '{topic_name}' อย่างละเอียด...</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    drawn_cards = context.user_data.get('drawn_cards')
    card_list_prompt = "\n".join([f"- {CELTIC_CROSS_POSITIONS[i]}: {card}" for i, card in enumerate(drawn_cards)])
    prompt = f"ไพ่ที่เปิดได้:\n{card_list_prompt}\n\nโปรด เจาะลึกคำทำนายเฉพาะเรื่อง '{topic_name}' เท่านั้น"
    
    try:
        chat = get_chat_session(update.effective_chat.id)
        response = chat.send_message(prompt)
        await send_long_message(update, context, response.text)
    except Exception as e:
        logger.error(f"Error getting topic prediction '{topic_name}': {e}")
        await update.message.reply_text(
            "😥 ขออภัย, ข้าพเจ้าพบข้อผิดพลาดในการทำนายเฉพาะเรื่อง\n<i>กรุณาลองใหม่อีกครั้ง</i>",
            parse_mode=ParseMode.HTML
        )
    
    # [แก้ไข] แสดงเมนูหัวข้ออีกครั้ง
    await show_topic_menu_10_cards(update, context)
    return CHOOSING_TOPIC_10

async def back_to_main_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # [แก้ไข] เปลี่ยนเป็นส่งปุ่ม CHOOSING_ACTION_MARKUP
    menu_text = (
        "ท่านต้องการรับคำทำนายในลักษณะใด?\n\n"
        "โปรดเลือกจากปุ่มด้านล่าง:"
    )
    await update.message.reply_text(menu_text, parse_mode=ParseMode.HTML, reply_markup=CHOOSING_ACTION_MARKUP)
    return CHOOSING_ACTION

# --- 6. [ปรับปรุง] โหมดทำนายรายวัน 3 ใบ (เพิ่ม Emojis) ---
async def daily_reading_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the 3-card daily reading."""
    user = update.effective_user
    logger.info("User %s (%s) starting a 3-card daily reading.", user.first_name, user.id)
    
    if update.effective_chat.id in chat_sessions:
        del chat_sessions[update.effective_chat.id]

    # [แก้ไข] ส่งปุ่ม DAILY_TOPIC_MARKUP
    menu_text = (
        "<b>☀️ การทำนายรายวัน (ไพ่ 3 ใบ)</b>\n\n"
        "โปรดเลือกหัวข้อที่ท่านสนใจสำหรับวันนี้\nหรือกดถามคำถามเฉพาะของท่าน:"
    )
    await update.message.reply_text(menu_text, parse_mode=ParseMode.HTML, reply_markup=DAILY_TOPIC_MARKUP)
    return SELECTING_DAILY_OPTION # [แก้ไข] เปลี่ยน State

async def get_daily_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Draws 3 cards and gives a daily prediction for the chosen topic."""
    try:
        # [แก้ไข] ค้นหา topic จากข้อความบนปุ่ม
        chosen_text = update.message.text
        topic_name = None
        for key, name in TOPIC_LIST:
            if name in chosen_text: # ตรวจสอบว่า "การงาน" อยู่ใน "💼 การงาน" หรือไม่
                topic_name = name
                break
        
        if not topic_name:
            # [แก้ไข] ถ้าไม่ใช่ topic (อาจจะพิมพ์มั่ว)
            await invalid_choice(update, context, message="❗️ โปรดกดปุ่มหัวข้อที่ท่านสนใจ หรือปุ่มถามคำถาม")
            return SELECTING_DAILY_OPTION # กลับไปรอเลือกหัวข้อ

    except (ValueError, IndexError):
        await invalid_choice(update, context, message="❗️ โปรดกดปุ่มหัวข้อที่ท่านสนใจ")
        return SELECTING_DAILY_OPTION # กลับไปรอเลือกหัวข้อ

    # [ปรับปรุง] เพิ่ม Emoji
    await update.message.reply_text(
        f"ท่านเลือกทำนายเรื่อง <b>{topic_name}</b>\n<i>⏳ กำลังเปิดไพ่ 3 ใบสำหรับวันนี้... โปรดรอสักครู่</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    drawn_cards = random.sample(FULL_DECK, k=3)
    
    card_list_parts = [f"<b>🃏 ไพ่ 3 ใบสำหรับเรื่อง '{topic_name}' ในวันนี้คือ:</b>\n"]
    for i, card in enumerate(drawn_cards):
        card_list_parts.append(f"<b>{DAILY_SPREAD_POSITIONS[i]}</b>: <b>{card}</b>")
    card_list_str = "\n".join(card_list_parts)
    
    save_reading_to_file(update.effective_user.id, card_list_str, mode="daily_3_cards")
    await update.message.reply_text(card_list_str, parse_mode=ParseMode.HTML)
    
    prompt = (f"โปรดทำนายรายวัน 3 ใบ สำหรับหัวข้อ '{topic_name}' โดยไพ่ที่เปิดได้คือ:\n"
              f"1. {DAILY_SPREAD_POSITIONS[0]}: {drawn_cards[0]}\n"
              f"2. {DAILY_SPREAD_POSITIONS[1]}: {drawn_cards[1]}\n"
              f"3. {DAILY_SPREAD_POSITIONS[2]}: {drawn_cards[2]}\n"
              f"ให้คำทำนายที่กระชับและตรงประเด็นสำหรับเป็นแนวทางในวันนี้")

    try:
        chat = get_chat_session(update.effective_chat.id)
        response = chat.send_message(prompt)
        await send_long_message(update, context, response.text)
    except Exception as e:
        logger.error(f"Error getting daily prediction: {e}")
        await update.message.reply_text(
            "😥 ขออภัย, ข้าพเจ้าไม่สามารถเชื่อมต่อกับพลังจักรวาลได้ในขณะนี้\n<i>กรุณาลองใหม่อีกครั้งในภายหลัง</i>",
            parse_mode=ParseMode.HTML
        )
        
    # [ปรับปรุง] เพิ่ม Emoji
    await update.message.reply_text(
        "✨ ขอให้ท่านโชคดีตลอดวัน\nหากต้องการคำชี้แนะอีกครั้ง โปรดเลือกรูปแบบการทำนาย",
        reply_markup=MARKUP
    )
    return ConversationHandler.END

# [ใหม่] ฟังก์ชันสำหรับรอรับคำถาม
async def prompt_for_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to type their specific question."""
    await update.message.reply_text(
        "<b>❓ ถามคำถามเฉพาะ</b>\n\n"
        "โปรดพิมพ์คำถามที่ท่านต้องการทราบให้ชัดเจน\n"
        "(เช่น 'ข้าพเจ้าควรลงทุนในตอนนี้หรือไม่?', 'ความสัมพันธ์กับคนนี้จะเป็นอย่างไร?')\n\n"
        "<i>หากต้องการยกเลิก ให้ใช้คำสั่ง /cancel</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove() # ลบปุ่มกดออก
    )
    return AWAITING_QUESTION

# [ใหม่] ฟังก์ชันสำหรับประมวลผลคำถาม
async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Draws 3 cards and answers the user's specific question."""
    question = update.message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await update.message.reply_text(
        f"<i>⏳ กำลังเปิดไพ่ 3 ใบสำหรับคำถามของท่าน: '{question}'...</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    drawn_cards = random.sample(FULL_DECK, k=3)
    
    card_list_parts = [f"<b>🃏 ไพ่ 3 ใบสำหรับคำถามของท่านคือ:</b>\n"]
    for i, card in enumerate(drawn_cards):
        card_list_parts.append(f"<b>{DAILY_SPREAD_POSITIONS[i]}</b>: <b>{card}</b>")
    card_list_str = "\n".join(card_list_parts)
    
    save_reading_to_file(user_id, f"Question: {question}\n\n{card_list_str}", mode="daily_question_3_cards")
    await update.message.reply_text(card_list_str, parse_mode=ParseMode.HTML)
    
    # [ใหม่] Prompt ที่รวมคำถามและไพ่
    prompt = (f"โปรดตอบคำถามเฉพาะของผู้ใช้: \"{question}\"\n"
              f"โดยใช้การตีความไพ่ 3 ใบนี้ (ตามภารกิจรอง):\n"
              f"1. {DAILY_SPREAD_POSITIONS[0]}: {drawn_cards[0]}\n"
              f"2. {DAILY_SPREAD_POSITIONS[1]}: {drawn_cards[1]}\n"
              f"3. {DAILY_SPREAD_POSITIONS[2]}: {drawn_cards[2]}\n"
              f"ให้คำตอบที่ตรงประเด็น อิงจากไพ่ และให้คำแนะนำ")

    try:
        # [ใหม่] ต้องล้าง session เก่า (ถ้ามี) และเริ่ม session ใหม่สำหรับคำถามนี้
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]
        chat = get_chat_session(chat_id)
        
        response = chat.send_message(prompt)
        await send_long_message(update, context, response.text)
    except Exception as e:
        logger.error(f"Error getting daily question prediction: {e}")
        await update.message.reply_text(
            "😥 ขออภัย, ข้าพเจ้าไม่สามารถเชื่อมต่อกับพลังจักรวาลได้ในขณะนี้\n<i>กรุณาลองใหม่อีกครั้งในภายหลัง</i>",
            parse_mode=ParseMode.HTML
        )
    
    await update.message.reply_text(
        "✨ ขอให้ท่านโชคดีตลอดวัน\nหากต้องการคำชี้แนะอีกครั้ง โปรดเลือกรูปแบบการทำนาย",
        reply_markup=MARKUP
    )
    return ConversationHandler.END


# --- 7. โครงสร้างหลักและ Chat ทั่วไป ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id not in chat_sessions:
        # [ปรับปรุง] เพิ่ม Emoji
        await update.message.reply_text("🤔 โปรดเลือกรูปแบบการทำนายจากเมนูด้านล่างเถิด", reply_markup=MARKUP)
        return
    
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    try:
        chat_session = get_chat_session(chat_id)
        response = chat_session.send_message(update.message.text)
        await send_long_message(update, context, response.text)
    except Exception as e:
        logger.error(f"Error in free-form chat: {e}")
        await update.message.reply_text(
            "😥 ขออภัย, เกิดข้อผิดพลาดในการสื่อสาร\n<i>ท่านสามารถลองใหม่อีกครั้ง หรือใช้คำสั่ง /cancel เพื่อเริ่มต้นใหม่</i>",
            parse_mode=ParseMode.HTML
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    chat_id = update.effective_chat.id
    if chat_id in chat_sessions: del chat_sessions[chat_id]
    
    # [ปรับปรุง] เพิ่ม Emoji
    await update.message.reply_text(
        "🙏 การทำนายสิ้นสุดลง\n\n✨ ขอให้ท่านโชคดีมีชัย และกลับมาใช้บริการได้ทุกเมื่อที่ท่านต้องการ",
        reply_markup=MARKUP
    )
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # [ปรับปรุง] Conversation Handler สำหรับโหมด 10 ใบ
    celtic_cross_handler = ConversationHandler(
        # [แก้ไข] เพิ่ม r เพื่อใช้ Raw String
        entry_points=[MessageHandler(filters.Regex(r"^🔮 ทำนายชะตา 10 ใบ \(ภาพรวม\)$"), tarot_reading_start_10_cards)],
        states={
            # [แก้ไข] State สำหรับการจั่วไพ่
            DRAWING_CARDS: [
                # [แก้ไข] เปลี่ยนจาก "9" เป็น Regex ของปุ่ม
                MessageHandler(filters.Regex(f"^{re.escape(DRAW_CARD_BUTTON_TEXT)}$"), draw_next_card),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_draw_choice),
            ],
            # [แก้ไข] State เลือก 1 หรือ 2
            CHOOSING_ACTION: [
                # [แก้ไข] เปลี่ยนจาก "1" และ "2" เป็น Regex ของปุ่ม
                MessageHandler(filters.Regex(r"^1️⃣ รับคำทำนายภาพรวม$"), generate_and_show_prediction_menu),
                MessageHandler(filters.Regex(r"^2️⃣ เจาะลึกคำทำนายเฉพาะเรื่อง$"), show_topic_menu_10_cards),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_choice),
            ],
            # [แก้ไข] State เลือกหัวข้อเจาะลึก
            CHOOSING_TOPIC_10: [
                MessageHandler(filters.Regex(f"^{re.escape(BACK_BUTTON_TEXT)}$"), back_to_main_choice),
                # [แก้ไข] รับ Text ธรรมดา (ที่เป็นปุ่มหัวข้อ) แล้วส่งไปประมวลผล
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_topic_prediction_10_cards),
            ],
            # [แก้ไข] State ดูผลทีละส่วน
            VIEWING_PREDICTION: [
                MessageHandler(filters.Regex(f"^{re.escape(CANCEL_BUTTON_TEXT)}$"), cancel),
                # [แก้ไข] รับ Text ธรรมดา (ที่เป็นปุ่มหัวข้อ) แล้วส่งไปประมวลผล
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_selected_prediction_part),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # [ปรับปรุง] Conversation Handler สำหรับโหมดรายวัน 3 ใบ
    daily_reading_handler = ConversationHandler(
        # [แก้ไข] เพิ่ม r เพื่อใช้ Raw String
        entry_points=[MessageHandler(filters.Regex(r"^☀️ ทำนายรายวัน 3 ใบ \(เจาะจง\)$"), daily_reading_start)],
        states={
            # [แก้ไข] State เลือกหัวข้อรายวัน หรือ ถามคำถาม
            SELECTING_DAILY_OPTION: [
                # [ใหม่] Handler สำหรับปุ่มถามคำถาม
                MessageHandler(filters.Regex(f"^{re.escape(ASK_QUESTION_BUTTON_TEXT)}$"), prompt_for_question),
                # [แก้ไข] Handler สำหรับปุ่มหัวข้อ (รับ Text ธรรมดา)
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_daily_prediction),
            ],
            # [ใหม่] State สำหรับรอรับคำถาม
            AWAITING_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_question)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(celtic_cross_handler)
    application.add_handler(daily_reading_handler)
    
    # [ปรับปรุง] Regex ของ chat handler ให้ไม่ทับซ้อนกับปุ่มเมนูหลัก
    # [แก้ไข] เพิ่ม r เพื่อใช้ Raw String และเพิ่มปุ่มใหม่ๆ ทั้งหมด
    main_menu_filter = (
        filters.Regex(r"^🔮 ทำนายชะตา 10 ใบ \(ภาพรวม\)$") |
        filters.Regex(r"^☀️ ทำนายรายวัน 3 ใบ \(เจาะจง\)$") |
        filters.Regex(f"^{re.escape(DRAW_CARD_BUTTON_TEXT)}$") | 
        filters.Regex(r"^1️⃣ รับคำทำนายภาพรวม$") | 
        filters.Regex(r"^2️⃣ เจาะลึกคำทำนายเฉพาะเรื่อง$") |
        filters.Regex(f"^{re.escape(BACK_BUTTON_TEXT)}$") |      # [ใหม่] กรองปุ่มย้อนกลับ
        filters.Regex(f"^{re.escape(CANCEL_BUTTON_TEXT)}$") |    # [ใหม่] กรองปุ่มยกเลิก
        filters.Regex(f"^{re.escape(ASK_QUESTION_BUTTON_TEXT)}$") | # [ใหม่] กรองปุ่มถามคำถาม
        filters.Regex(r"^\d+️⃣") |                               # [แก้ไข] กรองปุ่มเลือกผลทำนาย (เช่น 1️⃣... 10️⃣...)
        filters.Regex(r"^[💼💰❤️🩺👨‍👩‍👧‍👦✨]")                     # [ใหม่] กรองปุ่มเลือกหัวข้อ (เช่น 💼...)
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~main_menu_filter, chat))

    print("Bot is running with interactive 10-card, 3-card daily, and 3-card question modes... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
