import os
import random

JWT_KEY = os.getenv("JWT_KEY")
if not JWT_KEY:
    JWT_KEY = random.randbytes(64)


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    exit("Error: no token provided")
