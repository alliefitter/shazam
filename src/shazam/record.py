import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

SAMPLE_RATE = 48000
CHANNELS = 2
DURATION = 10
DEVICE = 0
CHUNK = 2400

recording = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="int32",
    device=DEVICE,
    blocksize=CHUNK,
)
print("Recording...")
sd.wait()
print("Done, saving...")
wav_write("test_python.wav", SAMPLE_RATE, recording)
print("Saved to test_python.wav")
