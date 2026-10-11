"""Config entries for dummy Home Assistant."""
from unittest.mock import MagicMock

class ConfigEntryState:
    LOADED = "loaded"
    SETUP_ERROR = "setup_error"
    NOT_LOADED = "not_loaded"

class ConfigEntry:
    def __init__(self, entry_id="test_entry", domain="multizone_thermostat", data=None, options=None, title="Test"):
        self.entry_id = entry_id
        self.domain = domain
        self.data = data or {}
        self.options = options or {}
        self.title = title
        self.state = ConfigEntryState.LOADED

class ConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.domain = domain

class OptionsFlow:
    pass

class FlowHandler:
    pass

FlowResult = dict

