"""Restore state helper for dummy Home Assistant."""
from .entity import Entity

class RestoreEntity(Entity):
    async def async_get_last_state(self):
        return None
