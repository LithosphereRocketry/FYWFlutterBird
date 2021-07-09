#!/usr/bin/env python
import freenect
import matplotlib.pyplot as mp
import numpy as np
import signal
import time

timeStep = 1/30 # 30fps for standard Kinect
percentile = 0.1 # base speed estimate on the X% most-leftward and most-rightward pixels
scalar = 0.01 # scale of graph in terminal; +/- 100 units after scaling by default

keep_running = True


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

print('Press Ctrl-C in terminal to stop')
signal.signal(signal.SIGINT, handler)

lastF = get_depth()

while keep_running:
	newF = get_depth()
	lrRaw = calcMoveX(newF, lastF, timeStep)
	left, right = np.percentile(lrRaw, (percentile, 100-percentile))
	lrIndex = right+left
	lIndex = -min(lrIndex, 0)
	rIndex = max(lrIndex, 0)
	print(" "*(100-int(lIndex*scalar)) + "#"*min(int(lIndex*scalar), 100) + "|" + "#"*int(rIndex*scalar))
	lastF = newF
