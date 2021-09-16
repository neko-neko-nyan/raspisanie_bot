from .admin import install_admin
from .invite import install_invite
from .my import install_my
from .search import install_search
from .settings import install_settings
from .start import install_start


def install_all_commands(dp):
    # Должен быть всегда первым для работы команды /cancel
    install_start(dp)

    install_admin(dp)
    install_invite(dp)
    install_my(dp)
    install_search(dp)
    install_settings(dp)
