# onoff.py    26/05/2022  D.J.Whale - turn an Energenie socket on and off

##from user_pico import user
from user_console import user
import energenie

light = energenie.LegacySocket()

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
