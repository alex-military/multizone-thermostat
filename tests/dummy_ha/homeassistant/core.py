"""Core classes for dummy Home Assistant."""
from unittest.mock import MagicMock, AsyncMock

class CoreState:
    running = "RUNNING"
    not_running = "NOT_RUNNING"

class HomeAssistant:
    def __init__(self):
        self.state = CoreState.running
        self.bus = MagicMock()
        self.services = MagicMock()
        self.services.async_call = AsyncMock()
        self.states = MagicMock()
        self.data = {}
        self.loop = MagicMock()
        self.config = MagicMock()
        self.config.path = lambda *args: "/".join(args)
        self.http = MagicMock()
        self.http.async_register_static_paths = AsyncMock()
        self.async_add_executor_job = AsyncMock(return_value=False)

class Event:
    def __init__(self, event_type, data=None, time_fired=None):
        self.event_type = event_type
        self.data = data or {}
        self.time_fired = time_fired

class State:
    def __init__(self, entity_id, state, attributes=None, last_changed=None, last_updated=None, last_reported=None):
        self.entity_id = entity_id
        self.state = str(state)
        self.attributes = attributes or {}
        self.last_changed = last_changed
        self.last_updated = last_updated or last_changed
        self.last_reported = last_reported or self.last_updated
        if "." in entity_id:
            self.domain = entity_id.split(".")[0]
        else:
            self.domain = ""

class ServiceCall:
    def __init__(self, domain, service, data=None):
        self.domain = domain
        self.service = service
        self.data = data or {}

class Context:
    def __init__(self, user_id=None, parent_id=None, id=None):
        self.user_id = user_id
        self.parent_id = parent_id
        self.id = id or "test_context_id"

def callback(func):
    return func
