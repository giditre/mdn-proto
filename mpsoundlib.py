import numpy as np
import sounddevice as sd
import numpy as np
from scipy.fftpack import rfft, rfftfreq

class SoundHandler():

  def __init__(self, playdev, recdev, fs=48000):
    self.playdev = playdev
    self.recdev = recdev
    self.fs = fs

    self.sample_cache = {}

    sd.default.samplerate = self.fs

  def send(self, freq, duration):
    sample_name = "{},{}".format(freq, duration)
    if sample_name in self.sample_cache:
      samples = self.sample_cache[sample_name]
    else:
      # generate samples
      samples = np.sin(2*np.pi*freq*np.arange(0., duration, 1/fs), dtype=np.float32)
    #print('Play sound (Ctrl+C to interrupt)...')
    sd.default.device = self.playdev
    sd.default.channels = 2
    try:
      sd.play(samples, blocking=True)
    except KeyboardInterrupt:
      sd.stop()

  def receive(self, duration, thresh=1e7):
    sd.default.device = self.recdev
    sd.default.channels = 1
    # record audio
    samples = sd.rec(duration * self.fs, blocking=True) 
    # analyse audio
    dft = [int(x) for x in np.abs(rfft(samples))]
    freq = [int(x*self.fs) for x in rfftfreq(len(dft))]    
    dft_dict = {}
    for i in range(len(freq)):
      f = freq[i]
      a = dft[i]
      if f not in dft_dict:
        dft_dict[f] = 0
      dft_dict[f] += a
    # apply threshold
    thresh_dft_dict = {}
    for f in dft_dict:
      if dft_dict[f] > thresh:
        thresh_dft_dict[f] = dft_dict[f]

    return [f for f in thresh_dft_dict]


if __name__ == "__main__":
  pass
