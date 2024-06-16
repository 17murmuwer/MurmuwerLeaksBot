import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
import os
import aiofiles
import aiohttp
from time import time
import phonenumbers as pnumb
from phonenumbers import geocoder, carrier, timezone
import logging
import re
import requests
API_TOKEN = 'Семпай, у т-тебя такой б-б-большой токен, хочу чтобы ты вставил его в меня:)'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


async def search_directory(directory, search_text, message):
    total_files = sum(len(files) for _, _, files in os.walk(directory))
    files_checked = 0

    progress_message = await message.answer("🔍 Поиск в процессе... ")
    progress_percent = 0

    for root, dirs, files in os.walk(directory):
        for file_name in files:
            if file_name.endswith(".txt"):
                file_path = os.path.join(root, file_name)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    for line in file:
                        if search_text in line:
                            await message.answer(f"🔍 Найдено в: {file_path}\n📄 Строка: {line.strip()}",
                                                 parse_mode=ParseMode.HTML)
            files_checked += 1
            new_progress_percent = int(files_checked / total_files * 100)
            if new_progress_percent != progress_percent:
                progress_percent = new_progress_percent
                progress_bar_length = 30
                progress_bar = "█" * int(progress_percent / (100 / progress_bar_length)) + " " * (
                        progress_bar_length - int(progress_percent / (100 / progress_bar_length)))
                progress_message_text = f"🔍 Проверено: {progress_percent}%\n[{progress_bar}]"
                await bot.edit_message_text(chat_id=progress_message.chat.id, message_id=progress_message.message_id,
                                            text=progress_message_text)
    if files_checked == 0:
        await message.answer("❌ Не найдено файлов для проверки.")
    else:
        await message.answer("✅ Поиск завершен.")


async def process_file(file_path, search_text, message):
    async with aiofiles.open(file_path, mode='r', encoding='utf-8', errors='ignore') as file:
        found = False
        async for line in file:
            if search_text in line:
                await message.answer(f"💾 Найдено в: {file_path}\n📄 Строка: {line.strip()}", reply_markup=main_keyboard())
                await asyncio.sleep(0.1)
                found = True


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот для поиска по утечкам. Нажми на кнопку, чтобы начать поиск.",
                         reply_markup=main_keyboard())


@dp.message_handler(lambda message: message.text == '🔍 Начать поиск', state="*")
async def start_search(message: types.Message):
    await message.answer("Отправьте мне текст запроса для поиска.", reply_markup=main_keyboard())


@dp.message_handler(lambda message: message.text.startswith('+'))
async def handle_phone_number(message: types.Message):
    phone_number = message.text.strip()
    await process_phone_number(phone_number, message)


async def process_phone_number(phone_number, message):
    try:
        parsed_number = pnumb.parse(phone_number, None)
        location = geocoder.description_for_number(parsed_number, "en")
        isp = carrier.name_for_number(parsed_number, "en")
        tz = timezone.time_zones_for_number(parsed_number)

        is_valid_number = pnumb.is_valid_number(parsed_number)
        is_possible_number = pnumb.is_possible_number(parsed_number)
        formatted_number = pnumb.format_number(parsed_number, pnumb.PhoneNumberFormat.INTERNATIONAL)
        formatted_number_for_mobile = pnumb.format_number_for_mobile_dialing(parsed_number, "ID", with_formatting=True)
        number_type = pnumb.number_type(parsed_number)
        region_code = pnumb.region_code_for_number(parsed_number)
        timezoneF = ', '.join(tz)

        info = (
            f"<b>Информация о номере телефона📞 :</b>\n"
            f"Локация: {location}\n"
            f"Код региона:☎ {region_code}\n"
            f"Временная зона🕛: {timezoneF}\n"
            f"Оператор📡: {isp}\n"
            f"Валидность номера: {is_valid_number}\n"
            f"Возможный номер: {is_possible_number}\n"
            f"Интернациональный формат: {formatted_number}\n"
            f"Мобильный формат: {formatted_number_for_mobile}\n"
            f"Оригинальный номер: {parsed_number.national_number}\n"
            f"E164 формат: {pnumb.format_number(parsed_number, pnumb.PhoneNumberFormat.E164)}\n"
            f"Страны код: {parsed_number.country_code}\n"
            f"Локальный номер: {parsed_number.national_number}\n"
        )

        if number_type == pnumb.PhoneNumberType.MOBILE:
            info += "Тип: Это мобильный телефон\n"
        elif number_type == pnumb.PhoneNumberType.FIXED_LINE:
            info += "Тип: Это стационарный телефон\n"
        else:
            info += "Тип: Другой тип номера (Либо виртуальный, либо не используется, либо введен неверно)\n"

        await message.answer(info, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
    except Exception as e:
        print(f"Ошибка при обработке номера телефона: {e}")
        await message.answer("Произошла ошибка при обработке номера телефона. Пожалуйста, попробуйте еще раз позже.",
                             reply_markup=main_keyboard())


email_domains = ['gmail.com', 'inbox.ru', 'mail.ru', 'rambler.ru']


@dp.message_handler(lambda message: message.text and '@' in message.text and all(domain not in message.text for domain in email_domains), state="*")
async def handle_username_search(message: types.Message):
    text = message.text
    username = text.split("@")[-1].strip()
    await search_social_media(message, username)


async def search_social_media(message: types.Message, username: str):
    links = {
            'instagram': 'https://www.instagram.com/{}',
            'facebook': 'https://www.facebook.com/{}',
            'twitter': 'https://www.twitter.com/{}',
            'youtube': 'https://www.youtube.com/{}',
            'blogger': 'https://{}.blogspot.com',
            'reddit': 'https://www.reddit.com/user/{}',
            'pinterest': 'https://www.pinterest.com/{}',
            'github': 'https://www.github.com/{}',
            'tumblr': 'https://{}.tumblr.com',
            'flickr': 'https://www.flickr.com/people/{}',
            'vimeo': 'https://vimeo.com/{}',
            'soundcloud': 'https://soundcloud.com/{}',
            'disqus': 'https://disqus.com/{}',
            'medium': 'https://medium.com/@{}',
            'deviantart': 'https://{}.deviantart.com',
            'vk': 'https://vk.com/{}',
            'about.me': 'https://about.me/{}',
            'imgur': 'https://imgur.com/user/{}',
            'slideshare': 'https://slideshare.net/{}',
            'spotify': 'https://open.spotify.com/user/{}',
            'scribd': 'https://www.scribd.com/{}',
            'badoo': 'https://www.badoo.com/en/{}',
            'patreon': 'https://www.patreon.com/{}',
            'XXX.ru(porn)': 'https://www.xv-ru.com/{}',
            'bitbucket': 'https://bitbucket.org/{}',
            'dailymotion': 'https://www.dailymotion.com/{}',
            'etsy': 'https://www.etsy.com/shop/{}',
            'cashme': 'https://cash.me/{}',
            'behance': 'https://www.behance.net/{}',
            'goodreads': 'https://www.goodreads.com/{}',
            'instructables': 'https://www.instructables.com/member/{}',
            'keybase': 'https://keybase.io/{}',
            'kongregate': 'https://kongregate.com/accounts/{}',
            'livejournal': 'https://{}.livejournal.com',
            'angellist': 'https://angel.co/{}',
            'last.fm': 'https://last.fm/user/{}',
            'dribbble': 'https://dribbble.com/{}',
            'codecademy': 'https://www.codecademy.com/{}',
            'gravatar': 'https://en.gravatar.com/{}',
            'foursquare': 'https://foursquare.com/{}',
            'gumroad': 'https://www.gumroad.com/{}',
            'newgrounds': 'https://{}.newgrounds.com',
            'wattpad': 'https://www.wattpad.com/user/{}',
            'canva': 'https://www.canva.com/{}',
            'creativemarket': 'https://creativemarket.com/{}',
            'trakt': 'https://www.trakt.tv/users/{}',
            '500px': 'https://500px.com/{}',
            'buzzfeed': 'https://buzzfeed.com/{}',
            'tripadvisor': 'https://tripadvisor.com/members/{}',
            'hubpages': 'https://{}.hubpages.com',
            'contently': 'https://{}.contently.com',
            'houzz': 'https://houzz.com/user/{}',
            'blip.fm': 'https://blip.fm/{}',
            'wikipedia': 'https://www.wikipedia.org/wiki/User:{}',
            'codementor': 'https://www.codementor.io/{}',
            'reverbnation': 'https://www.reverbnation.com/{}',
            'designspiration65': 'https://www.designspiration.net/{}',
            'bandcamp': 'https://www.bandcamp.com/{}',
            'colourlovers': 'https://www.colourlovers.com/love/{}',
            'ifttt': 'https://www.ifttt.com/p/{}',
            'slack': 'https://{}.slack.com',
            'okcupid': 'https://www.okcupid.com/profile/{}',
            'trip': 'https://www.trip.skyscanner.com/user/{}',
            'ello': 'https://ello.co/{}',
            'hackerone': 'https://hackerone.com/{}',
            'freelancer': 'https://www.freelancer.com/u/{}',
            'academia': 'https://independent.academia.edu/{}',
            'admireme': 'https://admireme.vip/{}',
            'airlinepilot': 'https://airlinepilot.life/u/{}',
            'airbit': 'https://airbit.com/{}',
            'alik': 'https://www.alik.cz/{}',
            'allthingsworn': 'https://www.allthingsworn.com/profile/{}',
            'allmylinks': 'https://allmylinks.com/{}',
            'aminoapps': 'https://aminoapps.com/u/{}',
            'aniworld': 'https://aniworld.to/user/profil/{}',
            'appledeveloperforums': 'https://developer.apple.com/forums/profile/{}',
            'archiveofourown': 'https://archiveofourown.org/users/{}',
            'artstation': 'https://www.artstation.com/{}',
            'asciinema': 'https://asciinema.org/~{}',
            'askfedora': 'https://ask.fedoraproject.org/u/{}',
            'askfm': 'https://ask.fm/{}',
            'audiojungle': 'https://audiojungle.net/user/{}',
            'autofrage': 'https://www.autofrage.net/nutzer/{}',
            'avizo': 'https://www.avizo.cz/{}',
            'bazar': 'https://www.bazar.cz/{}',
            'bezuzyteczna': 'https://bezuzyteczna.pl/uzytkownicy/{}',
            'biggerpockets': 'https://www.biggerpockets.com/users/{}',
            'dangerousthingsforum': 'https://forum.dangerousthings.com/u/{}',
            'bitwardencommunity': 'https://community.bitwarden.com/u/{}',
            'blipfoto': 'https://www.blipfoto.com/{}',
            'boothpm': 'https://{}.booth.pm/',
            'behance2': 'https://www.behance.net/{}',
            'bodyspace': 'https://bodyspace.bodybuilding.com/{}',
            'bongacams': 'https://pt.bongacams.com/profile/{}',
            'careerhabr': 'https://career.habr.com/{}',
            'chaturbate': 'https://chaturbate.com/{}',
            'chesscom': 'https://www.chess.com/member/{}',
            'codecademy2': 'https://www.codecademy.com/profiles/{}',
            'cryptomatorcommunity': 'https://community.cryptomator.org/u/{}',
            'duolingo': 'https://www.duolingo.com/profile/{}'
    }

    found_results = await verify_username(username, links)
    if found_results:
        results_message = "<b>Пользователь найден в следующих социальных сетях:</b>\n"
        for social_network, url in found_results:
            results_message += f"{social_network}: {url}\n"
        await message.answer(results_message, parse_mode=types.ParseMode.HTML, reply_markup=main_keyboard())
    else:
        await message.answer("Пользователь не найден в указанных социальных сетях.", reply_markup=main_keyboard())


async def verify_username(username, links):
    async with aiohttp.ClientSession() as session:
        tasks = [check_status(session, social_network, url, username) for social_network, url in links.items()]
        return [result for result in await asyncio.gather(*tasks) if result]


async def check_status(session, social_network, url, username):
    try:
        async with session.get(url.format(username)) as resp:
            if resp.status == 200:
                return (social_network, url.format(username))
    except aiohttp.ClientError:
        pass
    return None
IP_REGEX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

# Новый обработчик сообщений для поиска IP-адресов
@dp.message_handler(lambda message: IP_REGEX.search(message.text))
async def handle_ip_message(message: types.Message):
    # Извлекаем IP-адрес из текста сообщения
    targetip = IP_REGEX.search(message.text).group()
    # Получаем информацию о IP-адресе
    info = await get_ip_info(targetip)
    # Отправляем информацию пользователю
    await message.answer(info)

# Функция для получения информации о IP-адресе
async def get_ip_info(targetip):
    r = requests.get("http://ip-api.com/json/" + targetip)
    result = ""
    if r.status_code == 200:
        result += f"\n[*] Подробная информация об IP-адресе:\n"
        if r.json()['status'] == 'success':
            result += f"[*] Статус         : {r.status_code}\n"
            result += f"[*] Статус         : {r.json()['status']}\n"
            result += f"[*] Целевой IP-адрес: {r.json()['query']}\n"
            result += f"[*] Страна         : {r.json()['country']}\n"
            result += f"[*] Код страны     : {r.json()['countryCode']}\n"
            result += f"[*] Город          : {r.json()['city']}\n"
            result += f"[*] Часовой пояс   : {r.json()['timezone']}\n"
            result += f"[*] Название региона: {r.json()['regionName']}\n"
            result += f"[*] Регион         : {r.json()['region']}\n"
            result += f"[*] Почтовый индекс: {r.json()['zip']}\n"
            result += f"[*] Широта         : {r.json()['lat']}\n"
            result += f"[*] Долгота        : {r.json()['lon']}\n"
            result += f"[*] Провайдер      : {r.json()['isp']}\n"
            result += f"[*] Организация    : {r.json()['org']}\n"
            result += f"[*] AS             : {r.json()['as']}\n"
            result += f"[*] Местоположение  : {r.json()['lat']}, {r.json()['lon']}\n"
            result += f"[*] Google Карта   : https://maps.google.com/?q={r.json()['lat']},{r.json()['lon']}\n"
        elif r.json()['status'] == 'fail':
            result += f"[*] Статус         : {r.status_code}\n"
            result += f"[*] Статус         : {r.json()['status']}\n"
            result += f"[*] Сообщение      : {r.json()['message']}\n"
            if r.json()['message'] == 'invalid query':
                result += f"\n[!] {targetip} - это неверный IP-адрес, попробуйте другой IP-адрес.\n"
            elif r.json()['message'] == 'private range':
                result += f"\n[!] {targetip} - это частный IP-адрес, его нельзя проследить.\n"
            elif r.json()['message'] == 'reserved range':
                result += f"\n[!] {targetip} - это зарезервированный IP-адрес, его нельзя проследить.\n"
            else:
                result += f"\nПроверьте ваше интернет-соединение.\n"
    return result

@dp.message_handler(lambda message: message.text == '⛔ Остановить поиск', state="*")
async def stop_search(message: types.Message):
    await message.answer("Поиск остановлен.", reply_markup=main_keyboard())


@dp.message_handler(lambda message: message.text and message.text not in ['🔍 Начать поиск', '⛔ Остановить поиск'],
                    state="*")
async def search_files(message: types.Message):
    directory_to_search = "F:\\fordatabase"
    search_text = message.text
    await search_directory(directory_to_search, search_text, message)
    log_search(message.from_user.username, search_text)


def log_search(username, search_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("searchlog.txt", "a") as log_file:
        log_file.write(f"{timestamp} - Пользователь {username} сделал запрос: {search_text}\n")


def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('🔍 Начать поиск'))
    keyboard.add(KeyboardButton('⛔ Остановить поиск'))
    return keyboard


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(dp.start_polling())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(dp.stop_polling())
        loop.close()
