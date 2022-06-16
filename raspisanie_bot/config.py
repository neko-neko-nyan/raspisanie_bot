import json
import pathlib

BOT_DIR = pathlib.Path(__file__).parent.parent

config = json.loads((BOT_DIR / "config.json").read_text(encoding="utf8"))
_features = None
_replace_pair_names = None

INVITE_SIGN_KEY = config.get("INVITE_SIGN_KEY", "").encode()
JWT_KEY_FOR_ERRORS = config.get("JWT_KEY_FOR_ERRORS", "").encode()
BOT_TOKEN = config.get("BOT_TOKEN")
UPDATE_INTERVAL = config.get("UPDATE_INTERVAL", 3600)
TIMETABLE_URL = config.get("TIMETABLE_URL", "")


def feature_enabled(name):
    global _features
    if _features is None:
        _features = config.get("enable_features", {})

    return bool(_features.get(name, False))


def get_pair_name(name):
    global _replace_pair_names
    if _replace_pair_names is None:
        _replace_pair_names = config.get("replace_pair_names", {})

    return _replace_pair_names.get(name, name)
