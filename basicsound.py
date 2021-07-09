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
		self.color[0] = self.__fastNormFade(self.rFreq, f, ffreqs) # Red
		self.color[1] = self.__fastNormFade(self.gFreq, f, ffreqs) # Green
		self.color[2] = self.__fastNormFade(self.bFreq, f, ffreqs) # Blue	
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
		mu, sd = msd;
		ffnp = np.asarray(ffreqs)
		scalar = (1/chunk)*1/(sd*math.sqrt(2*math.pi))
		exp = np.exp
		weights = scalar * exp(-1/2 * exp((ffnp - mu)/sd)**2)
		return np.sum(f * weights)
	
# Initialize hardware libraries
i2c = busio.I2C(SCL, SDA)
pcas = []
feathers = []

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

if len(sys.argv) > 1:
	dev_index = int(sys.argv[1])

chunk = 2048 # sample size to analyze (shorter is faster but less precise)
samp_rate = 44100 # sample rate in hz
channel = 1 # mono audio
form = pyaudio.paInt16 # 16-bit format

bins = np.fft.fftfreq(chunk, d=1/samp_rate)[0:int(chunk/2)] # calculate FFT frequency series

audio = pyaudio.PyAudio() # initialize audio library
print("[ INFO ] Audio service started")

stream = audio.open(	format = form,
			rate = samp_rate,
			channels = channel,
			input_device_index = dev_index,
			input = True,
			frames_per_buffer = chunk) # start audio stream from microphone

def rms(items): # Root-mean-square average, used for audio intensity among other things
	return math.sqrt(sum([i**2 for i in items])/len(items))
def maxColorValue(feathers): # find the greatest float color value in a list of feathers (for scaling purposes)
	maxpf = [max(f.color) for f in feathers] # list all feathers' indivudial maxes
	return max(maxpf) # max of those

def scff(f):
	f.setColorFromFourier(pxx, bins)
scffv = np.vectorize(scff)

while True: # MAIN CONTROL LOOP
	data = stream.read(chunk, exception_on_overflow=False) # Pull one chunk of data from the microphone
	y_k = np.fft.fft([x/2 for x in data])[0:int(chunk/2)]/chunk # some complicated fourier transform math I don't fully understand
	y_k[1:] = 2*y_k[1:]
	pxx = np.abs(y_k) # pxx is the completed fourier transform	
	scffv(feathers)
	scale = 255/maxColorValue(feathers) # calculate intensity such that the brightest LED is full brightness
	for f in feathers: # also on each feather:
		f.applyColor(intensity=scale) # apply the calculated color to the LEDs
	feathers[int(time.time()) % 10].setServo(180)
	feathers[int(time.time()+5) % 10].setServo(0)
