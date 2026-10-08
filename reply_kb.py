from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎬 YouTube (видео/shorts)"),
                KeyboardButton(text="🎵 YouTube в формате аудио")
            ],
            [
                KeyboardButton(text="🎬 TikTok видео"),
                KeyboardButton(text="🎵 TikTok аудио")
            ],
            [
                KeyboardButton(text="🖼 TikTok фото"),
                KeyboardButton(text="🎬 Instagram видео")
            ],
            [
                KeyboardButton(text="🆘 Поддержка")
            ],
            [
                KeyboardButton(text="⛔ Остановить все процессы")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True
    )