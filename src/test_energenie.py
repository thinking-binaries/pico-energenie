# test_energenie.py  14/02/2023  D.J.Whale

import plat
import energenie
import json

def test_encode():
    """Test that we can encode switch messages"""
    ADDR =  0x02000373  # high byte is productid
    #NOTE: These are both signed and encrypted by make_switch_message
    ON  = energenie.OpenThingsLite.make_switch_message(ADDR, True)
    OFF = energenie.OpenThingsLite.make_switch_message(ADDR, False)

    print(energenie.hexstr(ON))
    print(energenie.hexstr(OFF))

def test_decode():
    """Test that we can decode to dict/json real captured messages"""
    MSG1 = b"\x0D\x04\x02\x4B\xA8\x98\x36\xEF\x9C\xC0\x3D\xE2\x25\x72"
    MSG2 = b"\x0D\x04\x02\xB9\x28\x0C\x8D\x78\x8F\x65\xBA\xED\x7B\x84"
    MSG3 = b"\x16\x04\x05\xC9\x8C\xFB\xD7\x5A\x44\x8E\xEE\x83\x21\xCC\xCB\xCF\x4A\xB8\x64\x66\x2C\x64\xAF"
    MSG4 = b"\x1C\x04\x02\x58\x0B\x55\x24\x23\xBC\xD2\xAC\x50\x8D\x26\x5B\xA2\xCF\x74\xB7\x73\x47\x4A\xA9\xF1\x97\xF1\xF0\x3F\x23"
    MSGS = (MSG1, MSG2, MSG3, MSG4)

    for msg in MSGS:
        buffer = bytearray(msg)
        ##nb = len(buffer)  #TODO
        ##raw_msg = memoryview(buffer)[0:nb]
        raw_msg = buffer
        print("encoded msg:%s" % energenie.hexstr(raw_msg))

        ot_msg = energenie.OpenThingsLite.decode(raw_msg)
        print(json.dumps(ot_msg, indent=2))

def test_send():
    """Test that when we send, the radio is correctly exercised"""
    # because we are on host, MOCKING will be true, and trace goes to stdout
    ADDR = 0x02000373

    print("Init")
    legacy = energenie.LegacySocket()
    mihome = energenie.MiHomeSocket(ADDR)

    print("\nLegacy ON")
    legacy.set(True, times=1)

    print("\nLegacy OFF")
    legacy.set(False, times=1)

    print("\nMiHome ON")
    mihome.on()

    print("\nMiHome OFF")
    mihome.off()

test_encode()
test_decode()
test_send()
