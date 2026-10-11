"""Dummy selector helpers for Home Assistant."""

class SelectSelectorMode:
    DROPDOWN = "dropdown"
    LIST = "list"

class SelectOptionDict(dict):
    def __init__(self, value, label):
        super().__init__(value=value, label=label)

class SelectSelectorConfig(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class SelectSelector:
    def __init__(self, config=None):
        self.config = config
    def __call__(self, val):
        return val

class EntitySelectorConfig(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class EntitySelector:
    def __init__(self, config=None):
        self.config = config
    def __call__(self, val):
        return val

class NumberSelectorMode:
    BOX = "box"
    SLIDER = "slider"

class NumberSelectorConfig(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class NumberSelector:
    def __init__(self, config=None):
        self.config = config
    def __call__(self, val):
        return val
