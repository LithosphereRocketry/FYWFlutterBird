servoLanes = [[12]];

import time

from board import SCL, SDA
import busio

from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

class Feather:
	minPulse = 500
	maxPulse = 2600
	
	def __init__(self, pca, firstPin):
		self.pca = pca
		self.rPin = firstPin
		self.gPin = firstPin+1
		self.bPin = firstPin+2
		self.servoPin = firstPin+3
		self.servo = servo.Servo(self.pca.channels[self.servoPin], min_pulse = self.minPulse, max_pulse = self.maxPulse)
		
	def setServo(self, angle):
		self.servo.angle = angle;

	def setColor(self, r, g, b):
		self.pca.channels[self.rPin].duty_cycle = r*256;
		self.pca.channels[self.gPin].duty_cycle = g*256;
		self.pca.channels[self.bPin].duty_cycle = b*256;

i2c = busio.I2C(SCL, SDA)

pcas = []
feathers = []

i = 0
for addr in servoLanes:
	pcas.append(PCA9685(i2c, address=64+i))
	pcas[i].frequency = 50
	for lane in addr:	
		feathers.append(Feather(pcas[i], lane))
	i += 1

i = 0
while True:
	#feathers[0].setServo(i % 180)
	feathers[0].setColor(i % 256, (i+85) % 256, (i+171)%256)
	i += 1	
	#time.sleep(0.01)
