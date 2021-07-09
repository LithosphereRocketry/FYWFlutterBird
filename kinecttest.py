#!/usr/bin/env python
# Color parameters
spacing = 1
whiteBalance = (1, 1, 1)

dev_index = 1 # microphone ID# in system, run lsaudio.py to check; can also run program with this as a parameter

# Libraries
import time
import math
import sys
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685
import pyaudio
import numpy as np

# Feather controller class
class Feather:
	minPulse = 500 # Servo minimum pulse (global)
	maxPulse = 2600 # Servo maximum pulse (global)
	# Public functions:
	def __init__(self, pca, firstPin, pos=[0, 0, 0], spacing=1): # create the feather object
		self.pca = pca # use the PCA9685 object given
		self.rPin = firstPin # assume pins are in the order R, G, B, Servo
		self.gPin = firstPin+1
		self.bPin = firstPin+2
		self.servoPin = firstPin+3
		self.servo = servo.Servo(self.pca.channels[self.servoPin], min_pulse = self.minPulse, max_pulse = self.maxPulse) # initialize servo object
		self.pos = pos # read spatial position from input
		self.rFreq = (self.__keyToFreq(pos[0]), self.__keyToFreqSD(pos[0], spacing)) # Set R, G, B response frequencies all to piano scale on X position
		self.gFreq = (self.__keyToFreq(pos[0]), self.__keyToFreqSD(pos[0], spacing))
		self.bFreq = (self.__keyToFreq(pos[0]), self.__keyToFreqSD(pos[0], spacing))
		self.color = [0, 0, 0] # initialize color variable for future use
	def setServo(self, angle): # set servo target angle
		self.servo.angle = angle; # does what it says on the can
	def applyColor(self, intensity=1): # set physical color to value stored in memory by whatever preset
		self.pca.channels[self.rPin].duty_cycle = int(self.__clip(self.color[0]*intensity*256*whiteBalance[0], 0, 65535)) # scale float color to 16-bit scale & incorportate white balance config
		self.pca.channels[self.gPin].duty_cycle = int(self.__clip(self.color[1]*intensity*256*whiteBalance[1], 0, 65535))
		self.pca.channels[self.bPin].duty_cycle = int(self.__clip(self.color[2]*intensity*256*whiteBalance[2], 0, 65535))
	def setColorFromFourier(self, f, ffreqs): # Option 1 to set memory color: set colors according to Gaussian-blurred intensity on Fourier transform
		self.color[0] = self.__normFade(self.rFreq, f, ffreqs) # Red
		self.color[1] = self.__normFade(self.gFreq, f, ffreqs) # Green
		self.color[2] = self.__normFade(self.bFreq, f, ffreqs) # Blue
	
	def debugColor(self, intensity=1): # Testing function, displays current memory color as int, scaled by intensity; no white balances
		return "("+str(int(self.color[0]*intensity))+", "+str(int(self.color[1]*intensity))+", "+str(int(self.color[2]*intensity))+")"
	#Private utility functions
	def __clip(self, n, lower, upper): # Limit a number between upper and lower bounds
		return min(upper, max(lower, n))	
	def __keyToFreq(self, key): # Calculate the frequency of a given piano key
		return 27.5*math.exp(key/12*math.log(2)) # This is a nicer way to write 27.5 * ( 12root(2) ) ^ key
	def __keyToFreqSD(self, key, spacing): # Calculate the frequency spacing between 2 keys
		return math.log(2)/12*spacing * self.__keyToFreq(key) # since keyToFreq is exponential, its derivative is a constant * itself
	def __normFade(self, msd, f, ffreqs): # Sum up a Gaussian "window" of a frequency spectrum
		mu, sd = msd; # The input is a tuple (mean, standard deviation)
		weights = [(1/chunk)*1/(sd*math.sqrt(2*math.pi)) * math.exp(-1/2 * ((x-mu)/sd)**2) for x in ffreqs] # For each frequency, create a Gaussian-curve weight based on distance from f
		return sum(np.multiply(f, weights)) # Take a weighted sum of all frequency weights * f

# Initialize hardware libraries
i2c = busio.I2C(SCL, SDA)
pcas = []
feathers = []

"""
cfgText = open("feathers.txt", "r").read() # Read config text into string
for block in cfgText.split("CONTROLLER "): # Split by controllers
	rows = block.split("\n") # Split each controller into rows
	if len(rows[0]) > 0: # If this controller actually exists... (sometimes there are false rows at the top or bottom of the file it seems)
		addr = int(rows[0]) # The first number after "CONTROLLER " is the controller's configured address
		pcas.append(PCA9685(i2c, address=64+addr)) # Create a controller object, i2c addresses for these chips start at 64 and go up to 127
		pcas[len(pcas)-1].frequency = 50 # 50 Hz is required for servos
		for f in rows[1:]: # Skip the first row since that was for the controller
			if len(f) > 0: # If this row exists... (see above)
				row = f.split("\t") # Split the row by tab characters
				channel = int(row[0]) # the first number is the pin
				position = [int(x) for x in row[1].split(",")] # Split coordinates by commas
				feathers.append(Feather(pcas[len(pcas)-1], channel, pos=position, spacing=spacing)) # Create a feather object with the given parameters
"""
testpca = PCA9685(i2c, address=67)
testpca.frequency = 50
feather = Feather(testpca, 0, pos=(1, 1, 1), spacing=1)
def rms(items): # Root-mean-square average, used for audio intensity among other things
	return math.sqrt(sum([i**2 for i in items])/len(items))
def maxColorValue(feathers): # find the greatest float color value in a list of feathers (for scaling purposes)
	maxpf = [max(f.color) for f in feathers] # list all feathers' indivudial maxes
	return max(maxpf) # max of those

import freenect
import matplotlib.pyplot as mp
import signal
import time

keep_running = True
def get_depth():
    return freenect.sync_get_depth()[0]
def get_video():
    return freenect.sync_get_video()[0]
def handler(signum, frame):
    global keep_running
    keep_running = False

print('Press Ctrl-C in terminal to stop')
signal.signal(signal.SIGINT, handler)

while keep_running:
	dataset = get_depth()
	meandepth = np.mean(dataset)
	print(meandepth)
	feather.color = [255 - meandepth/2048*255, 0, 0]
	feather.applyColor()
	time.sleep(0.1)
