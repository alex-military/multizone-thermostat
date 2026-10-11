"""Device registry helper for dummy Home Assistant."""
from unittest.mock import MagicMock

class DeviceEntry:
    def __init__(self, id="mock_device_id", identifiers=None, name="Mock Device", manufacturer="Mock", model="Mock"):
        self.id = id
        self.identifiers = identifiers or set()
        self.name = name
        self.manufacturer = manufacturer
        self.model = model

class DeviceRegistry:
    def __init__(self):
        self.devices = {}

    def async_get_or_create(self, config_entry_id=None, identifiers=None, name=None, manufacturer=None, model=None, **kwargs):
        dev_id = f"dev_{config_entry_id or 'default'}"
        if dev_id not in self.devices:
            self.devices[dev_id] = DeviceEntry(
                id=dev_id,
                identifiers=identifiers,
                name=name,
                manufacturer=manufacturer,
                model=model,
            )
        return self.devices[dev_id]

    def async_get(self, device_id):
        return self.devices.get(device_id)

_REGISTRY = DeviceRegistry()

def async_get(hass):
    return _REGISTRY
