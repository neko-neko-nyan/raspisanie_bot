import os
import random

JWT_KEY = os.getenvb(b"JWT_KEY")
if not JWT_KEY:
    JWT_KEY = random.randbytes(64)


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    exit("Error: no token provided")


ENABLE_DEBUG_DATA = True
UPDATE_INTERVAL = 15 * 60
TIMETABLE_URL = "http://novkrp.ru/raspisanie.htm"
