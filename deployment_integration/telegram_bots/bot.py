import aiohttp
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

bot = Bot(token="6089809737:AAEHL5_sXLT_agI8l--fPkjwDPziILWbE7Y")
dp = Dispatcher(bot)

async def get_sentiment(text):
    async with aiohttp.ClientSession() as session:
        async with session.post("http://127.0.0.1:8000/sentiment", json=[{"text": text}]) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                return None


@dp.message_handler(commands=['sentiment'])
async def sentiment_handler(message: types.Message):
    text = message.text.replace('/sentiment', '').strip()
    if text:
        result = await get_sentiment(text)
        if result:
            label = result[0]['label']
            prob = result[0]['probability']
            await message.reply(f"The sentiment of '<code>{text}</code>' \n\nis: <b>{label}</b> with probability <code>{prob}</code>", parse_mode=types.ParseMode.HTML)
        else:
            await message.reply("Failed to get sentiment analysis result")
    else:
        await message.reply("Please provide text to analyze\n\n Example: /sentiment O'zbekistonning poytaxti Toshkent shahri")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
