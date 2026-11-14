from homeassistant.helpers.entity import Entity


class ButtonEntity(Entity):
    async def async_press(self) -> None:
        pass
