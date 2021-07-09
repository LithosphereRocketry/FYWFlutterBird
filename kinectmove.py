#!/usr/bin/env python
# Color parameters
targetStep = 1/30
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

def getMoveX(current, prev, step=1/30):
	c = np.asarray(current)
	p = np.asarray(prev)	
	ddt = (c-p)/step
	return ddt

print('Press Ctrl-C in terminal to stop')
signal.signal(signal.SIGINT, handler)

lastFrame = get_depth()
time.sleep(targetStep)
lastTime = time.time()

while keep_running:
	dataset = get_depth()
	meandepth = np.mean(dataset)
	print(getMoveX(dataset, lastFrame, targetStep))
	while time.time() < lastTime + targetStep:
		time.sleep(0.001)
	lastTime = time.time()
	lastFrame = dataset
