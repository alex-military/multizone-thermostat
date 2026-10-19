"""Entity registry helper for dummy Home Assistant."""
from unittest.mock import MagicMock

class RegistryEntry:
    def __init__(self, entity_id, unique_id=None, original_name=None, domain=None, disabled=False, device_id=None):
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.original_name = original_name
        self.domain = domain or (entity_id.split(".")[0] if "." in entity_id else "")
        self.disabled = disabled
        self.device_id = device_id

class EntityRegistry:
    def __init__(self):
        self.entities = {}

    def async_get(self, entity_id):
        return self.entities.get(entity_id)

_REGISTRY = EntityRegistry()

def async_get(hass):
    return _REGISTRY

def async_entries_for_device(registry, device_id):
    if hasattr(registry, "entities"):
        entries = registry.entities.values() if isinstance(registry.entities, dict) else registry.entities
        return [e for e in entries if getattr(e, "device_id", None) == device_id]
    return []
