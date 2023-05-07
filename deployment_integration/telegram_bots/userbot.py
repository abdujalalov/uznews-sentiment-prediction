import re

import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

API_ID = 26457469
API_HASH = 'dbe71c9cc9a9b5df24dc825f1f348207'

LOGS_CHANNEL_ID = -1001922338680
CHANNELS_TO_LISTEN = [-1001041138277, -1001167945861, -1001138620944, -1001558288933, -1001802910786] # last one is our test gc. предпоследний это тестовый канал
# @gazetauz_ozb
# @kunuz
# @UzReport_uz

TOPICS = {
    'positive': {
        'chat_id': -1001491005437,
        'message_id': 44
    },
    'negative': {
        'chat_id': -1001491005437,
        'message_id': 46
    },
    'promotional': {
        'chat_id': -1001491005437,
        'message_id': 50
    }
}

app = Client("sentiment_bot", api_id=API_ID, api_hash=API_HASH)


def clean_patterns(text, channel_name):
    if channel_name == "UzReport_uz":
        # Remove "Batafsil 👉" pattern and URL
        text = re.sub(r'Batafsil 👉.*', '', text)
        text = re.sub(r'http\S+', '', text)
        # Remove "@uzreport_uz" mentions
        text = re.sub(r'@uzreport_uz', '', text)
    elif channel_name == "kunuz":
        # Remove URL and "@kunuz" mentions
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@kunuz', '', text)
    elif channel_name == "gazetauz_ozb":
        # Remove URL and "Kanalga obuna bo‘ling 👉 @gazetauz_ozb" pattern
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'Kanalga obuna bo‘ling.*', '', text)

    # Remove leading/trailing whitespaces and return cleaned text
    return text.strip()


async def get_sentiment(text):
    async with aiohttp.ClientSession() as session:
        async with session.post("http://20.113.98.85:80/sentiment", json=[{"text": text}]) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                return None


async def process_message(client, message):
    text = message.text or message.caption
    if text:
        channel_name = (await client.get_chat(message.chat.id)).username or ""
        text = clean_patterns(text, channel_name)
        if "reklama" in text.lower():
            topic = TOPICS["promotional"]
            chat_id = topic["chat_id"]
            message_id = topic["message_id"]

            channel_name = (await client.get_chat(message.chat.id)).title

            # shows original message and its probability of being positive or negative
            prob_caption = f'\n\n<i>Original message from <b><a href="{message.link}">{channel_name}</a></b></i>'

            # forwarded_message = await client.send_message(chat_id=chat_id, text=text, reply_to_message_id=message_id, parse_mode=ParseMode.HTML)
            forwarded_message = await client.copy_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.id,
                reply_to_message_id=message_id,
            )
            # make reklama word bold
            text = text.replace("reklama", "<b>reklama</b>")

            print(f"Forwarded message to promotional topic: {text}")
            # send message to logs channel
            await client.send_message(chat_id=LOGS_CHANNEL_ID, text=f"💲 Promotional: {text} \n\n{message.link}", parse_mode=ParseMode.HTML)

        else:
            result = await get_sentiment(text)
            if result:
                label = result[0]["label"]
                prob = result[0]["probability"]
                cleaned_text = result[0]['cleaned_text']

                topic = TOPICS[label]
                chat_id = topic["chat_id"]
                message_id = topic["message_id"]

                channel_name = (await client.get_chat(message.chat.id)).title

                prob_caption = f'\n\n<i>Original message from <b><a href="{message.link}">{channel_name}</a></b> with probability:</i> <code>{prob:.4f}</code>'

                forwarded_message = await client.copy_message(
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.id,
                    reply_to_message_id=message_id,
                    parse_mode=ParseMode.HTML
                )

                label = label.capitalize()
                label = f"🟢 {label} " if label == "Positive" else f"🔴 {label}"

                print(f"Forwarded message to {label} topic: {forwarded_message.text or forwarded_message.caption}")
                await client.send_message(chat_id=LOGS_CHANNEL_ID, text=f"<b>{label}</b> (<code>{prob:.4f}</code>)\n\n{cleaned_text} \n\n{message.link}")

            else:
                channel_name = (await client.get_chat(message.chat.id)).title
                print(f"Failed to get sentiment analysis result for message: {message.text} from channel: {channel_name}")
                await client.send_message(chat_id=LOGS_CHANNEL_ID, text=f"❗️ Failed to get sentiment analysis result for message: {message.text} from channel: {channel_name}")
    else:
        print("Could not process message because it does not contain proper text")



@app.on_message(filters.chat(CHANNELS_TO_LISTEN))
async def new_message_handler(client, message):
    await process_message(client, message)


app.run()
