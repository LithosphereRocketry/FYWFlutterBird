import time
import math
import board
import neopixel
import numpy as np
import threading

pixels = neopixel.NeoPixel(board.D18, 72, auto_write=False)

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

addresses = np.asarray(range(72))
vPixelEye = np.vectorize(getPixelEyeX)
vPixelX = np.vectorize(getPixelX)
vPixelY = np.vectorize(getPixelY)
eyeCoords = vPixelEye(addresses)
xCoords = vPixelX(addresses)
yCoords = vPixelY(addresses)

baseColors = []
for i in range(72): baseColors.append((255, 0, 255))

blinkTime = time.time()
blinkDuration = 0.1
blinkUnderflow = 2
mood = "none"

class moodIn(threading.Thread):
	def run(self):
		global mood
		while True:
			mood = input("Select mood: ")
m = moodIn()
m.daemon=True
m.start()

while True:
	blinkHeight = math.pow((time.time()-blinkTime-blinkDuration)/blinkDuration, 2) * (3+blinkUnderflow) - blinkUnderflow
	applyColors(getMoodMask(baseColors, mood, 0, blinkHeight))
	if time.time() > blinkTime+5:
		blinkTime = time.time()
	
