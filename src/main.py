from utime import sleep_ms
from machine import Pin

LED_RED = Pin(6, Pin.OUT)
LED_GREEN = Pin(7, Pin.OUT)

for i in range(4):
    LED_GREEN.on()
    sleep_ms(250)
    LED_GREEN.off()
    sleep_ms(250)
    
import onoff 
