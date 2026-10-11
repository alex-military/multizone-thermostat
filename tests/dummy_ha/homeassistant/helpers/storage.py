"""Storage helper for dummy Home Assistant."""
import asyncio

class Store:
    def __init__(self, hass, version, key, minor_version=1):
        self.hass = hass
        self.version = version
        self.key = key
        self.minor_version = minor_version
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data

    def async_delay_save(self, data_func, delay=0):
        self._data = data_func()
