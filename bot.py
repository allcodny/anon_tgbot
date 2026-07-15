import asyncio
from typing import Optional
import aiomysql
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram import types
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument


bot = Bot(token="YOUR_TOKEN")
bot_id = 
dp = Dispatcher()
adm = 

dbconfig = {"host": 'localhost',
                "user": '',
                "password": '',
                "db": '',
                'port': 3307,
                'charset': 'utf8mb4'}

ban_users: set = {}

class UserMes:
    def __init__(self, user_id: int, id_in_user_chat: int, id_in_adm_chat: int):
        self.user_id = user_id
        self.id_in_user_chat = id_in_user_chat
        self.id_in_adm_chat = id_in_adm_chat

    def print(self):
        print(f"user_id: {self.user_id}")
        print(f"id_in_user_chat: {self.id_in_user_chat}")
        print(f"id_in_adm_chat: {self.id_in_adm_chat}")

class UserMess:
    def __init__(self):
        self.list: list = []

    def put(self, mes: UserMes):
        self.list.append(mes)

    async def append(self, mes: UserMes):
        self.list.append(mes)
        await Database.add_mes(mes.user_id, mes.id_in_user_chat, mes.id_in_adm_chat)

    def print(self):
        for mes in self.list:
            mes.print()

    async def get_from_adm(self, mes_id):
        for mes in self.list:
            if mes.id_in_adm_chat == mes_id:
                return mes
            
    async def get_from_user(self, mes_id):
        for mes in self.list:
            if mes.id_in_user_chat == mes_id:
                return mes

list_mes = UserMess()

class Database:
    _pool: Optional[aiomysql.Pool] = None

    @classmethod
    async def initialize_pool(cls):
        global dbconfig
        try:
            cls._pool = await aiomysql.create_pool(
                minsize=5,
                maxsize=20,
                autocommit=True,
                pool_recycle=3600,
                **dbconfig
            )
            print("db done!")
            return True
        except Exception as e:
            await bot.send_message(adm, f"⚠️ Error connecting to database! \n\n{e}")
            return False

    @classmethod
    async def get_connection(cls):
        if not cls._pool:
            await cls.initialize_pool()
        elif cls._pool.closed:
            await cls.initialize_pool()
        return cls._pool

    @staticmethod
    async def execute_query(query: str, params=None, fetchall=False):
        pool = await Database.get_connection()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    await cursor.execute(query, params or ())
                    
                    if fetchall:
                        result = await cursor.fetchall()
                    else:
                        result = True
                    
                    return result
                except Exception as e:
                    await bot.send_message(adm, f"⚠️ Error while requesting {query}: \n\n{e}")
                    return False
                
    @staticmethod
    async def get_ban_user():
        query = "SELECT user_id FROM ban_users"
        return await Database.execute_query(query, (), fetchall=True)
    
    @staticmethod
    async def ban_user(user_id: int):
        query = """
            INSERT IGNORE INTO ban_users (user_id) 
            VALUES (%s)
        """
        return await Database.execute_query(query, (user_id,))
    
    @staticmethod
    async def unban_user(user_id: int):
        query = "DELETE FROM ban_users WHERE user_id = %s"
        return await Database.execute_query(query, (user_id,))
    
    @staticmethod
    async def get_mes():
        query = "SELECT * FROM anon_mes"
        result = await Database.execute_query(query, (), fetchall=True)
        return result

    @staticmethod
    async def add_mes(user_id: int, id_user_chat: int, id_adm_chat: int):
        query = """
            INSERT IGNORE INTO anon_mes (user_id, id_in_user_chat, id_in_adm_chat) 
            VALUES (%s, %s, %s)
        """
        return await Database.execute_query(query, (user_id, id_user_chat, id_adm_chat))


async def init_database():
    global ban_users
    if await Database.initialize_pool():
        result = await Database.get_ban_user()
        ban_users = {row['user_id'] for row in result}
        print(ban_users)
        result = await Database.get_mes()
        for obj in result:
            list_mes.put(UserMes(obj['user_id'], obj['id_in_user_chat'], obj['id_in_adm_chat']))
        list_mes.print()


@dp.message(Command("start"))
async def start_command(message: types.Message):
    if message.from_user.id in ban_users:
        await message.answer("<i>Unfortunately, you have been banned...</i>", parse_mode="HTML")
    else:
        await message.answer('''Here you can send any message anonymously!''', parse_mode="HTML", disable_web_page_preview=True)

media_groups = {}


@dp.message(F.media_group_id & (F.photo | F.video | F.document))
async def handle_album(message: types.Message):
    if message.from_user.id in ban_users:
        await message.answer("<i>Unfortunately, you have been banned...</i>", parse_mode="HTML")
        return
    
    if message.reply_to_message and message.reply_to_message.from_user.id==bot_id:
        reply = True
    else:
        reply = False
    
    media_group_id = message.media_group_id

    if media_group_id not in media_groups:
        media_groups[media_group_id] = []
        asyncio.create_task(send_album_later(media_group_id, reply))

    media_groups[media_group_id].append(message)


async def send_album_later(media_group_id: str, reply: bool):
    await asyncio.sleep(0.2)

    messages = media_groups.pop(media_group_id, [])
    media = []

    for msg in messages:
        spoiler = msg.has_media_spoiler or False

        if msg.photo:
            media.append(
                InputMediaPhoto(
                    media=msg.photo[-1].file_id,
                    caption=msg.caption if not media else None,
                    caption_entities=msg.caption_entities if not media else None,
                    has_spoiler=spoiler
                )
            )
        elif msg.video:
            media.append(
                InputMediaVideo(
                    media=msg.video.file_id,
                    caption=msg.caption if not media else None,
                    caption_entities=msg.caption_entities if not media else None,
                    has_spoiler=spoiler
                )
            )
        elif msg.document:
            media.append(
                InputMediaDocument(
                    media=msg.document.file_id,
                    caption=msg.caption if not media else None,
                    caption_entities=msg.caption_entities if not media else None
                )
            )

    if media:
        if reply:
            message = messages[0]
            if message.from_user.id == adm:
                m = await list_mes.get_from_adm(message.reply_to_message.message_id)
                mes = await bot.send_media_group(m.user_id, media, reply_to_message_id=m.id_in_user_chat)
                for m in mes:
                    await list_mes.append(UserMes(message.from_user.id, m.message_id, message.message_id))
            else:
                m = await list_mes.get_from_user(message.reply_to_message.message_id)
                mes = await bot.send_media_group(m.user_id, media, reply_to_message_id=m.id_in_adm_chat)
                for m in mes:
                    await list_mes.append(UserMes(message.from_user.id, message.message_id, m.message_id))
        else:
            mes = await bot.send_media_group(adm, media)
            for i in range(0, len(mes)):
                await list_mes.append(UserMes(messages[0].from_user.id, messages[i].message_id, mes[i].message_id))
        r_mes = await bot.send_message(messages[0].from_user.id, "✅ The message has been sent successfully.")
        asyncio.create_task(delete_mes(r_mes))

@dp.message()
async def handle_messages(message: types.Message):
    if message.from_user.id in ban_users:
        await message.answer("<i>Unfortunately, you have been banned...</i>", parse_mode="HTML")
        return
    elif message.reply_to_message and message.reply_to_message.from_user.id==bot_id:
        if message.from_user.id == adm:
            m = await list_mes.get_from_adm(message.reply_to_message.message_id)
            if message.text == "ban":
                ban_users.add(m.user_id)
                result = await Database.ban_user(m.user_id)
                if result:
                    await message.answer(f"User tg://user?id={m.user_id} has been successfully banned!")
                else:
                    await message.answer(f"Failed to add to database tg://user?id={m.user_id}.")
                return
            elif message.text.lower() == "id":
                await message.answer(f"ID: {m.user_id}\nURL: tg://user?id={m.user_id}")
                return
            mes = await message.copy_to(m.user_id, reply_to_message_id=m.id_in_user_chat)
            await list_mes.append(UserMes(message.from_user.id, mes.message_id, message.message_id))
        else:
            m = await list_mes.get_from_user(message.reply_to_message.message_id)
            mes = await message.copy_to(m.user_id, reply_to_message_id=m.id_in_adm_chat)
            await list_mes.append(UserMes(message.from_user.id, message.message_id, mes.message_id))
    elif message.from_user.id == adm:
        if message.text.startswith("ban"):
            user_ids = list(map(int, message.text[3:].split()))
            for id in user_ids:
                ban_users.add(id)
                result = await Database.ban_user(id)
                if not result:
                    await message.answer(f"Failed to add to database tg://user?id={id}.")
            await message.answer("Done!")
            return
        elif message.text.startswith("unban"):
            user_ids = list(map(int, message.text[3:].split()))
            for id in user_ids:
                ban_users.remove(id)
                result = await Database.unban_user(id)
                if result:
                    await message.answer(f"User tg://user?id={id} has been successfully unbanned!")
                else:
                    await message.answer(f"Failed to delete from database tg://user?id={id}.")
            await message.answer("Done!")
            return
    else:
        m = await message.copy_to(adm)
        await list_mes.append(UserMes(message.from_user.id, message.message_id, m.message_id))
    r_mes = await message.answer("✅ The message has been sent successfully.")
    asyncio.create_task(delete_mes(r_mes))

async def delete_mes(message: types.Message):
    await asyncio.sleep(3)
    await message.delete()


async def main():
    await init_database()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
