#!/usr/bin/env python
import freenect
import numpy as np
import signal
import time
import math
import random as r
import board
import neopixel
import threading
import sys
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685
import pyaudio

timeStep = 1/30 # 30fps for standard Kinect
movePct = 0.1 # base speed estimate on the X% most-leftward and most-rightward pixels
#scalar = 0.01 # scale of graph in terminal; +/- 100 units after scaling by default

viewPct = 10 # percent of view an activation object takes up
maxFalloff = 0.25 # minimum state before feather reset
minFallTime = 0.25 # time (s) of fastest feather cycle
maxFallTime = 2 # time (s) of slowest feather cycle

nearPlane = 300  # distance at nearest point before errors
farPlane = 500 # distance at background

movementTrigger = 5000 # amount of movement needed to trigger an expression

# Color parameters
spacing = 1
whiteBalance = (1, 1, 1)

dev_index = 1 # microphone ID# in system, run lsaudio.py to check; can also run program with this as a parameter

keep_running = True

# Kinect related functions
def get_depth():
	depth = freenect.sync_get_depth()[0]
	return np.where(depth == 2047, 0, depth)

def get_video():
	return freenect.sync_get_video()[0]

def calcMoveX(frame, lastFrame, step):
	f1 = np.asarray(frame).astype(np.int32, casting='same_kind')
	f0 = np.asarray(lastFrame).astype(np.int32, casting='same_kind')
	ddt = np.subtract(f1,f0)/step
	lr = f1[:,1:-1] * (ddt[:,2:] - ddt[:,:-2]) / np.mean(f1)
	return lr

def handler(signum, frame):
	global keep_running
	keep_running = False

# Neopixel related functions
def getPixelEyeX(index):
	pos = index%24
	angle = pos/12*math.pi
	x = -3*math.sin(angle)
	return x
def getPixelX(index):
	pos = index%24
	angle = pos/12*math.pi
	ring = (index-pos)/24
	x = 3 + 14*ring - 3*math.sin(angle)
	return x
def getPixelY(index):
	pos = index%24
	angle = pos/12*math.pi
	y = -3*math.cos(angle)
	return y
# most depths range from -3 to 3, units in cm (approximately)
def getMoodMask(in_colors, mood, depth, blink):
	colors = np.asarray(in_colors)
	def getMoodPixel(r, g, b, x, y, e, mood, depth, blink):
		color = (r, g, b)
		if mood=="left":
			if e > depth: color = (0, 0, 0)
		elif mood=="right":
			if e < depth: color = (0, 0, 0)
		elif mood=="tired":
			if y > depth: color = (0, 0, 0)
		elif mood=="excited":
			if y < depth: color = (0, 0, 0)
		elif mood=="doubt":
			if abs(y) > 2+depth/3: color = (0, 0, 0)
		if abs(y) > blink: color = (0, 0, 0)
		return color
	colors = np.swapaxes(np.vectorize(getMoodPixel)(colors[:, 0], colors[:, 1], colors[:, 2], xCoords, yCoords, eyeCoords, mood, depth, blink), 0, 1)
	return colors

def applyColors(arr):
	global pixels
	for i in range(min(len(arr), len(pixels))):
		pixels[i] = arr[i]
	pixels.show()

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
		self.cycleTime = r.uniform(minFallTime, maxFallTime)
		self.lastCycle = time.time()
	def setServoFromTime(self, maxAngle):
		mAngInv = 180-maxAngle
		if time.time() > self.lastCycle + self.cycleTime: self.lastCycle = time.time()
		angle = 180-mAngInv*(1-math.pow(maxFalloff, (time.time()-self.lastCycle)/self.cycleTime))
		self.setServo(angle)
	def setServo(self, angle): # set servo target angle
		self.servo.angle = self.__clip(angle, 0, 180) # does what it says on the can
	def applyColor(self, intensity=1): # set physical color to value stored in memory by whatever preset
		self.pca.channels[self.rPin].duty_cycle = int(self.__clip(self.color[0]*intensity*256*whiteBalance[0], 0, 65535)) # scale float color to 16-bit scale & incorportate white balance config
		self.pca.channels[self.gPin].duty_cycle = int(self.__clip(self.color[1]*intensity*256*whiteBalance[1], 0, 65535))
		self.pca.channels[self.bPin].duty_cycle = int(self.__clip(self.color[2]*intensity*256*whiteBalance[2], 0, 65535))
	def setColorFromFourier(self, f, ffreqs): # Option 1 to set memory color: set colors according to Gaussian-blurred intensity on Fourier transform
		self.color[0] = self.__fastNormFade(self.rFreq, f, ffreqs) # Red
		self.color[1] = self.__fastNormFade(self.gFreq, f, ffreqs) # Green
		self.color[2] = self.__fastNormFade(self.bFreq, f, ffreqs) # Blue	
	def setColorFromIntensity(self, i):
		self.color = [510*i-255*i**2, 1020*i - 1020*i**2, 1020*i - 1020*i**2]
	def debugColor(self, intensity=1): # Testing function, displays current memory color as int, scaled by intensity; no white balances
		return "("+str(int(self.color[0]*intensity))+", "+str(int(self.color[1]*intensity))+", "+str(int(self.color[2]*intensity))+")"
	
	#Private utility functions
	def __clip(self, n, lower, upper): # Limit a number between upper and lower bounds
		return min(upper, max(lower, n))	
	def __keyToFreq(self, key): # Calculate the frequency of a given piano key
		return 27.5*math.exp(key/12*math.log(2)) # This is a nicer way to write 27.5 * ( 12root(2) ) ^ key
	def __keyToFreqSD(self, key, spacing): # Calculate the frequency spacing between 2 keys
		return math.log(2)/12*spacing * self.__keyToFreq(key) # since keyToFreq is exponential, its derivative is a constant * itself
	def __fastNormFade(self, msd, f, ffreqs):
		mu, sd = msd
		ffnp = np.asarray(ffreqs)
		scalar = (1/chunk)*1/(sd*math.sqrt(2*math.pi))
		exp = np.exp
		weights = scalar * exp(-1/2 * exp((ffnp - mu)/sd)**2)
		return np.sum(f * weights)

# initialize neopixel coords
addresses = np.asarray(range(72))
vPixelEye = np.vectorize(getPixelEyeX)
vPixelX = np.vectorize(getPixelX)
vPixelY = np.vectorize(getPixelY)
eyeCoords = vPixelEye(addresses)
xCoords = vPixelX(addresses)
yCoords = vPixelY(addresses)

# Initialize hardware
i2c = busio.I2C(SCL, SDA)
pixels = neopixel.NeoPixel(board.D18, 72, auto_write=False)
baseColors = []
feathers = []
pcas = []
for i in range(72): baseColors.append((255, 0, 255))

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

blinkTime = time.time()
blinkDuration = 0.1
blinkUnderflow = 2
mood = "none"

print('Press Ctrl-C in terminal to stop')
signal.signal(signal.SIGINT, handler)
lastF = farPlane-get_depth()

distMask = np.linspace(np.full(640, 0), np.full(640, 2), 480)

while keep_running:
	# Kinect directional processing
	newF = farPlane-np.asarray(get_depth()).astype(np.int32)
	lrRaw = calcMoveX(newF, lastF, timeStep)
	left, right = np.percentile(lrRaw, (movePct, 100-movePct))
	lrIndex = right+left
#	lIndex = -min(lrIndex, 0)
#	rIndex = max(lrIndex, 0)
#	print(" "*(100-int(lIndex*scalar)) + "#"*min(int(lIndex*scalar), 100) + "|" + "#"*int(rIndex*scalar))
#	lastF = newF
	
	# Neopixel expressions
	#print(lrIndex)
	#print(left)
	#if lrIndex > movementTrigger:
	#	mood = "left"
	#elif lrIndex < -movementTrigger:
	#	mood = "right" #reversed because of stage vs camera right
	blinkHeight = math.pow((time.time()-blinkTime-blinkDuration)/blinkDuration, 2) * (3+blinkUnderflow) - blinkUnderflow
	applyColors(getMoodMask(baseColors, mood, 0, blinkHeight))
	if time.time() > blinkTime+5:
		blinkTime = time.time()
		mood = "none"
	fdist = np.percentile((newF*distMask)[newF != farPlane], 100-viewPct)
	distScale = fdist/(farPlane-nearPlane) ##fdist has to do with distance. Turns negative when crossing the clipping planer
	for f in feathers:
		f.setServoFromTime(180-distScale*180) ##180 is the full range of motion
		f.setColorFromIntensity(distScale)
		f.applyColor()
	print(distScale)
