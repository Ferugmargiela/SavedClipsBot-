import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from handlers import commands
from handlers.function import cleanup_downloads


async def main():
    load_dotenv()

    token = os.getenv(
        "BOT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "BOT_TOKEN не найден в .env"
        )

    cleanup_downloads()

    session = AiohttpSession(
        timeout=500
    )

    bot = Bot(
        token=token,
        session=session
    )

    dp = Dispatcher()

    dp.include_router(
        commands.router
    )

    print(
        "Bot Start"
    )

    try:
        await dp.start_polling(
            bot
        )

    finally:
        await bot.session.close()


if __name__ == "__main__":

    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Exit"
        )