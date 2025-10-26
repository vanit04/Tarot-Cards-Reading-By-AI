# -*- coding: utf-8 -*-
# tarot_deck.py
# ไฟล์นี้เก็บข้อมูลไพ่ทั้งหมดของเรา

MAJOR_ARCANA = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World"
]

SUITS = ["Wands", "Cups", "Swords", "Pentacles"]
RANKS = [
    "Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Page", "Knight", "Queen", "King"
]

# สร้างสำรับ Minor Arcana
MINOR_ARCANA = [f"{rank} of {suit}" for suit in SUITS for rank in RANKS]

# สำรับเต็ม 78 ใบ
FULL_DECK = MAJOR_ARCANA + MINOR_ARCANA

# ตำแหน่งไพ่ Celtic Cross (ภาษาไทยตาม Persona)
CELTIC_CROSS_POSITIONS = [
    "เรื่องของเธอตอนนี้", "เรื่องที่เข้ามาท้าทาย", "พื้นฐานที่ผ่านมา",
    "อนาคตอันใกล้", "สิ่งที่เธอคิด", "สิ่งที่ซ่อนอยู่ในใจ",
    "คำแนะนำจากไพ่", "คนรอบข้างและสิ่งแวดล้อม", "ความหวังและความกังวล", "บทสรุป"
]