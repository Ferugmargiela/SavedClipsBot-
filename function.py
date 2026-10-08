import os
import re
import shutil
import asyncio
import threading
import uuid
import subprocess
import time
import traceback
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

from aiogram.types import FSInputFile


active_tasks = {}
stop_events = {}
progress_data = {}

MAX_VIDEO_SIZE = 49 * 1024 * 1024
BOT_FILE_NAME = "Скачан с @Saved_ClipsBOT"
CAPTION = "📢 Подпишись на наш канал, там много интересного\n@CyberMed_Cartel"

DOWNLOADS_DIR = "downloads"


class DownloadCancelled(Exception):
    pass


class TikTokForbidden(Exception):
    pass


def is_download_active(chat_id):
    task = active_tasks.get(chat_id)

    if task is None:
        return False

    if task.done():
        active_tasks.pop(chat_id, None)
        stop_events.pop(chat_id, None)
        progress_data.pop(chat_id, None)
        return False

    return True


def check_cancel(chat_id):
    event = stop_events.get(chat_id)

    if event and event.is_set():
        raise DownloadCancelled()


def format_size(size):
    if not size:
        return "0 Б"

    size = float(size)

    if size < 1024:
        return f"{int(size)} Б"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} КБ"

    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} МБ"

    return f"{size / (1024 * 1024 * 1024):.2f} ГБ"


def format_speed(speed):
    if not speed:
        return "—"

    speed = float(speed)

    if speed < 1024:
        return f"{int(speed)} Б/с"

    if speed < 1024 * 1024:
        return f"{speed / 1024:.1f} КБ/с"

    return f"{speed / (1024 * 1024):.1f} МБ/с"


def collect_files(directory):
    result = []

    if not os.path.exists(directory):
        return result

    for root, _, files in os.walk(directory):
        for filename in files:
            path = os.path.join(root, filename)

            if os.path.isfile(path):
                result.append(path)

    return result


def is_valid_service_url(url, media_type):
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        path = parsed.path.lower()
    except Exception:
        return False

    if media_type in {
        "youtube_video",
        "youtube_audio"
    }:
        return (
            host == "youtube.com"
            or host.endswith(".youtube.com")
            or host == "youtu.be"
        )

    if media_type in {
        "tiktok_video",
        "tiktok_audio",
        "tiktok_photo"
    }:
        if not (
            host == "tiktok.com"
            or host.endswith(".tiktok.com")
        ):
            return False

        if "/photo/" in path:
            return media_type == "tiktok_photo"

        if "/video/" in path:
            return media_type in {
                "tiktok_video",
                "tiktok_audio"
            }

        if "/t/" in path:
            return True

        return True

    if media_type == "instagram_video":
        if not (
            host == "instagram.com"
            or host.endswith(".instagram.com")
        ):
            return False

        if "/stories/" in path:
            return False

        if path.startswith("/p/"):
            return False

        return (
            "/reel/" in path
            or "/reels/" in path
        )

    return False


def progress_hook_factory(chat_id):
    def progress_hook(data):
        try:
            check_cancel(chat_id)

            status = data.get("status")

            if status == "downloading":
                downloaded = data.get("downloaded_bytes", 0)
                total = (
                    data.get("total_bytes")
                    or data.get("total_bytes_estimate")
                    or 0
                )
                speed = data.get("speed", 0)
                eta = data.get("eta")

                percent = 0

                if total:
                    percent = downloaded / total * 100

                progress_data[chat_id] = {
                    "status": "downloading",
                    "percent": percent,
                    "downloaded": downloaded,
                    "total": total,
                    "speed": speed,
                    "eta": eta
                }

            elif status == "finished":
                progress_data[chat_id] = {
                    "status": "processing",
                    "percent": 100,
                    "downloaded": 0,
                    "total": 0,
                    "speed": 0,
                    "eta": None
                }

        except DownloadCancelled:
            raise

        except Exception:
            pass

    return progress_hook


def download_with_ytdlp(
    url,
    task_dir,
    media_type,
    chat_id
):
    check_cancel(chat_id)

    ydl_opts = {
        "outtmpl": os.path.join(
            task_dir,
            "%(id)s_%(title)s.%(ext)s"
        ),
        "js_runtimes": {
            "deno": {}
        },
        "progress_hooks": [
            progress_hook_factory(chat_id)
        ],
        "quiet": True,
        "no_warnings": False,
        "noplaylist": True,
        "restrictfilenames": False,
        "windowsfilenames": False,
        "ignoreerrors": False
    }

    if media_type in {
        "tiktok_video",
        "tiktok_audio"
    }:
        ydl_opts["impersonate"] = ImpersonateTarget(
            client="chrome",
            version="131",
            os="macos",
            os_version="14"
        )

    if media_type in {
        "youtube_video",
        "tiktok_video",
        "instagram_video"
    }:
        ydl_opts.update({
            "format": "bv*+ba/b",
            "merge_output_format": "mp4"
        })

    elif media_type in {
        "youtube_audio",
        "tiktok_audio"
    }:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }
            ]
        })

    progress_data[chat_id] = {
        "status": "preparing",
        "percent": 0,
        "downloaded": 0,
        "total": 0,
        "speed": 0,
        "eta": None
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            check_cancel(chat_id)

            result = ydl.download([url])

            check_cancel(chat_id)

            if result not in (None, 0):
                raise RuntimeError(
                    f"yt-dlp завершился с кодом {result}"
                )

    except DownloadCancelled:
        raise

    except Exception as error:
        error_text = str(error)

        if (
            "HTTP Error 403" in error_text
            or "403: Forbidden" in error_text
            or "403 Forbidden" in error_text
        ):
            if media_type in {
                "tiktok_video",
                "tiktok_audio"
            }:
                raise TikTokForbidden()

        raise


def download_with_gallery_dl(
    url,
    task_dir,
    chat_id
):
    check_cancel(chat_id)

    gallery_dl = shutil.which("gallery-dl")

    if not gallery_dl:
        raise RuntimeError(
            "gallery-dl не найден в PATH"
        )

    command = [
        gallery_dl,
        "--no-input",
        "--no-mtime",
        "-D",
        task_dir,
        "-o",
        "extractor.tiktok.photos=true",
        "-o",
        "extractor.tiktok.audio=false",
        "-o",
        "extractor.tiktok.videos=false",
        "-o",
        "extractor.tiktok.covers=false",
        url
    ]

    progress_data[chat_id] = {
        "status": "downloading",
        "percent": 0,
        "downloaded": 0,
        "total": 0,
        "speed": 0,
        "eta": None
    }

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    try:
        while True:
            check_cancel(chat_id)

            line = process.stdout.readline()

            if line:
                print(
                    f"[gallery-dl] {line.rstrip()}",
                    flush=True
                )

            if process.poll() is not None:
                break

            time.sleep(0.1)

        return_code = process.wait()

        check_cancel(chat_id)

        if return_code != 0:
            raise RuntimeError(
                f"gallery-dl завершился с кодом {return_code}"
            )

    except DownloadCancelled:
        try:
            process.kill()
        except Exception:
            pass

        try:
            process.wait(timeout=2)
        except Exception:
            pass

        raise

    except Exception:
        try:
            process.kill()
        except Exception:
            pass

        try:
            process.wait(timeout=2)
        except Exception:
            pass

        raise

    files = collect_files(task_dir)

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    files = [
        file
        for file in files
        if os.path.splitext(file)[1].lower()
        in allowed_extensions
    ]

    if not files:
        raise RuntimeError(
            "gallery-dl не нашёл фотографии"
        )

    return files


def safe_filename(name):
    name = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        name
    )

    name = name.strip(" .")

    if not name:
        name = "file"

    return name


def rename_files(
    files,
    media_type
):
    renamed_files = []

    if media_type == "tiktok_photo":
        for index, file in enumerate(files, start=1):
            extension = os.path.splitext(file)[1].lower()

            if extension not in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp"
            }:
                continue

            if len(files) == 1:
                new_name = (
                    f"{BOT_FILE_NAME}{extension}"
                )
            else:
                new_name = (
                    f"{BOT_FILE_NAME}_{index}{extension}"
                )

            new_name = safe_filename(new_name)

            new_path = os.path.join(
                os.path.dirname(file),
                new_name
            )

            if os.path.abspath(file) != os.path.abspath(new_path):
                if os.path.exists(new_path):
                    os.remove(new_path)

                os.replace(file, new_path)

            renamed_files.append(new_path)

        return renamed_files

    for file in files:
        extension = os.path.splitext(file)[1].lower()

        if media_type in {
            "youtube_audio",
            "tiktok_audio"
        }:
            extension = ".mp3"

        new_name = safe_filename(
            f"{BOT_FILE_NAME}{extension}"
        )

        new_path = os.path.join(
            os.path.dirname(file),
            new_name
        )

        if os.path.abspath(file) != os.path.abspath(new_path):
            if os.path.exists(new_path):
                os.remove(new_path)

            os.replace(file, new_path)

        renamed_files.append(new_path)

    return renamed_files


async def update_progress_message(
    bot,
    chat_id,
    message
):
    last_text = ""

    while True:
        task = active_tasks.get(chat_id)

        if task is None:
            break

        if task.done():
            break

        data = progress_data.get(chat_id, {})

        status = data.get("status")

        if status == "preparing":
            text = "⏳ Подготавливаю загрузку..."

        elif status == "downloading":
            percent = data.get("percent", 0)
            downloaded = data.get("downloaded", 0)
            total = data.get("total", 0)
            speed = data.get("speed", 0)
            eta = data.get("eta")

            if total:
                text = (
                    f"⬇️ Загружаю...\n\n"
                    f"📊 {percent:.1f}%\n"
                    f"📦 {format_size(downloaded)} / "
                    f"{format_size(total)}\n"
                    f"⚡ {format_speed(speed)}"
                )

                if eta is not None:
                    text += f"\n⏱ Осталось: {eta} сек."

            else:
                text = (
                    f"⬇️ Загружаю...\n\n"
                    f"📦 Загружено: "
                    f"{format_size(downloaded)}\n"
                    f"⚡ Скорость: "
                    f"{format_speed(speed)}"
                )

        elif status == "processing":
            text = "⚙️ Обрабатываю файл..."

        elif status == "sending":
            text = "📤 Отправляю файл..."

        else:
            text = "⏳ Подготавливаю..."

        if text != last_text:
            try:
                await bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=message.message_id
                )
                last_text = text
            except Exception:
                pass

        await asyncio.sleep(2)


async def send_downloaded_files(
    bot,
    chat_id,
    files,
    media_type
):
    for file in files:
        if not os.path.exists(file):
            continue

        input_file = FSInputFile(file)

        if media_type in {
            "youtube_audio",
            "tiktok_audio"
        }:
            await bot.send_audio(
                chat_id=chat_id,
                audio=input_file,
                caption=CAPTION,
                title=BOT_FILE_NAME,
                performer="Saved Clips"
            )

        elif media_type == "tiktok_photo":
            await bot.send_photo(
                chat_id=chat_id,
                photo=input_file,
                caption=CAPTION
            )

        else:
            file_size = os.path.getsize(file)

            if file_size > MAX_VIDEO_SIZE:
                raise ValueError(
                    f"VIDEO_TOO_LARGE:{file_size}"
                )

            await bot.send_video(
                chat_id=chat_id,
                video=input_file,
                caption=CAPTION,
                supports_streaming=True
            )


async def download_and_send_media(
    bot,
    chat_id,
    url,
    media_type
):
    if is_download_active(chat_id):
        return

    task_id = uuid.uuid4().hex

    task_dir = os.path.join(
        DOWNLOADS_DIR,
        task_id
    )

    os.makedirs(
        task_dir,
        exist_ok=True
    )

    stop_event = threading.Event()

    stop_events[chat_id] = stop_event

    current_task = asyncio.current_task()

    active_tasks[chat_id] = current_task

    progress_data[chat_id] = {
        "status": "preparing",
        "percent": 0,
        "downloaded": 0,
        "total": 0,
        "speed": 0,
        "eta": None
    }

    progress_message = None
    progress_task = None

    try:
        progress_message = await bot.send_message(
            chat_id,
            "⏳ Подготавливаю загрузку..."
        )

        progress_task = asyncio.create_task(
            update_progress_message(
                bot,
                chat_id,
                progress_message
            )
        )

        check_cancel(chat_id)

        if media_type == "tiktok_photo":
            files = await asyncio.to_thread(
                download_with_gallery_dl,
                url,
                task_dir,
                chat_id
            )

        else:
            await asyncio.to_thread(
                download_with_ytdlp,
                url,
                task_dir,
                media_type,
                chat_id
            )

            check_cancel(chat_id)

            files = collect_files(task_dir)

        check_cancel(chat_id)

        if not files:
            raise RuntimeError(
                "Файлы не были найдены после загрузки"
            )

        files = rename_files(
            files,
            media_type
        )

        check_cancel(chat_id)

        if not files:
            raise RuntimeError(
                "Не удалось подготовить файлы"
            )

        if media_type in {
            "youtube_video",
            "tiktok_video",
            "instagram_video"
        }:
            valid_files = []

            for file in files:
                if not os.path.isfile(file):
                    continue

                size = os.path.getsize(file)

                if size > MAX_VIDEO_SIZE:
                    raise ValueError(
                        f"VIDEO_TOO_LARGE:{size}"
                    )

                valid_files.append(file)

            files = valid_files

            if not files:
                raise RuntimeError(
                    "Видео не найдено"
                )

        progress_data[chat_id] = {
            "status": "sending",
            "percent": 100,
            "downloaded": 0,
            "total": 0,
            "speed": 0,
            "eta": None
        }

        await asyncio.sleep(0.3)

        await send_downloaded_files(
            bot,
            chat_id,
            files,
            media_type
        )

        try:
            await bot.delete_message(
                chat_id,
                progress_message.message_id
            )
        except Exception:
            pass

        from keyboards.reply_kb import main_keyboard

        await bot.send_message(
            chat_id,
            "👇 Выберите, что хотите скачать:",
            reply_markup=main_keyboard()
        )

    except TikTokForbidden:
        print(
            f"[TIKTOK 403] chat_id={chat_id}: "
            f"TikTok запретил загрузку видеофайла",
            flush=True
        )

        if progress_message:
            try:
                await bot.edit_message_text(
                    "❌ TikTok не разрешил скачать это видео.\n\n"
                    "Попробуй другую ссылку или повтори попытку позже.",
                    chat_id=chat_id,
                    message_id=progress_message.message_id
                )
            except Exception:
                pass

    except DownloadCancelled:
        print(
            f"[CANCELLED] chat_id={chat_id}",
            flush=True
        )

        if progress_message:
            try:
                await bot.edit_message_text(
                    "⛔ Загрузка остановлена.\n🧹 Временные файлы удалены.",
                    chat_id=chat_id,
                    message_id=progress_message.message_id
                )
            except Exception:
                pass

    except ValueError as error:
        error_text = str(error)

        if error_text.startswith("VIDEO_TOO_LARGE:"):
            try:
                file_size = int(
                    error_text.split(":", 1)[1]
                )
            except Exception:
                file_size = 0

            print(
                f"[VIDEO TOO LARGE] chat_id={chat_id}: "
                f"{file_size} bytes",
                flush=True
            )

            if progress_message:
                try:
                    await bot.edit_message_text(
                        "❌ Видео слишком большое.\n\n"
                        f"📦 Размер видео: {format_size(file_size)}\n"
                        "🚫 Максимальный размер: 49 МБ\n\n"
                        "🎵 Попробуй скачать это видео "
                        "в формате аудио.",
                        chat_id=chat_id,
                        message_id=progress_message.message_id
                    )
                except Exception:
                    pass

        else:
            print(
                f"[ERROR] chat_id={chat_id}: "
                f"{type(error).__name__}: {error}",
                flush=True
            )

            if progress_message:
                try:
                    await bot.edit_message_text(
                        "❌ Не удалось скачать файл.\n\n"
                        "Проверь ссылку и попробуй ещё раз.",
                        chat_id=chat_id,
                        message_id=progress_message.message_id
                    )
                except Exception:
                    pass

    except asyncio.CancelledError:
        stop_event.set()

        print(
            f"[CANCELLED] chat_id={chat_id}",
            flush=True
        )

        raise

    except Exception as error:
        print(
            f"[ERROR] chat_id={chat_id}: "
            f"{type(error).__name__}: {error}",
            flush=True
        )

        traceback.print_exc()

        if progress_message:
            try:
                await bot.edit_message_text(
                    "❌ Не удалось скачать файл.\n\n"
                    "Проверь ссылку и попробуй ещё раз.",
                    chat_id=chat_id,
                    message_id=progress_message.message_id
                )
            except Exception:
                pass

    finally:
        if progress_task:
            progress_task.cancel()

            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        try:
            shutil.rmtree(
                task_dir,
                ignore_errors=True
            )
        except Exception:
            pass

        if active_tasks.get(chat_id) is current_task:
            active_tasks.pop(
                chat_id,
                None
            )

        stop_events.pop(
            chat_id,
            None
        )

        progress_data.pop(
            chat_id,
            None
        )


async def stop_all_tasks(chat_id):
    task = active_tasks.get(chat_id)
    event = stop_events.get(chat_id)

    stopped = False

    if event:
        event.set()
        stopped = True

    if task and not task.done():
        task.cancel()
        stopped = True

    if os.path.exists(DOWNLOADS_DIR):
        for name in os.listdir(DOWNLOADS_DIR):
            path = os.path.join(
                DOWNLOADS_DIR,
                name
            )

            if os.path.isdir(path):
                try:
                    shutil.rmtree(
                        path,
                        ignore_errors=True
                    )
                except Exception:
                    pass

    active_tasks.pop(
        chat_id,
        None
    )

    stop_events.pop(
        chat_id,
        None
    )

    progress_data.pop(
        chat_id,
        None
    )

    return stopped


def cleanup_downloads():
    os.makedirs(
        DOWNLOADS_DIR,
        exist_ok=True
    )

    for name in os.listdir(DOWNLOADS_DIR):
        path = os.path.join(
            DOWNLOADS_DIR,
            name
        )

        try:
            if os.path.isdir(path):
                shutil.rmtree(
                    path,
                    ignore_errors=True
                )
            else:
                os.remove(path)
        except Exception as error:
            print(
                f"[CLEANUP ERROR] {path}: {error!r}",
                flush=True
            )