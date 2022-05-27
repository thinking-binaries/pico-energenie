class ConsoleUser:
    ON, OFF = ("on", "off")

    def __init__(self):
        self._last_cmd = None

    def _get_cmd(self) -> str:
        while True:
            c = input("command[Y=on, N=off]? ")
            if c in ("Y", "y"): return self.ON
            if c in ("N", "n"): return self.OFF

    def _wanted_cmd(self, wanted_cmd:str) -> bool:
        if self._last_cmd is None:
            self._last_cmd = self._get_cmd()

        if self._last_cmd == wanted_cmd:
            self._last_cmd = None
            return True
        return False

    def waiting(self) -> None:
        print("waiting")

    def is_on(self) -> None:
        print("is ON")

    def is_off(self) -> None:
        print("is OFF")

    def wants_on(self) -> bool:
        return self._wanted_cmd(self.ON)

    def wants_off(self) -> bool:
        return self._wanted_cmd(self.OFF)

user = ConsoleUser()
