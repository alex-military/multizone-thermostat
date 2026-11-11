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

    async def async_set_unique_id(self, unique_id=None):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass

    def async_show_form(self, step_id=None, data_schema=None, errors=None, description_placeholders=None):
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders or {},
        }

    def async_create_entry(self, title="", data=None):
        return {"type": "create_entry", "title": title, "data": data or {}}

    def async_abort(self, reason=""):
        return {"type": "abort", "reason": reason}

class OptionsFlow:
    def async_show_form(self, step_id=None, data_schema=None, errors=None, description_placeholders=None):
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders or {},
        }

    def async_create_entry(self, title="", data=None):
        return {"type": "create_entry", "title": title, "data": data or {}}

    def async_abort(self, reason=""):
        return {"type": "abort", "reason": reason}

class FlowHandler:
    pass

FlowResult = dict
