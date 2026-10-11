"""Event helper for dummy Home Assistant."""

def async_track_state_change_event(hass, entity_ids, action):
    return lambda: None

def async_track_time_interval(hass, action, interval):
    return lambda: None

def async_call_later(hass, delay, action):
    return lambda: None
