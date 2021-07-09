#!/usr/bin/env python
import freenect
import numpy as np
import signal
import time
import math
import board
import neopixel
import threading

timeStep = 1/30 # 30fps for standard Kinect
percentile = 0.1 # base speed estimate on the X% most-leftward and most-rightward pixels
#scalar = 0.01 # scale of graph in terminal; +/- 100 units after scaling by default

movementTrigger = 5000 # amount of movement needed to trigger an expression

keep_running = True

# Kinect related functions
def get_depth():
	return freenect.sync_get_depth()[0]

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

# initialize neopixels
addresses = np.asarray(range(72))
vPixelEye = np.vectorize(getPixelEyeX)
vPixelX = np.vectorize(getPixelX)
vPixelY = np.vectorize(getPixelY)
eyeCoords = vPixelEye(addresses)
xCoords = vPixelX(addresses)
yCoords = vPixelY(addresses)
pixels = neopixel.NeoPixel(board.D18, 72, auto_write=False)

baseColors = []
for i in range(72): baseColors.append((255, 0, 255))

blinkTime = time.time()
blinkDuration = 0.1
blinkUnderflow = 2
mood = "none"

print('Press Ctrl-C in terminal to stop')
signal.signal(signal.SIGINT, handler)
lastF = get_depth()

# thread for text input, currently not in use
# class moodIn(threading.Thread):
#	def run(self):
#		global mood
#		while True:
#			mood = input("Select mood: ")
#m = moodIn()
#m.daemon=True
#m.start()

while keep_running:
	# Kinect directional processing
	newF = get_depth()
	lrRaw = calcMoveX(newF, lastF, timeStep)
	left, right = np.percentile(lrRaw, (percentile, 100-percentile))
	lrIndex = right+left
#	lIndex = -min(lrIndex, 0)
#	rIndex = max(lrIndex, 0)
#	print(" "*(100-int(lIndex*scalar)) + "#"*min(int(lIndex*scalar), 100) + "|" + "#"*int(rIndex*scalar))
#	lastF = newF
	
	# Neopixel expressions
	if lrIndex > movementTrigger:
		mood = "left"
	elif lrIndex < -movementTrigger:
		mood = "right" #reversed because of stage vs camera right
	blinkHeight = math.pow((time.time()-blinkTime-blinkDuration)/blinkDuration, 2) * (3+blinkUnderflow) - blinkUnderflow
	applyColors(getMoodMask(baseColors, mood, 0, blinkHeight))
	if time.time() > blinkTime+5:
		blinkTime = time.time()
		mood = "none"
	print(np.mean(newF))

