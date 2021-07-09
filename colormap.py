# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import sys

from board import SCL, SDA
import busio

# Import the PCA9685 module. Available in the bundle and here:
#   https://github.com/adafruit/Adafruit_CircuitPython_PCA9685
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(SCL, SDA)

# Create a simple PCA9685 class instance.
dev_index = 0
if len(sys.argv) > 1:
	dev_index = int(sys.argv[1])

pca = PCA9685(i2c, address=64+dev_index)
# You can optionally provide a finer tuned reference clock speed to improve the accuracy of the
# timing pulses. This calibration will be specific to each board and its environment. See the
# calibration.py example in the PCA9685 driver.
# pca = PCA9685(i2c, reference_clock_speed=25630710)
pca.frequency = 50

rpt, gpt, bpt = input("Pin order: ").split(" ")
rp = int(rpt)
gp = int(gpt)
bp = int(bpt)

while True:
	rt, gt, bt = input("Color: ").split(" ")
	pca.channels[rp].duty_cycle = 256*int(rt)
	pca.channels[gp].duty_cycle = 256*int(gt)
	pca.channels[bp].duty_cycle = 256*int(bt)
