# onoff.py  09/05/2022  D.J.Whale - turn an Energenie socket on and off

import energenie
from user_pico import user

light = energenie.Socket()

user.waiting()

try:
    while True:
        if user.wants_on():
            light.on()
            user.is_on()

        elif user.wants_off():
            light.off()
            user.is_off()
except KeyboardInterrupt:
    pass
