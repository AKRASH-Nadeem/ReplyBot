# import for GUI signals and threads
from PyQt5.QtCore import QRunnable, QThreadPool,QThread,pyqtSignal,QObject,pyqtSlot
import threading
# Import for telegram bot and async code usage
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils import executor
import re
# SQLite database imports
import sqlite3

# Making bot code

async def bot_main(token,status):
    bot = Bot(token)
    dp = Dispatcher(bot)
    try:
        # Use the 'get_me' method to check if the token is valid
        me = await bot.get_me()
        print("Bot information:", me)
        print("Token is valid!")
        mydict = me.__dict__["_values"]
        mydict['status'] = True
        print(mydict)
        status.emit(mydict)
    except Exception as e:
        print("Token is invalid:", e)
        mydict = {"status":False,"message":str(e)}
        status.emit(mydict)
    finally:
        # Close the bot session gracefully
        await dp.storage.close()
        await dp.storage.wait_closed()
        session = await bot.get_session()
        await session.close()
    return True

class Test_Bot(QThread):
    status = pyqtSignal(dict)
    def __init__(self,token):
        super().__init__()
        self.token = token

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_main(self.token,self.status))
        return
        






class AIogramBot(QThread):
    stopped = pyqtSignal(bool)
    started = pyqtSignal()
    error = pyqtSignal(str)
    def __init__(self,token,bot_started_signal: pyqtSignal):
        super().__init__()
        try:
            self.bot = Bot(token=token)
            self.dp = Dispatcher(self.bot)
            self.bot_started_signal = bot_started_signal
        except Exception as error:
            print(error)
            self.error.emit(str(error))
            raise error
        
        @self.dp.message_handler()
        async def get_messages(message: types.Message):
            try:
                db = sqlite3.connect("information.db")
                cursor = db.cursor()
                cursor.execute("SELECT * FROM messages")
                rows = cursor.fetchall()
                for row in rows:
                    if row[2] != "" and row[2] != None:
                        if row[4] == 0:
                            print("checking in lowercase : ",message.text.lower()," | ",row[2].lower())
                            if message.text.lower() == row[2].lower():
                                await message.reply(row[1])
                                break
                        else:
                            if message.text == row[2]:
                                await message.reply(row[1])
                                break
                    elif row[3] != "" and row[3] != None:
                        if row[4] == 0:
                            matches = re.findall(row[3],message.text,re.IGNORECASE)
                        else:
                            matches = re.findall(row[3],message.text)
                        if len(matches)>0:
                            await message.reply(row[1])
                            break
                cursor.close()
                db.close()
            except sqlite3.Error as e:
                print(f"Error occurred: {e}")
    async def started_signal(self,dp):
        self.started.emit()
        self.bot_started_signal.emit(True)
    def start_bot(self):
        try:
            print("bot starting...")
            executor.start_polling(dispatcher=self.dp,skip_updates=True,on_startup=self.started_signal)
        except Exception as error:
            print(error)
            self.error.emit(str(error))
            return

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.start_bot()
        except Exception as error:
            print(error)
            self.error.emit(str(error))
            return 

    def stop_bot(self):
        self.terminate()
        self.wait()
        print("bot is stopped")
        self.stopped.emit(True)
        self.bot_started_signal.emit(False)
