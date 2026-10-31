from .cards_dialog import CardsMixin
from .files_dialog import FilesMixin
from .inspect_dialog import InspectMixin
from .settings_dialog import SettingsMixin
from .worlds_dialog import WorldsMixin


class DialogMixin(WorldsMixin, FilesMixin, CardsMixin, SettingsMixin, InspectMixin):
    pass
