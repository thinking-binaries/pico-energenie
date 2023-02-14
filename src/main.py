# main.py  11/02/2023  D.J.Whale

import plat
import energenie

DELAY_MS = 1000
legacy = energenie.LegacySocket()
mihome = energenie.MiHomeSocket(0x02000373)  # productID in high byte

def test_switching():
    print("test_switching")
    while True:
        print("LEGACY OFF")
        legacy.off()
        plat.sleep_ms(DELAY_MS)

        print("MIHOME OFF")
        mihome.off()
        plat.sleep_ms(DELAY_MS)

        print("LEGACY ON")
        legacy.on()
        plat.sleep_ms(DELAY_MS)

        print("MIHOME ON")
        mihome.on()
        plat.sleep_ms(DELAY_MS)

def test_receive_raw():
    """Receive a raw payload and print it"""
    print("test_receive_raw")
    radio = energenie.radio
    buffer = bytearray(radio.MTU)

    radio.always_receive()
    while True:
        nb = radio.recvinto(buffer)
        if nb is not None and nb > 0:
            raw_msg = memoryview(buffer)[0:nb]
            print("raw msg:%s" % energenie.hexstr(raw_msg))

def test_receive_ot():
    """Receive a raw payload and print it"""
    print("test_receive_ot")
    radio = energenie.radio

    radio.always_receive()
    while True:
        decoded = radio.ot_recv()
        if decoded is not None:
            print(decoded)

test_switching()

#test_receive_raw()
#test_receive_ot()