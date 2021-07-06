# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time

from board import SCL, SDA
import busio

# Import the PCA9685 module. Available in the bundle and here:
#   https://github.com/adafruit/Adafruit_CircuitPython_PCA9685
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(SCL, SDA)

# Create a simple PCA9685 class instance.
pca = PCA9685(i2c, address=64)
# You can optionally provide a finer tuned reference clock speed to improve the accuracy of the
# timing pulses. This calibration will be specific to each board and its environment. See the
# calibration.py example in the PCA9685 driver.
# pca = PCA9685(i2c, reference_clock_speed=25630710)
pca.frequency = 50

# This is an example for the Micro Servo - High Powered, High Torque Metal Gear:
#   https://www.adafruit.com/product/2307
servo7 = servo.Servo(pca.channels[15], min_pulse=500, max_pulse=2600)

pca.channels[13].duty_cycle = 0xFFFF

# We sleep in the loops to give the servo time to move into position.
for i in range(180):
    servo7.angle = i
    pca.channels[12].duty_cycle = 0xFFFF - 364*i
    pca.channels[14].duty_cycle = 364*i
    time.sleep(0.03)
for i in range(180):
    servo7.angle = 180 - i
    pca.channels[12].duty_cycle = 0xFFFF - 364*i
    pca.channels[14].duty_cycle = 364*i
    time.sleep(0.03)

pca.deinit()
