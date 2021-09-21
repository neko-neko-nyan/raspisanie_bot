from .admin import install_admin
from .invite import install_invite
from .my import install_my
from .report import install_report
from .search import install_search
from .settings import install_settings
from .start import install_start, install_cancel


def install_all_commands(dp):
    all_commands = []

    install_cancel(dp)
    install_my(dp, all_commands)
    install_search(dp, all_commands)
    install_report(dp, all_commands)
    install_invite(dp, all_commands)
    install_settings(dp, all_commands)
    install_start(dp, all_commands)
    install_admin(dp)

    return all_commands
