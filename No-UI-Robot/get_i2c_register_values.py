import smbus2 as smbus
import time
import RPi.GPIO as GPIO

PIN_I2C6_POWER_ENABLE = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_I2C6_POWER_ENABLE, GPIO.OUT)
time.sleep(0.1)
GPIO.output(PIN_I2C6_POWER_ENABLE, GPIO.HIGH)
time.sleep(0.1)

bus = smbus.SMBus(6)
DEVICE_ADDRESS = 0x53

for i in range(10):
    print(bus.read_byte_data(DEVICE_ADDRESS, i))
