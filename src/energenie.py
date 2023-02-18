# energenie.py  09/05/2022  D.J.Whale - communicate with an energenie socket

import plat

def hexstr(data) -> str:
    """Print a run of bytes as a hexascii string"""
    if data is None: return ""
    res = []
    for b in data:
        res.append("%02X" % b)
    return " ".join(res)

#----- SPI LINK TO RADIO -------------------------------------------------------
def get_radio_link():
    """Get a mock or a real SPI connnection to the RFM69 radio"""
    if plat.MOCKING:
        class MockSPIRadio:
            def __init__(self):
                pass

            @staticmethod
            def cmd(data) -> str:
                rdwr = "WR" if (data & 0x80) != 0 else "RD"
                data &= 0x7F
                for k,v in RFM69.__dict__.items():
                    if type(v) == int and k.startswith("R_") and v==data:
                        return "%s %s" % (rdwr, k)
                return "??? %s %02X" % (rdwr, data)

            @staticmethod
            def transfer(tx=None, rx=None, select:bool=True) -> int:
                if tx:
                    print("spi (%s) %s" % (MockSPIRadio.cmd(tx[0]), hexstr(tx)))
                    return len(tx)
                return 0

            @staticmethod
            def byte(tx_byte:int) -> int:
                print("byte:%02X" % tx_byte)
                return 0

            # SCAFFOLDING
            @staticmethod
            def select(): pass
            @staticmethod
            def deselect(): pass
            @staticmethod
            def reset(): pass
            @staticmethod
            def power(flag=True) -> None: pass
            @staticmethod
            def is_int() -> bool: return False
            @staticmethod
            def txing(flag): pass
            @staticmethod
            def rxing(flag): pass

        return MockSPIRadio()

    if not plat.MOCKING:
        from machine import Pin, SPI
        class PicoSPIRadio:
            def __init__(self, cspin, link, txledpin=None, rxledpin=None, resetpin=None,
                         enpin=None, intpin=None, cspol=0):
                self._link = link
                self._resetpin = resetpin
                self._txledpin = txledpin
                self._rxledpin = rxledpin
                self._cspin    = cspin
                self._enpin    = enpin
                self._intpin   = intpin
                if enpin is not None: enpin(1)  # prevent it floating around

                if cspol:  # active high
                    self.select   = lambda: self._cspin(1)
                    self.deselect = lambda: self._cspin(0)
                else:  # active low
                    self.select   = lambda: self._cspin(0)
                    self.deselect = lambda: self._cspin(1)
                self.deselect()  # correct idle state at start

            # keep the static inspector happy
            def select(self) -> None: pass
            def deselect(self) -> None: pass

            def power(self, flag=True) -> None:
                """Supply power to the radio regulator or not"""
                if self._enpin is not None:
                    self._enpin(flag)

            def is_int(self) -> bool:
                """Is the interrupt pin asserted?"""
                if self._intpin is not None:
                    return self._intpin()

            def reset(self) -> None:
                """Hard reset the radio"""
                if self._resetpin is not None:
                    self._resetpin(1)
                    plat.sleep_ms(150)
                    self._resetpin(0)
                    plat.sleep_ms(100) # allow a long holdoff until first reg write

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

            def transfer(self, tx=None, rx=None, select:bool=True) -> None:
                if select: self.select()

                if isinstance(tx, int):
                    # tx fixed value, with receive up to length rxbuf
                    assert rx is not None
                    self._link.readinto(rx, tx)

                elif tx is not None:
                    if rx is None:
                        # tx only of length txbuf
                        self._link.write(tx)
                    else:
                        # tx and rx lengths must be same, bufs same or diff
                        ##print("write %s read back" % hexstr(tx))
                        self._link.write_readinto(tx, rx)
                        ##print("got:%s" % hexstr(rx))

                else:
                    # rx only, will tx 0's
                    assert rx is not None
                    self._link.readinto(rx, 0x00)

                if select: self.deselect()

            def byte(self, tx_byte:int) -> int:
                """Transfer a single byte"""
                return self._link.read(1, tx_byte)[0]

        # SPI_MODES: 0=CPOL0 CPHA0, 1=CPOL0 CPHA1 2=CPOL1 CPHA0, 3=CPOL1 CPHA1
        SPEED_HZ  = 1000000
        SPI_N     = 0
        GP_G0     = 0   # DIO0 INT pin
        GP_CS     = 1
        GP_SCK    = 2
        GP_MOSI   = 3
        GP_MISO   = 4
        GP_RES    = 6   # must be low in normal operation (floats high)
        GP_EN     = 7   # must be high to enable regulator (floats high)
        GP_TX_LED = 26  # LED1
        GP_RX_LED = 27  # LED2
        return PicoSPIRadio(Pin(GP_CS, Pin.OUT),
                        SPI(SPI_N,
                            baudrate=SPEED_HZ,
                            polarity=0,
                            phase=0,
                            bits=8,
                            sck=Pin(GP_SCK),
                            mosi=Pin(GP_MOSI),
                            miso=Pin(GP_MISO)),
                        resetpin = Pin(GP_RES, Pin.OUT),
                        enpin    = Pin(GP_EN, Pin.OUT),
                        txledpin = Pin(GP_TX_LED, Pin.OUT),
                        rxledpin = Pin(GP_RX_LED, Pin.OUT),
                        intpin   = Pin(GP_G0, Pin.IN))


#----- RFM69 -------------------------------------------------------------------
class RFM69:
    """A generic RFM69 radio with no specific configuration"""
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
    V_DATAMODUL_FSK   = 0x00
    R_BITRATEMSB    = 0x03
    R_BITRATELSB    = 0x04
    R_FDEVMSB       = 0x05
    V_FDEVMSB30       = 0x01  # frequency deviation 5kHz 0x0052 -> 30kHz 0x01EC
    R_FDEVLSB       = 0x06
    V_FDEVLSB30       = 0xEC  # frequency deviation 5kHz 0x0052 -> 30kHz 0x01EC
    R_FRMSB         = 0x07
    V_FRMSB_433_92    = 0x6C
    V_FRMSB_434_3     = 0x6C  # carrier freq -> 434.3MHz 0x6C9333
    R_FRMID         = 0x08
    V_FRMID_433_92    = 0x7A
    V_FRMID_434_3     = 0x93  # carrier freq -> 434.3MHz 0x6C9333
    R_FRLSB         = 0x09
    V_FRLSB_433_92    = 0xE1
    V_FRLSB_434_3     = 0x33  # carrier freq -> 434.3MHz 0x6C9333
    R_OSC1          = 0x0A
    R_AFCCTRL       = 0x0B
    V_AFCCTRLS        = 0x00  # standard AFC routine
    V_AFCCTRLI        = 0x20  # improved AFC routine
    # RESERVED 0C
    R_LISTEN1       = 0x0D
    R_LISTEN2       = 0x0E
    R_LISTEN3       = 0x0F
    R_VERSION       = 0x10
    V_VERSION         = 0x24
    R_PALEVEL       = 0x11
    R_PARAMP        = 0x12
    R_OCP           = 0x13
    # RESERVED 14,15,16,17
    R_LNA           = 0x18
    V_LNA50           = 0x08  # LNA input impedance 50 ohms
    V_LNA50G          = 0x0E  # LNA input impedance 50 ohms, LNA gain -> 48db
    V_LNA200          = 0x88  # LNA input impedance 200 ohms
    R_RXBW          = 0x19
    V_RXBW_60         = 0x43  # channel filter bandwidth 10kHz -> 60kHz  page:26
    V_RXBW_120        = 0x41
    R_AFCBW         = 0x1A
    R_OOKPEAK       = 0x1B
    R_OOKAVG        = 0x1C
    R_OOKFIX        = 0x1D
    R_AFCFEI        = 0x1E
    R_AFCMSB        = 0x1F
    R_AFCLSB        = 0x20
    R_FE1MSB        = 0x21
    R_FEILSB        = 0x22
    R_RSSICONFIG    = 0x23
    R_RSSIVALUE     = 0x24
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
    M_FIFOFULL        = 0x80
    M_FIFONOTEMPTY    = 0x40
    M_FIFOLEVEL       = 0x20
    M_FIFOOVERRUN     = 0x10
    M_PACKETSENT      = 0x08
    M_PAYLOADREADY    = 0x04
    M_CRCOK           = 0x02
    R_RSSITHRESH    = 0x29
    V_RSSITHRESH220   = 0xDC  # RSSI threshold 0xE4 -> 0xDC (220)
    R_RXTIMEOUT1    = 0x2A
    R_RXTIMEOUT2    = 0x2B
    R_PREAMBLEMSB   = 0x2C
    R_PREAMBLELSB   = 0x2D
    V_PREAMBLELSB3    = 0x03  # preamble size LSB 3
    V_PREAMBLELSB5    = 0x05  # preamble size LSB 5
    R_SYNCCONFIG    = 0x2E
    V_SYNCCONFIG0     = 0x00
    V_SYNCCONFIG1     = 0x80  # 1 byte  of tx sync
    V_SYNCCONFIG2     = 0x88  # 2 bytes of tx sync
    V_SYNCCONFIG3     = 0x90  # 3 bytes of tx sync
    V_SYNCCONFIG4     = 0x98  # 4 bytes of tx sync
    R_SYNCVALUE1    = 0x2F
    R_SYNCVALUE2    = 0x30
    R_SYNCVALUE3    = 0x31
    R_SYNCVALUE4    = 0x32
    R_SYNCVALUE5    = 0x33
    R_SYNCVALUE6    = 0x34
    R_SYNCVALUE7    = 0x35
    R_SYNCVALUE8    = 0x36
    R_PACKETCONFIG1 = 0x37
    R_PAYLOADLEN    = 0x38
    R_NODEADRS      = 0x39
    R_BROADCASTADRS = 0x3A
    R_AUTOMODES     = 0x3B
    R_FIFOTHRESH    = 0x3C
    V_FIFOTHRESH1     = 0x81  # Condition to start packet transmission: at least one byte in FIFO
    V_FIFOTHRESH30    = 0x1E  # Condition to start packet transmission: wait for 30 bytes in FIFO
    R_PACKETCONFIG2 = 0x3D
    R_AESKEY1       = 0x3E
    # AESKEY2..AESKEY16 = 3F..4D
    R_TEMP1         = 0x4E
    R_TEMP2         = 0x4F
    # RESERVED 50..57
    R_TESTLNA       = 0x58
    # RESERVED 59
    R_TESTPA1       = 0x5A
    # RESERVED 5B
    R_TESTPA2       = 0x5C
    # RESERVED 5D..6E
    R_TESTDAGC     = 0x6F
    # RESERVED 70
    R_TESTAFC      = 0x71
    # RESERVED 72..7F

    RX_POLL = 0
    RX_INT  = 1

    def __init__(self, link=None):
        self._spi = link
        self._mode = self.V_OPMODE_STBY
        self._rxmode = self.RX_POLL
        self._regbuf = bytearray(2)  # reusable buffer for reg reads and writes

    def readreg(self, addr: int) -> int:
        self._regbuf[0] = addr
        self._regbuf[1] = 0
        self._spi.transfer(self._regbuf, self._regbuf)
        return self._regbuf[1]

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
                ##plat.sleep_ms(100)
                pass

    def writefifo(self, buf) -> None:
        """Send all bytes to the FIFO buffer"""
        #NOTE: irqflags comes back in the read buffer if we want it
        self._spi.select()
        self._spi.byte(self.R_FIFO | self._WRITE)
        self._spi.transfer(buf, select=False)
        self._spi.deselect()

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
        if not plat.MOCKING:
            self.waitreg(self.R_IRQFLAGS1, self.M_MODEREADY, self.M_MODEREADY)

    def wait_tx_ready(self) -> None:
        if not plat.MOCKING:
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
        assert times >= 1 and 1 <= pllen <= 32

        # CONFIGURE
        # Start transmitting when a full payload is loaded. So for '15':
        # level triggers when it 'strictly exceeds' level (i.e. 16 bytes starts tx,
        # and <=15 bytes triggers fifolevel irqflag to be cleared)
        # We already know from earlier that payloadlen<=32 (which fits into half a FIFO)
        self.writereg(self.R_FIFOTHRESH, pllen - 1)

        # TRANSMIT: Transmit a number of payloads back to back
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

    def recv_rdy(self) -> bool:
        """Is there something to be received?"""
        if self._rxmode == self.RX_INT:
            return self._spi.is_int()
        else:  # self.RX_POLL:
            irqflags2 = self.readreg(self.R_IRQFLAGS2)
            return (irqflags2 & self.M_PAYLOADREADY) == self.M_PAYLOADREADY

    def readfifo_cbp_into(self, rxbuf) -> int:
        """Receive a count byte preceeded block of data"""
        #NOTE: only call this if you know there is something in the FIFO
        # clear buffer first, for diags
        for i in range(len(rxbuf)):
            rxbuf[i] = 0

        self._spi.select()
        self._spi.byte(self.R_FIFO)  #  prime the burst receiver

        length = self._spi.byte(self.R_FIFO)  # read the length byte
        if length > len(rxbuf):
            self._spi.deselect()
            print("warning: rxbuf too small, want:%d got:%d" % (length+1, len(rxbuf)))
            self.clearfifo()
            return 0  # NOTDONE

        #SLOW RECEIVE
        rxbuf[0] = length
        for i in range(length):
            b = self._spi.byte(self.R_FIFO)
            rxbuf[i+1] = b
        self._spi.deselect()

        return length+1  # DONE, actual nbytes in buffer including cbp

        #FAST RECEIVE (not working
        # rxbuf[0] = length  # user sees the CBP also
        # print("delay for packet")
        # plat.sleep_ms(250)  # wait for rest of payload to fill buffer
        # self._spi.transfer(self.R_FIFO, memoryview(rxbuf[1:length]), select=False)
        # self._spi.deselect()
        # print("packet apparently received")
        # return length+1  # DONE, actual length

#----- RADIO -------------------------------------------------------------------
class EnergenieRadio:
    """A specific configuration of the RFM69 radio, for Energenie devices"""
    class RadioError(Exception): pass

    OOK = 0
    FSK = 1
    FOREVER = 0xFFFFFFFF
    MTU = 66

    # see: https://www.ti.com/lit/an/swra048/swra048.pdf table 9
    # see datasheet table 10
    #R_PALEVEL            012 xxxxx
    # normal power radio, tx on RFIO pin (-18dBm..+13dBm)
    V_RFIO_N18_DBM   = 0b_100_00000    # PA0: -18dBm+0 = -18dBm
    V_RFIO_10_DBM    = 0b_100_11100    # PA0: -18dBm+28 = 10dBm (swra048 limit in UK)
    ##V_RFIO_MAX     = 0b_100_11111    # PA0: -18dBm+31 = 13dBm (DON'T USE IN UK)

    # high power (HCW) radio, tx on PA_BOOST pin  (PA1:-2dBm..13dBm, PA1+2:+2dBm..+17dBm, PA1+2+HIGHP:+5dBm..+20dBm)
    # datasheet: only the 16 upper values of PLEV are used with PA1 or PA2 combinations
    V_PABOOST_0_DBM  = 0b_010_1_0010    # PA1: -18dBm + PLEV(18) = 0dBm   # swra048 433.05..434.79 0dBm duty(any) chbw(any)
    V_PABOOST_10_DBM = 0b_010_1_1100    # PA1: -18dBm + PLEV(28) = 10dBm  # swra048 433.05..434.79 10dBm duty(<10%) or chbw(<25kHz)

    R = RFM69
    OOK_ENERGENIE_CFG = (
        # RFM69HCW (high power)
        (R.R_PALEVEL,       V_PABOOST_10_DBM),  # RFM69HCW PA_BOOST PA1 10%duty 25kHz bw max (ANT=PABOOST PIN)
        #RFM69 (low power)
        ##{R.R_PALEVEL,     V_RFIO_10_DBM},     # RMF69 (Energenie RT board) PA0 10%duty 25kHz bw max (ANT=RFIO PIN)

        #OOK specific
        (R.R_AFCCTRL,       0x20),              # Improved AFC
        (R.R_LNA,           0x00),              # LNA 50ohm, set by AGC loop
        (R.R_RSSITHRESH,    0xF0),              # 120*2
        (R.R_DIOMAPPING1,   0x04),              # DIO2=DATA in TX/RX
        (R.R_DATAMODUL,     R.V_DATAMODUL_OOK), # on-off keyed
        (R.R_FDEVMSB,       0),                 # frequency deviation 0kHz
        (R.R_FDEVLSB,       0),
        (R.R_FRMSB,         R.V_FRMSB_433_92),  # carrier freq 433.92MHz
        (R.R_FRMID,         R.V_FRMID_433_92),
        (R.R_FRLSB,         R.V_FRLSB_433_92),
        (R.R_RXBW,          R.V_RXBW_120),      # channel filter bandwidth 120kHz
        (R.R_BITRATEMSB,    0x1A),              # bitrate 4800bps (4b syms means 1200bps eff)
        (R.R_BITRATELSB,    0x00),
        (R.R_PREAMBLEMSB,   0),
        (R.R_PREAMBLELSB,   0),                 # no preamble (done in payload)
        (R.R_SYNCCONFIG,    R.V_SYNCCONFIG0),   # sync word size (disabled)
        (R.R_PACKETCONFIG1, 0x80),              # Tx variable length, no manchester coding
        (R.R_PAYLOADLEN,    0)                  # No payload length
    )

    FSK_ENERGENIE_CFG = {
        # RFM69HCW (high power)
        (R.R_PALEVEL,       V_PABOOST_10_DBM),  # RFM69HCW PA_BOOST PA1 10%duty 25kHz bw max (ANT=PABOOST PIN)
        #RFM69 (low power)
        ##{R.R_PALEVEL,     V_RFIO_10_DBM},     # RMF69 (Energenie RT board) PA0 10%duty 25kHz bw max (ANT=RFIO PIN)

        # FSK specific
        (R.R_DATAMODUL,     R.V_DATAMODUL_FSK), # modulation scheme FSK
        (R.R_AFCCTRL,       R.V_AFCCTRLS),      # standard AFC routine
        (R.R_LNA,           R.V_LNA50),         # 200ohms, gain by AGC loop -> 50ohms
        ##(R.R_RSSITHRESH,  0xF0),              # 120*2
        (R.R_FDEVMSB,       R.V_FDEVMSB30),     # frequency deviation 5kHz 0x0052 -> 30kHz 0x01EC
        (R.R_FDEVLSB,       R.V_FDEVLSB30),     # frequency deviation 5kHz 0x0052 -> 30kHz 0x01EC
        (R.R_FRMSB,         R.V_FRMSB_434_3),   # carrier freq -> 434.3MHz 0x6C9333
        (R.R_FRMID,         R.V_FRMID_434_3),   # carrier freq -> 434.3MHz 0x6C9333
        (R.R_FRLSB,         R.V_FRLSB_434_3),   # carrier freq -> 434.3MHz 0x6C9333
        (R.R_RXBW,          R.V_RXBW_60),       # channel filter bandwidth 10kHz -> 60kHz  page:26
        (R.R_BITRATEMSB,    0x1A),              # 4800b/s
        (R.R_BITRATELSB,    0x0B),              # 4800b/s
        (R.R_SYNCCONFIG,    R.V_SYNCCONFIG2),   # Size of the Sync word = 2 (SyncSize + 1)
        (R.R_SYNCVALUE1,    0x2D),              # 1st byte of Sync word
        (R.R_SYNCVALUE2,    0xD4),              # 2nd byte of Sync word
        (R.R_PACKETCONFIG1, 0xA0),              # Variable length, Manchester coding
        ##(R.R_PACKETCONFIG1,0xA2),             # Variable length, Manchester coding, Addr must match NodeAddress
        (R.R_PAYLOADLEN,    MTU),               # max Length in RX, not used in Tx
        (R.R_NODEADRS,      0x06)               # Node address used in address filtering (not used)
    }

    CFGS = (OOK_ENERGENIE_CFG, FSK_ENERGENIE_CFG)
    def __init__(self, link=None):
        if link is None:
            link = get_radio_link()
        self._rfm = RFM69(link)
        self._configured = False
        self._is_on = False
        self._mode = self._rfm.V_OPMODE_STBY
        self._cfg = None
        self._rxbuf = bytearray(self.MTU)

    def get_version(self) -> int:
        if plat.MOCKING: return RFM69.V_VERSION
        return self._rfm.readreg(RFM69.R_VERSION)

    def loadtable(self, table:tuple) -> None:
        for entry in table:
            reg, value = entry
            self._rfm.writereg(reg, value)

    def want_cfg(self, cfg):
        if self._cfg != cfg:
            self._configure(self.CFGS[cfg])
            self._cfg = cfg

    def _configure(self, cfg):
        rv = self.get_version()
        if rv != RFM69.V_VERSION:
            raise self.RadioError("Unexpected radio version, want:%d got:%d" % (RFM69.V_VERSION, rv))
        self.loadtable(cfg)
        self._configured = True

    def is_configured(self) -> bool:
        return self._configured

    def is_on(self) -> bool:
        return self._is_on

    def on(self):
        if not self.is_configured():
            #radio EN=true
            self._rfm.reset()
            self.want_cfg(self.OOK)
        self._rfm.setmode(self._rfm.V_OPMODE_STBY)
        self._is_on = True

    def send(self, payload:bytes, times:int=1) -> None:
        entry_mode = self._rfm.getmode()
        if entry_mode != self._rfm.V_OPMODE_TX:
            self._rfm.setmode(self._rfm.V_OPMODE_TX)

        self._rfm.transmit(payload, times)

        if self._rfm.getmode() != entry_mode:
            self._rfm.setmode(entry_mode)

    def always_receive(self) -> None:
        """Leave the radio permanently in receive"""
        # This reduces the chance of missing payloads
        self.on()
        self.want_cfg(radio.FSK)  # we only support FSK receive at present
        self._rfm.setmode(self._rfm.V_OPMODE_RX)

    def recvinto(self, buffer, wait_ms:int=0) -> int:
        """Try to receive a single payload in the current mode"""

        # if radio not in receive, put it into receive
        entry_mode = self._rfm.getmode()
        if entry_mode != self._rfm.V_OPMODE_RX:
            self._rfm.setmode(self._rfm.V_OPMODE_RX)

        # check if there is anything ready to receive
        if wait_ms is not None and wait_ms > 0:
            ready = False
            timeout_ms = plat.now_ms() + wait_ms
            while True:
                if self._rfm.recv_rdy():
                    ready = True
                    break
                if plat.now_ms() > timeout_ms: break
        else:
            ready = self._rfm.recv_rdy()

        total_length = 0
        if ready:
            # Something is ready to be received
            total_length = self._rfm.readfifo_cbp_into(buffer)
            # This is a raw buffer, not decrypted, not crc validated

        if self._rfm.getmode() != entry_mode:
            self._rfm.setmode(entry_mode)

        return total_length  # number of bytes in buffer, including len byte

    def ot_recv(self, wait_ms:int=0) -> dict or None:
        """Receive, decrypt, and return as a decoded dict"""
        nb = self.recvinto(self._rxbuf, wait_ms)
        if nb is None or nb == 0: return None  # no data

        raw_msg = memoryview(self._rxbuf)[0:nb]
        ot_msg = OpenThingsLite.decode(raw_msg)
        return ot_msg  # dict

    def off(self):
        self._rfm.setmode(self._rfm.V_OPMODE_STBY)
        #radio EN=False
        self._is_on = False

#----- SOCKET (Generic) --------------------------------------------------------
class Socket:
    def __init__(self, address:int, channel:int=0):
        self._address = address
        self._channel = channel
        if not radio.is_on(): radio.on()

    def set(self, state:bool) -> None:
        pass # override in subclass

    def on(self) -> None:
        self.set(True)

    def off(self) -> None:
        self.set(False)

#----- SOCKET (Energenie-OOK) --------------------------------------------------
class LegacySocket(Socket):
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
        LOW  = 0x08  # ^___  short+long
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
        LegacySocket.encode_bits(buf, address, 4, 20)  # [4..13]  address, 2 bits stored per byte
        LegacySocket.encode_bits(buf, k, 14, 4)  # [14..15] k, 2 bits stored per byte
        return buf

    def __init__(self, address:int=DEFAULT_ADDR, channel:int=1):
        Socket.__init__(self, address, channel)
        assert channel in [1,2,3,4]

    def set(self, state:bool, times:int=8) -> None:
        k = self.switch_to_k(self._channel, state)
        payload = self.encode_msg(self._address, k)
        radio.want_cfg(radio.OOK)
        radio.send(payload, times=times)
        # short silence at end to stop switch sticking
        plat.sleep_ms(50)

#----- CRC ---------------------------------------------------------------------
class CRC:
    @staticmethod
    def calc(buffer) -> int:
        length = len(buffer)
        crcsum = 0
        for idx in range(length):
            crcsum ^= buffer[idx] << 8
            for b in range(8):
                if (crcsum & 0x8000) != 0:
                    # high bit is set
                    crcsum = (crcsum<<1) ^ 0x1021
                else:
                    # high bit is clear
                    crcsum <<= 1
            crcsum &= 0xFFFF  # keep as U16
        return crcsum

    @staticmethod
    def sign(buffer) -> None:
        """Set last two bytes of buffer to CRC of rest of buffer"""
        crc = CRC.calc(memoryview(buffer)[:-2])
        buffer[-2] = (crc>>8) & 0xFF  # MSB
        buffer[-1] = crc      & 0xFF  # LSB

    @staticmethod
    def verify(buffer) -> bool:
        """Check that crc in last two bytes match the crcsum of buffer"""
        crc = CRC.calc(memoryview(buffer)[:-2])
        if buffer[-2] != ((crc>>8) & 0xFF): return False  # MSB
        if buffer[-1] != (crc      & 0xFF): return False  # LSB
        return True

#----- CRYPT -------------------------------------------------------------------
class Crypt:
    def __init__(self, pid:int, pip:int):
        self._ran = ((pid<<8) ^ pip) & 0xFFFF  # keep as U16

    def byte(self, data:int) -> int:
        """Crypt a single byte of data, and update crypto engine state"""
        ran = self._ran  # perf
        for i in range(5):
            if (ran & 0x01) != 0:
                # bit 0 is set
                ran = (ran>>1) ^ 0xF5F5
            else:
                # bit 0 is clear
                ran >>= 1

        self._ran = ran  # stays as U16 due to right shifts
        return (ran ^ data ^ 0x5a) & 0xFF  # as a U8

    def block(self, block):
        """Encrypt a range of bytes in place, by modifying the payload bytes"""
        for idx in range(len(block)):
            block[idx] = self.byte(block[idx])
        return block

#----- OPEN THINGS LITE --------------------------------------------------------
byte0 = lambda v: v       & 0xFF
byte1 = lambda v: (v>>8)  & 0xFF
byte2 = lambda v: (v>>16) & 0xFF
byte3 = lambda v: (v>>24) & 0xFF

class Parameter:
    # PARAMETERS (P_) and UNITS (U_)
    P_ALARM             = 0x21
    P_DEBUG_OUTPUT      = 0x2D
    P_IDENTIFY          = 0x3F
    P_SOURCE_SELECTOR   = 0x40  # command only
    P_WATER_DETECTOR    = 0x41
    P_GLASS_BREAKAGE    = 0x42
    P_CLOSURES          = 0x43
    P_DOOR_BELL         = 0x44
    P_ENERGY            = 0x45
    U_ENERGY            = "kWh"
    P_FALL_SENSOR       = 0x46
    P_GAS_VOLUME        = 0x47
    U_GAS_VOLUME        = "m3"
    P_AIR_PRESSURE      = 0x48
    U_AIR_PRESSURE      = "mbar"
    P_ILLUMINANCE       = 0x49
    U_ILLUMINANCE       = "Lux"
    P_LEVEL             = 0x4C
    P_RAINFALL          = 0x4D
    U_RAINFALL          = "mm"
    P_APPARENT_POWER    = 0x50
    U_APPARENT_POWER    = "VA"
    P_POWER_FACTOR      = 0x51
    P_REPORT_PERIOD     = 0x52
    U_REPORT_PERIOD     = "s"
    P_SMOKE_DETECTOR    = 0x53
    P_TIME_AND_DATE     = 0x54
    U_TIME_AND_DATE     = "s"
    P_VIBRATION         = 0x56
    P_WATER_VOLUME      = 0x57
    U_WATER_VOLUME      = "l"
    P_WIND_SPEED        = 0x58
    U_WIND_SPEED        = "m/s"
    P_GAS_PRESSURE      = 0x61
    U_GAS_PRESSURE      = "Pa"
    P_BATTERY_LEVEL     = 0x62
    U_BATTERY_LEVEL     = "V"
    P_CO_DETECTOR       = 0x63
    P_DOOR_SENSOR       = 0x64
    P_EMERGENCY         = 0x65
    P_FREQUENCY         = 0x66
    U_FREQUENCY         = "Hz"
    P_GAS_FLOW_RATE     = 0x67
    U_GAS_FLOW_RATE     = "m3/hr"
    P_RELATIVE_HUMIDITY = 0x68
    U_RELATIVE_HUMIDITY = "%"
    P_CURRENT           = 0x69
    U_CURRENT           = "A"
    P_JOIN              = 0x6A
    P_LIGHT_LEVEL       = 0x6C
    P_MOTION_DETECTOR   = 0x6D
    P_OCCUPANCY         = 0x6F
    P_REAL_POWER        = 0x70
    U_REAL_POWER        = "W"
    P_REACTIVE_POWER    = 0x71
    U_REACTIVE_POWER    = "VAR"
    P_ROTATION_SPEED    = 0x72
    U_ROTATION_SPEED    = "RPM"
    P_SWITCH_STATE      = 0x73
    P_TEMPERATURE       = 0x74
    U_TEMPERATURE       = "C"
    P_VOLTAGE           = 0x76
    U_VOLTAGE           = "V"
    P_WATER_FLOW_RATE   = 0x77
    U_WATER_FLOW_RATE   = "l/hr"
    P_WATER_PRESSURE    = 0x78
    U_WATER_PRESSURE    = "Pa"
    P_TEST              = 0xAA

    # TYPES
    T_UINT              = 0x00
    T_UINT_BP4          = 0x10
    T_UINT_BP8          = 0x20
    T_UINT_BP12         = 0x30
    T_UINT_BP16         = 0x40
    T_UINT_BP20         = 0x50
    T_UINT_BP24         = 0x60
    T_CHAR              = 0x70
    T_SINT              = 0x80
    T_SINT_BP8          = 0x90
    T_SINT_BP16         = 0xA0
    T_SINT_BP24         = 0xB0
    # C0,D0,E0 RESERVED
    T_FLOAT             = 0xF0

    # typename to tid   T_<NAME>
    # tid to typename   TYPEID_FOR[id]

    # name to pid:      P_<NAME>
    # pid to name:      NAME_FOR[id]
    # name to unitstr:  U_<NAME>
    # pid to unitstr:   UNIT_FOR[id]

    # build reverse lookup tables, ID(int)->name(str) ID(int)->unit(str)
    NAME_FOR     = {}  # pid(int) -> name(str)
    UNIT_FOR     = {}  # pid(int) -> unit(str)
    TYPENAME_FOR = {}  # tid(int) -> typename(str)

    @staticmethod
    def build() -> None:
        for name,v in Parameter.__dict__.items():
            if name.startswith("P_"):
                name = name[2:]
                Parameter.NAME_FOR[v] = name
                try:
                    unitstr = Parameter.__dict__["U_%s" % name]
                    Parameter.UNIT_FOR[v] = unitstr
                except KeyError: pass

            elif name.startswith("T_"):
                name = name[2:]
                Parameter.TYPENAME_FOR[v] = name

    @staticmethod
    def paramname_for(pid:int) -> str:
        try:
            return Parameter.NAME_FOR[pid]
        except KeyError:
            return "P_0x%02X" % pid

    @staticmethod
    def unitname_for(pid:int) -> str:
        try:
            return Parameter.UNIT_FOR[pid]
        except KeyError:
            return ""  # no unit

    @staticmethod
    def typename_for(tid:int) -> str:
        try:
            return Parameter.TYPENAME_FOR[tid]
        except KeyError:
            return "T_0x%02X" % tid

Parameter.build()

class Value:
    @staticmethod
    def typebits(typeid:int) -> int:
        """work out number of bits to represent this type"""
        if typeid == Parameter.T_UINT_BP4:  return 4
        if typeid == Parameter.T_UINT_BP8:  return 8
        if typeid == Parameter.T_UINT_BP12: return 12
        if typeid == Parameter.T_UINT_BP16: return 16
        if typeid == Parameter.T_UINT_BP20: return 20
        if typeid == Parameter.T_UINT_BP24: return 24
        if typeid == Parameter.T_SINT_BP8:  return 8
        if typeid == Parameter.T_SINT_BP16: return 16
        if typeid == Parameter.T_SINT_BP24: return 24
        raise ValueError("Can't calculate number of bits for type:" + str(typeid))

    @staticmethod
    def highestClearBit(value:int, maxbits:int=15*8) -> int or None:
        """Find the highest clear bit scanning MSB to LSB"""
        mask = 1<<(maxbits-1)
        bitno = maxbits-1
        while mask != 0:
            ##trace("compare %s with %s" %(hex(value), hex(mask)))
            if (value & mask) == 0:
                ##trace("zero at bit %d" % bitno)
                return bitno
            mask >>= 1
            bitno-=1
        ##trace("not found")
        return None # NOT FOUND

    @staticmethod
    def valuebits(value:int) -> int:
        """Work out number of bits required to represent this value"""
        if value >= 0 or type(value) != int:
            raise RuntimeError("valuebits only on -ve int at moment")

        if value == -1: # always 0xFF, so always needs exactly 2 bits to represent (sign and value)
            return 2 # bits required
        ##trace("valuebits of:%d" % value)
        # Turn into a 2's complement representation
        MAXBYTES = 15
        MAXBITS  = 1<<(MAXBYTES*8)
        #TODO: check for truncation?
        value &= MAXBITS-1
        ##trace("hex:%s" % hex(value))
        highz = Value.highestClearBit(value, MAXBYTES*8)
        ##trace("highz at bit:%d" % highz)
        # allow for a sign bit, and bit numbering from zero
        neededbits = highz+2

        ##trace("needed bits:%d" % neededbits)
        return neededbits

    @staticmethod
    def encode(value:int, typeid:int, length:int or None=None): #list?
        ##trace("encoding:" + str(value))
        if typeid == Parameter.T_CHAR:
            if type(value) != str:
                value = str(value)
            if length is not None and len(value) > length:
                raise ValueError("String too long")
            result = []
            for ch in value:
                result.append(ord(ch))
            if len is not None and len(result) < length:
                for a in range(length-len(result)):
                    result.append(0) # zero pad
            return result

        if typeid == Parameter.T_FLOAT:
            raise ValueError("IEEE-FLOAT not yet supported")

        if typeid <= Parameter.T_UINT_BP24:
            # unsigned integer
            if value < 0:
                raise ValueError("Cannot encode negative number as an unsigned int")

            if typeid != Parameter.T_UINT:
                # pre-adjust for BP
                if type(value) == float:
                    value *= (2**Value.typebits(typeid)) # shifts float into int range using BP
                    value = round(value, 0) # take off any unstorable bits
            value = int(value) # It must be an integer for the next part of encoding

            # code it in the minimum length bytes required
            # Note that this codes zero in 0 bytes (might not be correct?)
            v = value
            result = []
            while v != 0:
                result.insert(0, v&0xFF) # MSB first, so reverse bytes as inserting
                v >>= 8

            # check length mismatch and zero left pad if required
            if length is not None:
                if len(result) < length:
                    result = [0 for _ in range(length-len(result))] + result
                elif len(result) > length:
                    raise ValueError("Field width overflow, not enough bits")
            return result

        if Parameter.T_SINT <= typeid <= Parameter.T_SINT_BP24:
            # signed int
            if typeid != Parameter.T_SINT:
                # pre-adjust for BP
                if type(value) == float:
                    value *= (2**Value.typebits(typeid)) # shifts float into int range using BP
                    value = round(value, 0) # take off any unstorable bits
            value = int(value) # It must be an integer for the next part of encoding

            #If negative, take complement by masking with the length mask
            # This turns -1 (8bit) into 0xFF, which is correct
            # -1 (16bit) into 0xFFFF, which is correct
            # -128(8bit) into 0x80, which is correct
            #i.e. top bit will always be set as will all following bits up to number

            if value < 0: # -ve
                if typeid == Parameter.T_SINT:
                    bits = Value.valuebits(value)
                else:
                    bits = Value.typebits(typeid)
                ##trace("need bits:" + str(bits))
                # NORMALISE BITS TO BYTES
                #round up to nearest number of 8 bits
                # if already 8, leave 1,2,3,4,5,6,7,8 = 8   0,1,2,3,4,5,6,7 (((b-1)/8)+1)*8
                # 9,10,11,12,13,14,15,16=16
                bits = (((bits-1)/8)+1)*8 # snap to nearest byte boundary
                ##trace("snap bits to 8:" + str(bits))

                value &= ((2**int(bits))-1)
                neg = True
            else:
                neg = False

            #encode in minimum bytes possible
            v = value
            result = []
            while v != 0:
                result.insert(0, v&0xFF) # MSB first, so reverse when inserting
                v >>= 8

            # if desired length mismatch, zero pad or sign extend to fit
            if length is not None: # fixed size
                if len(result) < length: # pad
                    if not neg:
                        result = [0 for _ in range(length-len(result))] + result
                    else: # negative
                        result = [0xFF for _ in range(length-len(result))] + result
                elif len(result) >length: # overflow
                    raise ValueError("Field width overflow, not enough bits")

            return result

        raise ValueError("Unknown typeid:%d" % typeid)

    @staticmethod
    def decode(valuebytes, typeid:int, length:int): # any value
        if typeid <= Parameter.T_UINT_BP24:
            result = 0
            # decode unsigned integer first
            for i in range(length):
                result <<= 8
                result += valuebytes[i]
            # process any fixed binary points
            if typeid == Parameter.T_UINT:
                return result # no BP adjustment
            return (float(result)) / (2**Value.typebits(typeid))

        elif typeid == Parameter.T_CHAR:
            result = ""
            for b in range(length):
                result += chr(b)
            return result

        elif Parameter.T_SINT <= typeid <= Parameter.T_SINT_BP24:
            # decode unsigned int first
            result = 0
            for i in range(length):
                result <<= 8
                result += valuebytes[i]

            # turn to signed int based on high bit of MSB
            # 2's comp is 1's comp plus 1
            neg = ((valuebytes[0] & 0x80) == 0x80)
            if neg:
                onescomp = (~result) & ((2**(length*8))-1)
                result = -(onescomp + 1)

            # adjust for binary point
            if typeid == Parameter.T_SINT:
                return result # no BP, return as int
            else:
                # There is a BP, return as float
                return (float(result))/(2**Value.typebits(typeid))

        elif typeid == Parameter.T_FLOAT:
            return "TODO_FLOAT_IEEE_754-2008" #TODO: IEEE 754-2008

        #TODO: make this a bit 'softer'
        raise ValueError("Unsupported typeid:%s" % hex(typeid))

class OpenThingsLite: #TODO: now OpenThings (not lite)
    MFRID_ENERGENIE         = 0x04
    ENE_PRODUCTID_MIHO004   = 0x01  # monitor only
    ENE_PRODUCTID_MIHO005   = 0x02  # adaptor plus
    ENE_PRODUCTID_MIHO013   = 0x03  # eTRV
    ENE_PRODUCTID_MIHO006   = 0x05  # house monitor
    ENE_PRODUCTID_MIHO032   = 0x0C  # Motion sensor
    ENE_PRODUCTID_MIHO033   = 0x0D  # Open sensor
    ENE_PRODUCTID_MIHO069   = 0x12  # Thermostat

    HEADER_LEN              = 5
    CRYPT_IDX               = 0x03
    CRYPT_PID               = 242
    CRYPT_PIP               = 0x0100

    WR                      = 0x80

    SWITCH_PROD_IDX         = 0x02
    SWITCH_SENSOR_IDX       = 0x05
    SWITCH_VALUE_IDX        = 0x0A

    # sensor_id:
    #   high bit:    '0' for MiHome    (1 for OOK Legacy)
    #   high byte:   product_id        (0..127)
    #   low 3 bytes: sensor_serial_no

    SWITCH_TEMPL = (
        # HEADER
        0x0D,                            # [0]   length
        MFRID_ENERGENIE,                 # [1]   mfrid
        0,                               # [2]   prodid (fill in)
        byte1(CRYPT_PIP),                # [3]   pip msb
        byte0(CRYPT_PIP),                # [4]   pip lsb
        # BODY
        0,                               # [5]   sensor high (fill in)
        0,                               # [6]   sensor mid  (fill in)
        0,                               # [7]   sensor low  (fill in)
        WR | Parameter.P_SWITCH_STATE,   # [8]   rw | param
        Parameter.T_UINT | 1,            # [9]   type | len
        0,                               # [A]   value (fill in)
        0,                               # [B]   NUL
        0, 0                             # [C,D] CRC (fill in)
    )

    @staticmethod
    def make_switch_message(sensor_id:int, state:bool) -> bytes:
        """create a crc'd and signed switch message"""
        sensor_id &= 0x7FFFFFFF # high bit always 0 for MiHome
        buffer = bytearray(OpenThingsLite.SWITCH_TEMPL)
        buffer[OpenThingsLite.SWITCH_PROD_IDX]     = byte3(sensor_id)
        buffer[OpenThingsLite.SWITCH_SENSOR_IDX+0] = byte2(sensor_id)
        buffer[OpenThingsLite.SWITCH_SENSOR_IDX+1] = byte1(sensor_id)
        buffer[OpenThingsLite.SWITCH_SENSOR_IDX+2] = byte0(sensor_id)
        buffer[OpenThingsLite.SWITCH_VALUE_IDX]    = 1 if state else 0

        body = memoryview(buffer)[OpenThingsLite.HEADER_LEN:]
        CRC.sign(body)

        ##print("unencrypted version:%s" % hexstr(buffer))
        Crypt(OpenThingsLite.CRYPT_PID, OpenThingsLite.CRYPT_PIP).block(body)

        ##print("encrypted version:%s" % hexstr(buffer))
        return bytes(buffer)

    @staticmethod
    def decode(buffer) -> dict or None:
        """Decode an OpenThings message header into a dict"""

        MIN_LEN = OpenThingsLite.HEADER_LEN + 3 + 1 + 2  # sensorid+NUL+CRC
        if len(buffer) < MIN_LEN:
            print("warning: short payload, min:%d got:%d" % (MIN_LEN, len(buffer)))
            return None  #NODATA

        # DECRYPT
        encryptPIP = (buffer[OpenThingsLite.CRYPT_IDX]<<8) | buffer[OpenThingsLite.CRYPT_IDX+1]
        #NOTE decrypt is in place, need to take a copy?
        body = memoryview(buffer)[OpenThingsLite.HEADER_LEN:]
        #NOTE: this is an in-place decrypt
        Crypt(OpenThingsLite.CRYPT_PID, encryptPIP).block(body)

        # VERIFY CRC
        if not CRC.verify(body):
            print("warning: payload has invalid CRC: %s" % hexstr(buffer))
            return None  #NODATA

        # DECODE HEADER (5)
        length    = buffer[0]                               #0x0D
        mfrid     = buffer[1]                               #0x04
        productid = buffer[2]                               #0x02
        #pipH[3] pipL[4]                                    #0xnnnn
        header = {
            "mfrid": mfrid,
            "productid": productid
        }

        # DECODE BODY
        # [567]  sensorid(3)                                #0x000373
        data_len = length - 10
        if data_len >= 3:
            sensorid = buffer[5]<<16 | buffer[6]<<8 | buffer[7]
            header["sensorid"] = sensorid

        # DECODE SPECIFIC RECORDS
        # [8..]  data(length-10)
        #   switch:
        #     [8]paramid+rdwr (WR|PARAM_SWITCH_STATE)       0x80 + 0x73
        #     [9]type&len (UINT|1)                          0x00 + 0x01
        #     [A]value(0|1)                                 0x00 or 0x01
        #   [B]NUL(0)                                       0x00
        # [CD]crc[2]                                        0xnnnn

        i = 8
        recs = []

        while i < length and buffer[i] != 0:
            # PARAM
            param = buffer[i]
            wr = ((param & 0x80) == 0x80)
            paramid = param & 0x7F
            i += 1

            # TYPE/LEN
            typeid = buffer[i] & 0xF0
            vlen   = buffer[i] & 0x0F
            i += 1

            rec = {
                "wr":         wr,
                "paramid":    paramid,
                "paramname":  Parameter.paramname_for(paramid),
                "paramunit":  Parameter.unitname_for(paramid),
                "typeid":     typeid,
                "typename":   Parameter.typename_for(typeid),
                "length":     vlen
            }

            # VALUE
            if vlen != 0:
                valuebytes = memoryview(buffer)[i:i+vlen]
                rec["valuebytes"] = hexstr(valuebytes)
                i += vlen
                try:
                    rec["value"] = Value.decode(valuebytes, typeid, vlen)
                except Exception as e:
                    # soft fail
                    print("warning: Can't decode valuebytes:%s due to:%s" % (hexstr(valuebytes), str(e)))
            # store rec
            recs.append(rec)

        msg = {
            "type":    "OpenThings.Lite",
            "header":  header,
            "recs":    recs,
            "rawbytes": hexstr(buffer)
        }
        return msg

#----- MIHOME SOCKET -----------------------------------------------------------
class MiHomeSocket(Socket):
    def __init__(self, address:int, channel:int=0):
        Socket.__init__(self, address, channel)
        self._on_message  = self._make_switch_message(address, True)
        self._off_message = self._make_switch_message(address, False)

    @staticmethod
    def _make_switch_message(address:int, state:bool) -> bytes:
        return OpenThingsLite.make_switch_message(address, state)

    def set(self, state:bool, times:int=4) -> None:
        radio.want_cfg(radio.FSK)
        if state:
            radio.send(self._on_message, times=times)
        else:
            radio.send(self._off_message, times=times)

radio = EnergenieRadio()

#END: energenie.py
