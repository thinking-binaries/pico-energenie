from machine import Pin

class PicoUser:
    def __init__(self):
        self._led_red = Pin(6, Pin.OUT)
        self._led_green = Pin(7, Pin.OUT)
        self._button_a = Pin(12, Pin.IN)
        self._button_b = Pin(13, Pin.IN)

    def waiting(self) -> None:
        self._led_red.on()
        self._led_green.on()

    def is_on(self) -> None:
        self._led_red.off()
        self._led_green.on()

    def is_off(self) -> None:
        self._led_red.on()
        self._led_green.off()

    def wants_off(self) -> bool:
        return self._button_a.value() == 0  # pressed

    def wants_on(self) -> bool:
        return self._button_b.value() == 0  # pressed

user = PicoUser()
