# pico-energenie

Control and monitor Energenie devices, using a Raspberry Pi Pico

This can be loaded onto a Raspberry Pi Pico that is running the default 
MicroPython build that the Thonny IDE provides. It will probably also work
with Pimoroni MicroPython and CircuitPython (although you might need to
change how pins are refered to in CircuitPython as their API is slightly different).

This code is mostly a port of code from my Raspberry Pi Energenie repo here:
[github.com/whaleygeek/pyenergenie](https://github.com/whaleygeek/pyenergenie)

# Parts needed

[Raspberry Pi Pico](https://shop.pimoroni.com/products/raspberry-pi-pico?variant=32402092326995)

[Breadboard and Jumpers](https://monkmakes.com/pico_kit1.html)

[Adafruit RFM69HCW radio](https://shop.pimoroni.com/products/adafruit-rfm69hcw-transceiver-radio-breakout?variant=19594984071)

[Green button socket](https://cpc.farnell.com/energenie/ener002/1-gang-socket-radio-controlled/dp/PL14928)

Optionally, any other Energenie device from their catalogue (this code now supports
every device in the Energenie catalogue, if correctly configured).

# Wiring it up

The GP pin assignments are in ```energenie.py```, so wire your pico to your
Adafruit RFM69HCW board as per this map. Note that the EN pin is specific to the
Adafruit board, if you use the SparkFun board, you don't need that. If you
want to use a different layout (such as the pimoroni pico explorer), just change
these pin constants. You can also use the Energenie Raspberry Pi Two-Way radio
board if you have one of those (but the one-way remote won't work as it doesn't 
use the RFM69 radio chip).

Beware that some RFM69 radios are the 'standard power' type, and some are the
'high power type' (HCW). The configuration registers in this code are set for the
HCW high power device from Adafruit. If you have a standard power device, you
will need to change the PALEVEL register settings in ```energenie.py/EnergenieRadio```
to match (the changes are commented in there for you already, remember to change
both the OOK and FSK table entries).

The two LEDs are optional.

```python
SPI_N     = 0   # number of the SPI peripheral to use
GP_G0     = 0   # DIO0 INT pin
GP_CS     = 1   # chip select
GP_SCK    = 2   # SPI clock
GP_MOSI   = 3   # SPI master out slave in
GP_MISO   = 4   # SPI master in slave out
GP_RES    = 6   # must be low in normal operation (floats high)
GP_EN     = 7   # must be high to enable regulator (floats high)
GP_TX_LED = 26  # LED1, shows when transmitting
GP_RX_LED = 27  # LED2, shows when receiving
```

You need a 173mm bit of wire soldered to the ANT pin (bottom right)

# Pairing a legacy (green button) socket

To 'learn' the code to a socket, hold the green button on socket until
the socket LED flashes. Then use this code:
```
  import energenie
  light = LegacySocket()
  light.on()
```

The LED on the socket should flash a few times and the code is learnt.

# Tested the paired legacy socket
Use this simple code at the REPL prompt, to test your switch works:

```
  import energenie
  light = LegacySocket()
  light.on()
```

# Switching the legacy socket on and off with a simple user interface

To run a simple user interface that uses the REPL prompt, run this code at 
the REPL, or save it as your ```main.py``` and reboot.

```
   import onoff
```

Press Y then RETURN to turn the switch on

Press N then RETURN to turn the switch off

There is also a ```pico_user.py``` that can be connected to two LEDs and two buttons
to create a completely embedded demonstrator. Change ```onoff.py``` to import
```pico_energenie``` to use that interface. The code is commented already to show
you where to make the change.


# Using more than one socket

Device addresses are 20-bit numbers. The legacy address baked into this example 
code is 0xA0170, which happens to be the serial number of a battery powered hand
controller I own. But you can set a different address within that 20-bit
range and 'learn' any switches you have to that new code (as above).

```
light2 = LegacySocket(0x6C6C6)
light2.on()
```

If you have a 4-gang socket (or a dimmer switch), there are 4 sub-channels
on those devices, and you can set the sub channel as follows:

```
4gang_A = LegacySocket(channel=1)
4gang_B = LegacySocket(channel=2)
4gang_C = LegacySocket(channel=3)
4gang_D = LegacySocket(channel=4)
4gang_ALL = LegacySocket(channel=0)
```

Note that channel 0 means 'all channels'. Thus to turn all sockets off
on your 4-gang, use this:

```
4gang_ALL.off()
```

# MiHome devices

For the MiHome sockets, use the ```MiHomeSocket()``` class and provide it with
an address that matches your socket. 

You can work out the address of your MiHome socket (or any MiHome device)
by using the ```test_receive_ot()``` method in ```main.py``` to receive and 
decode the payload that is sent when you press the button on the front of the 
MiHome socket.

The address is a 32 bit number consisting of the productid in the high byte,
and the sensorid in the lower 3 bytes. Thus productid 2 address 0x373 would be
coded as address 0x02000373.

The MiHome devices are two-way and have significantly more features than the
legacy green-button devices. We plan to add more test programs in this repo
later to exercise all the features of all the devices. Until then, take a
look at the existing support for these devices in my Raspberry Pi pyenergenie
repo here, to work it out yourself:

[github.com/whaleygeek/pyenergenie](https://github.com/whaleygeek/pyenergenie)

David Whale, Feb 2023

