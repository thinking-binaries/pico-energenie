# energenie.py  09/05/2022  D.J.Whale - communicate with an energenie socket

PLATFORM = "pico"  # mock, pico
MOCKING = PLATFORM == "mock"
import utime

def get_radio_link():
    if PLATFORM == "mock":
        class MockSPI:
            def __init__(self):
                pass

            @staticmethod
            def hexbytes(buf: bytes) -> str:
                result = []
                for b in buf:
                    result.append("%02X" % b)
                return "".join(result)

            @staticmethod
            def transfer(buf: bytes) -> bytes:
                print("spi %s <> " % MockSPI.hexbytes(buf), end="")
                res = bytes(len(buf))
                print("%s" % MockSPI.hexbytes(res))
                return res

            def reset(self): pass

            def txing(self, flag): pass

            def rxing(self, flag): pass

        return MockSPI()

    # 0=CPOL0 CPHA0, 1=CPOL0 CPHA1 2=CPOL1 CPHA0, 3=CPOL1 CPHA1
    SPEED_HZ = 1000000

    if PLATFORM == "pico":
        from machine import Pin, SPI
        class PicoSPI:
            def __init__(self, cspin, link, txledpin=None, rxledpin=None, resetpin=None):
                self._link = link
                self._resetpin = resetpin
                self._txledpin = txledpin
                self._rxledpin = rxledpin
                self._cspin = cspin
                self._cspin(1)  # deselect, output

            def reset(self) -> None:
                if self._resetpin is not None:
                    self._resetpin(1)
                    utime.sleep_ms(150)
                    self._resetpin(0)
                    utime.sleep_us(100)

            def txing(self, flag:bool) -> None:
                if self._txledpin is not None:
                    self._txledpin(1 if flag else 0)
                else:
                    pass ##print("txled:%s" % flag)

            def rxing(self, flag:bool) -> None:
                if self._rxledpin is not None:
                    self._rxledpin(1 if flag else 0)
                else:
                    pass ##print("rxled:%s" % flag)

            def transfer(self, buf:bytes) -> bytes:
                self._cspin(0)  # select
                res = bytearray(len(buf))
                self._link.write_readinto(buf, res)
                self._cspin(1)  # deselect
                return res

        return PicoSPI(Pin(5, Pin.OUT),
                       SPI(0, baudrate=SPEED_HZ, polarity=0, phase=0, bits=8, sck=Pin(2), mosi=Pin(3), miso=Pin(4)),
                       resetpin=Pin(28, Pin.OUT))

    raise ValueError("Unknown platform:%s" % PLATFORM)




#----- RFM69 -------------------------------------------------------------------
class RFM69:
    VARIANT_HCW    = True  # aerial routing is different on high power device
    MTU            = 66
    _WRITE         = 0x80

    R_FIFO          = 0x00
    R_OPMODE        = 0x01
    V_OPMODE_STBY     = 0x04
    V_OPMODE_TX       = 0x0C
    V_OPMODE_RX       = 0x10
    R_DATAMODUL     = 0x02
    V_DATAMODUL_OOK   = 0x08
    R_BITRATEMSB    = 0x03
    R_BITRATELSB    = 0x04
    R_FDEVMSB       = 0x05
    R_FDEVLSB       = 0x06
    R_FRMSB         = 0x07
    V_FRMSB_433_92    = 0x6C
    R_FRMID         = 0x08
    V_FRMID_433_92    = 0x7A
    R_FRLSB         = 0x09
    V_FRLSB_433_92    = 0xE1
    R_AFCCTRL       = 0x0B
    R_VERSION       = 0x10
    V_VERSION         = 0x24


    R_PALEVEL       = 0x11
    R_OCP           = 0x13
    R_LNA           = 0x18

    R_RXBW          = 0x19
    V_RXBW_120        = 0x41
    R_DIOMAPPING1   = 0x25
    R_DIOMAPPING2   = 0x26
    R_IRQFLAGS1     = 0x27
    M_MODEREADY       = 0x80
    M_RXREADY         = 0x40
    M_TXREADY         = 0x20
    M_PLLLOCK         = 0x10
    M_RSSI            = 0x08
    M_TIMEOUT         = 0x04
    M_AUTOMODE        = 0x02
    M_SYNCADDRMATCH   = 0x01
    R_IRQFLAGS2     = 0x28
    FIFOFULL          = 0x80
    M_FIFONOTEMPTY    = 0x40
    M_FIFOLEVEL       = 0x20
    M_FIFOOVERRUN     = 0x10
    M_PACKETSENT      = 0x08
    M_PAYLOADREADY    = 0x04
    M_CRCOK           = 0x02
    R_RSSITHRESH    = 0x29
    R_PREAMBLEMSB   = 0x2C
    R_PREAMBLELSB   = 0x2D
    R_SYNCCONFIG    = 0x2E
    V_SYNCCONFIG0     = 0x00
    R_PACKETCONFIG1 = 0x37
    R_PAYLOADLEN    = 0x38
    R_FIFOTHRESH    = 0x3C

    def __init__(self, link=None):
        self._spi = link
        self._mode = self.V_OPMODE_STBY

    def readreg(self, addr: int) -> int:
        return self._spi.transfer(bytearray((addr, 0)))[1]

    def writereg(self, addr: int, value: int) -> None:
        ##print("writereg:%02X=%02X" % (addr, value))
        self._spi.transfer(bytearray((addr | self._WRITE, value)))

    ##def checkreg(self, addr: int, mask: int, value: int) -> bool:
    ##    v = self.readreg(addr)
    ##    return (v & mask) == value

    def waitreg(self, addr: int, mask: int, value: int):
        ##print("waitreg: %02X & %02X == %02X?" % (addr, mask, value))
        while True:
            v = self.readreg(addr)
            ##print("  got:%02X" % v, end=" ")
            if (v & mask) == value:
                ##print("YES")
                return
            else:
                ##print("NO")
                ##utime.sleep_ms(100)
                pass

    def writefifo(self, buf: bytes) -> None:
        #NOTE: Pico MicroPython has no bytearray.insert()
        buf2 = bytearray(len(buf)+1)
        buf2[0] = self.R_FIFO | self._WRITE
        for i in range(len(buf)):
            buf2[i+1] = buf[i]
        ##print("fifo:%s" % str(buf2))
        self._spi.transfer(buf2)

    def clearfifo(self) -> None:
        while (self.readreg(self.R_IRQFLAGS2) & self.M_FIFONOTEMPTY) == self.M_FIFONOTEMPTY:
            self.readreg(self.R_FIFO)

    def reset(self) -> None:
        self._spi.txing(False)
        self._spi.rxing(False)
        self._spi.reset()

    def setmode(self, mode: int) -> None:
        self._spi.txing(False)
        self._spi.rxing(False)

        self.writereg(self.R_OPMODE, mode)

        if mode == self.V_OPMODE_TX:
            self.wait_tx_ready()
            self._spi.txing(True)

        elif mode == self.V_OPMODE_RX:
            self.wait_ready()
            self._spi.rxing(True)
        else: # e.g. STBY
            self.wait_ready()

        self._mode = mode

    def getmode(self):
        return self._mode

    def wait_ready(self) -> None:
        if not MOCKING:
            self.waitreg(self.R_IRQFLAGS1, self.M_MODEREADY, self.M_MODEREADY)

    def wait_tx_ready(self) -> None:
        if not MOCKING:
            FLAGS = self.M_MODEREADY | self.M_TXREADY
            self.waitreg(self.R_IRQFLAGS1, FLAGS, FLAGS)

    def transmit(self, payload: bytes, times: int) -> None:
        # Note, when PA starts up, radio inserts a 01 at start before any user data
        # we might need to pad away from this by sending a sync of many zero bits
        # to prevent it being misinterpreted as a preamble, and prevent it causing
        # the first bit of the preamble being twice the length it should be in the
        # first packet.

        # CHECK
        pllen = len(payload)
        assert times != 0 and 1 <= pllen <= 32

        # CONFIGURE
        # Start transmitting when a full payload is loaded. So for '15':
        # level triggers when it 'strictly exceeds' level (i.e. 16 bytes starts tx,
        # and <=15 bytes triggers fifolevel irqflag to be cleared)
        # We already know from earlier that payloadlen<=32 (which fits into half a FIFO)
        self.writereg(self.R_FIFOTHRESH, pllen - 1)

        # TRANSMIT: Transmit a number of payloads back to back */

        for i in range(times):
            self.writefifo(payload)
            # Tx will auto start when fifolevel is exceeded by loading the payload
            # so the level register must be correct for the size of the payload
            # otherwise transmit will never start.
            # wait for FIFO to not exceed threshold level
            self.waitreg(self.R_IRQFLAGS2, self.M_FIFOLEVEL, 0)

        # WAIT: wait for FIFO empty, to indicate transmission completed
        self.waitreg(self.R_IRQFLAGS2, self.M_FIFONOTEMPTY, 0)

        # CONFIRM: Was the transmit ok?
        # Check final flags in case of overruns etc
        ##uint8_t irqflags1 = HRF_readreg(HRF_ADDR_IRQFLAGS1)
        ##uint8_t irqflags2 = HRF_readreg(HRF_ADDR_IRQFLAGS2)
        ##TRACE_OUTS("irqflags1,2=")
        ##TRACE_OUTN(irqflags1)
        ##TRACE_OUTC(',')
        ##TRACE_OUTN(irqflags2)
        ##TRACE_NL()
        ##
        ##if (((irqflags2 & HRF_MASK_FIFONOTEMPTY) != 0) || ((irqflags2 & HRF_MASK_FIFOOVERRUN) != 0))
        ##{
        ##    TRACE_FAIL("FIFO not empty or overrun at end of burst")
        ##}

#----- RADIO -------------------------------------------------------------------
class Radio:
    class RadioError(Exception): pass

    R = RFM69
    OOK_ENERGENIE_CFG = (
        # RFM69HCW (high power)

        (R.R_PALEVEL,       0x7F),  # RFM69HCW high power PA_BOOST PA1+PA2
        (R.R_OCP,           0x00),  # RFM69HCW over current protect off
        #RFM69 (low power)
        ##{R.R_PALEVEL,      0x9F},  # RMF69 (Energenie RT board) 13dBm, PA0=ON

        #OOK specific (receive?)
        (R.R_AFCCTRL,       0x20),  # Improved AFC
        (R.R_LNA,           0x00),  # LNA 50ohm, set by AGC loop
        (R.R_RSSITHRESH,    0xF0),  # 120*2
        (R.R_DIOMAPPING1,   0x04),  # DIO2=DATA in TX/RX

        (R.R_DATAMODUL,     R.V_DATAMODUL_OOK),  # on-off keyed
        (R.R_FDEVMSB,       0),  # frequency deviation 0kHz
        (R.R_FDEVLSB,       0),
        (R.R_FRMSB,         R.V_FRMSB_433_92),  # carrier freq 433.92MHz
        (R.R_FRMID,         R.V_FRMID_433_92),
        (R.R_FRLSB,         R.V_FRLSB_433_92),
        (R.R_RXBW,          R.V_RXBW_120),  # channel filter bandwidth 120kHz
        (R.R_BITRATEMSB,    0x1A),  # bitrate 4800bps (4b syms means 1200bps eff)
        (R.R_BITRATELSB,    0x00),
        (R.R_PREAMBLEMSB,   0),
        (R.R_PREAMBLELSB,   0),  # no preamble (done in payload)
        (R.R_SYNCCONFIG,    R.V_SYNCCONFIG0),  # sync word size (disabled)
        (R.R_PACKETCONFIG1, 0x80),  # Tx variable length, no manchester coding
        (R.R_PAYLOADLEN,    0),  # No payload length
    )

    def __init__(self, link=None):
        if link is None:
            link = get_radio_link()
        self._rfm = RFM69(link)
        self._configured = False
        self._is_on = False
        self._mode = self._rfm.V_OPMODE_STBY

    def get_version(self) -> int:
        if MOCKING: return RFM69.V_VERSION
        return self._rfm.readreg(RFM69.R_VERSION)

    def loadtable(self, table:tuple) -> None:
        for entry in table:
            reg, value = entry
            self._rfm.writereg(reg, value)

    def configure(self):
        rv = self.get_version()
        if rv != RFM69.V_VERSION:
            raise self.RadioError("Unexpected radio version, want:%d got:%d" % (RFM69.V_VERSION, rv))
        self.loadtable(self.OOK_ENERGENIE_CFG)
        self._configured = True

    def is_configured(self) -> bool:
        return self._configured

    def is_on(self) -> bool:
        return self._is_on

    def on(self):
        if not self.is_configured():
            self._rfm.reset()
            self.configure()
        self._rfm.setmode(self._rfm.V_OPMODE_STBY)
        self._is_on = True

    def send(self,payload:bytes, times:int=1) -> None:
        entry_mode = self._rfm.getmode()
        if entry_mode != self._rfm.V_OPMODE_TX:
            self._rfm.setmode(self._rfm.V_OPMODE_TX)

        self._rfm.transmit(payload, times)

        if self._rfm.getmode() != entry_mode:
            self._rfm.setmode(entry_mode)

    def off(self):
        self._rfm.setmode(self._rfm.V_OPMODE_STBY)
        self._is_on = False

class Socket:
    """A connector to a remote legacy energenie socket, in OOK mode"""
    ALL = 0                # channel index for 'all switches'
    DEFAULT_ADDR = 0xA0170 # @whaleygeek's hand controller

    @staticmethod
    def switch_to_k(channel: int, state: bool) -> int:
        """Encode a channel and a state into a LSB-first k-value for HS1527"""
        assert channel in (0, 1, 2, 3, 4)  # 0 = ALL
        state = 1 if state else 0  #  to int
        return (0xC, 0xE, 0x6, 0xA, 0x2)[channel] + state

    @staticmethod
    def encode_bits(buf: bytearray, value: int, offset: int, bits: int) -> None:
        """Encode as per: http://www.sc-tech.cn/en/1527en.htm"""
        LOW = 0x08  # ^___  short+long
        HIGH = 0x0E  # ^^^_  long+short

        mask = 1 << (bits - 1)

        for i in range(bits):
            if value & mask:
                symbol = HIGH
            else:
                symbol = LOW

            if (i % 2) == 0:
                # most significant nibble written first
                buf[offset] = symbol << 4
            else:
                # least significant nibble written second
                buf[offset] |= symbol
                offset += 1
            mask >>= 1

    @staticmethod
    def encode_msg(address:int=DEFAULT_ADDR, k:int=0x0F) -> bytes:
        """Pack/encode a 32 bit preamble, 20 bit address, 4 bits of k, into 16 bytes"""
        ##print("encode addr:%08X k:%04X" % (address, k))
        buf = bytearray(16)
        buf[0:4] = b'\x80\x00\x00\x00'  # [0..3]   preamble, 32 bits
        Socket.encode_bits(buf, address, 4, 20)  # [4..13]  address, 2 bits stored per byte
        Socket.encode_bits(buf, k, 14, 4)  # [14..15] k, 2 bits stored per byte
        return buf

    def __init__(self, address:int=DEFAULT_ADDR, channel:int=1):
        assert channel in [1,2,3,4]
        self._address = address
        self._channel = channel
        if not radio.is_on(): radio.on()

    def set(self, state:bool) -> None:
        k = self.switch_to_k(self._channel, state)
        payload = self.encode_msg(self._address, k)
        radio.send(payload, times=80)
        # short silence at end to stop switch sticking
        utime.sleep_ms(50)

    def on(self) -> None:
        self.set(True)

    def off(self) -> None:
        self.set(False)

radio = Radio()

def test(s:Socket) -> None:
    try:
        while True:
            print("ON")
            s.on()
            print("OFF")
            s.off()
    except KeyboardInterrupt:
        print("STOPPED")


