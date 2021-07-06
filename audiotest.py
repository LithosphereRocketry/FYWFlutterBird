import pyaudio
import wave
import numpy as np

dev_index = 1
rectime = 60
out_file = "test.wav"

samp_rate = 44100
chunk = 4096
channel = 1
form = pyaudio.paInt16
targetfreq = 440

bins = np.fft.fftfreq(chunk, d=1/samp_rate)

targetBin = 0
binFound = False
for b in bins:
	if b > targetfreq and not binFound:
		binFound = True
		targetBin = np.where(bins == b)[0][0]
		

audio = pyaudio.PyAudio()

print("[ INFO ] Audio service started")

stream = audio.open(	format = form,
			rate = samp_rate,
			channels = channel,
			input_device_index = dev_index,
			input = True,
			frames_per_buffer = chunk)

print("[ INFO ] Recording")
frames  = []
while True:
	data = stream.read(chunk)
	y_k = np.fft.fft([x/2 for x in data])[0:int(chunk/2)]/chunk
	y_k[1:] = 2*y_k[1:]
	pxx = np.abs(y_k)
	print("#"*int(pxx[targetBin]))
