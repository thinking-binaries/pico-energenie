# plat.py  14/02/2023  D.J.Whale - platform detect and switch

try:
    # PICO
    from utime import sleep_ms, ticks_ms
    now_ms = ticks_ms
    MOCKING = False

except ImportError:
    #HOST
    from time import sleep, time
    sleep_ms = lambda d: sleep(d/1000)
    now_ms   = lambda :  time()*1000
    MOCKING = True
