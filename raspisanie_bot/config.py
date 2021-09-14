import os
import random

JWT_TOKEN = os.getenv("JWT_TOKEN")
if not JWT_TOKEN:
    JWT_TOKEN = random.randbytes(64)


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    exit("Error: no token provided")
