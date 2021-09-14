from .admin import install_admin
from .help_invite import install_help_invite
from .my import install_my
from .search import install_search
from .settings import install_settings


def install_all_commands(dp):
    install_admin(dp)
    install_help_invite(dp)
    install_my(dp)
    install_search(dp)
    install_settings(dp)
