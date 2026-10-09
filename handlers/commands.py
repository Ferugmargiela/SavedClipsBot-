import asyncio

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.reply_kb import main_keyboard
from handlers.function import (
    download_and_send_media,
    stop_all_tasks,
    is_download_active,
    is_valid_service_url
)

router = Router()

class DownloadState(StatesGroup):
    waiting_for_url = State()

@router.message(CommandStart())
async def start_command(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "📥 Скачивай видео, аудио и фото "
        "без водяных знаков.\n\n"
        "⚡ Быстро и удобно.\n\n"
        "👇 Выберите, что хотите скачать:",
        reply_markup=main_keyboard()
    )

@router.message(F.text == "🎬 YouTube (видео/shorts)")
async def youtube_video(
    message: Message,
    state: FSMContext
):
    if is_download_active(message.chat.id):
        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы»."
        )
        return

    await state.set_state(
        DownloadState.waiting_for_url
    )

    await state.update_data(
        media_type="youtube_video"
    )

    await message.answer(
        "⚠️ Ограничение Telegram\n\n"
        "Видео размером больше 49 МБ бот отправить "
        "не сможет.\n\n"
        "Если видео окажется больше 49 МБ, "
        "оно не будет отправлено.\n\n"
        "🎵 В таком случае рекомендуем выбрать "
        "«YouTube в формате аудио»."
    )

    await message.answer(
        "🎬 Отправь ссылку на YouTube видео или Shorts:"
    )

@router.message(F.text == "🎵 YouTube в формате аудио")
async def youtube_audio(
    message: Message,
    state: FSMContext
):
    if is_download_active(message.chat.id):
        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы»."
        )
        return

    await state.set_state(
        DownloadState.waiting_for_url
    )

    await state.update_data(
        media_type="youtube_audio"
    )

    await message.answer(
        "🎵 Отправь ссылку на YouTube видео или Shorts:"
    )

@router.message(F.text == "🎬 TikTok видео")
async def tiktok_video(
    message: Message,
    state: FSMContext
):
    if is_download_active(message.chat.id):
        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы»."
        )
        return

    await state.set_state(
        DownloadState.waiting_for_url
    )

    await state.update_data(
        media_type="tiktok_video"
    )

    await message.answer(
        "🎬 Отправь ссылку на TikTok:"
    )

@router.message(F.text == "🎵 TikTok аудио")
async def tiktok_audio(
    message: Message,
    state: FSMContext
):
    if is_download_active(message.chat.id):
        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы»."
        )
        return

    await state.set_state(
        DownloadState.waiting_for_url
    )

    await state.update_data(
        media_type="tiktok_audio"
    )

    await message.answer(
        "🎵 Отправь ссылку на TikTok:"
    )

@router.message(F.text == "🖼 TikTok фото")
async def tiktok_photo(
    message: Message,
    state: FSMContext
):
    if is_download_active(message.chat.id):
        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы»."
        )
        return

    await state.set_state(
        DownloadState.waiting_for_url
    )

    await state.update_data(
        media_type="tiktok_photo"
    )

    await message.answer(
        "🖼 Отправь ссылку на TikTok с фотографиями:"
    )

@router.message(F.text == "🎬 Instagram видео")
async def instagram_video(
    message: Message,
    state: FSMContext
):
    if is_download_active(message.chat.id):
        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы»."
        )
        return

    await state.set_state(
        DownloadState.waiting_for_url
    )

    await state.update_data(
        media_type="instagram_video"
    )

    await message.answer(
        "🎬 Instagram видео\n\n"
        "⚠️ Истории и фотографии из Instagram "
        "не загружаются.\n\n"
        "📌 Доступна загрузка только видео Reels."
    )

    await message.answer(
        "🔗 Отправь ссылку на Instagram Reels:"
    )

@router.message(F.text == "🆘 Поддержка")
async def support(
    message: Message
):
    await message.answer(
        "🆘 Поддержка\n\n"
        "Если у вас возникли проблемы с ботом "
        "или есть предложения по улучшению, "
        "напишите нам:\n\n"
        "👤 @TrueKostil"
    )

@router.message(F.text == "⛔ Остановить все процессы")
async def stop_processes(
    message: Message,
    state: FSMContext
):
    stopped = await stop_all_tasks(
        message.chat.id
    )

    await state.clear()

    if stopped:
        text = (
            "⛔ Все загрузки остановлены.\n"
            "🧹 Временные файлы удалены."
        )
    else:
        text = "ℹ️ Активных загрузок нет."

    await message.answer(
        text + "\n\n"
        "👇 Выберите, что хотите скачать:",
        reply_markup=main_keyboard()
    )

@router.message(DownloadState.waiting_for_url)
async def receive_url(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "❌ Отправь ссылку."
        )
        return

    url = message.text.strip()

    data = await state.get_data()

    media_type = data.get(
        "media_type"
    )

    if not media_type:
        await state.clear()

        await message.answer(
            "❌ Сначала выбери, что хочешь скачать.",
            reply_markup=main_keyboard()
        )

        return

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        await message.answer(
            "❌ Это не похоже на ссылку.\n"
            "Отправь правильную ссылку."
        )
        return

    if not is_valid_service_url(
        url,
        media_type
    ):
        await message.answer(
            "❌ Эта ссылка не подходит для выбранного раздела.\n\n"
            "Проверь ссылку или выбери другой раздел."
        )
        return

    if is_download_active(message.chat.id):
        await state.clear()

        await message.answer(
            "⏳ У вас уже выполняется загрузка.\n\n"
            "Дождитесь её завершения или нажмите "
            "⛔ «Остановить все процессы».",
            reply_markup=main_keyboard()
        )

        return

    await state.clear()

    asyncio.create_task(
        download_and_send_media(
            message.bot,
            message.chat.id,
            url,
            media_type
        )
    )

@router.message()
async def unknown_message(
    message: Message
):
    await message.answer(
        "👇 Выберите, что хотите скачать:",
        reply_markup=main_keyboard()
    )