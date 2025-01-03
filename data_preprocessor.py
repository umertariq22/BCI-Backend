from scipy import signal

class PreprocessEEG:
    def __init__(self,sampling_rate = 512,notch_freq = 50, lowcut = 0.5, highcut = 30):
        self.sampling_rate = sampling_rate
        self.notch_freq = notch_freq
        self.lowcut = lowcut
        self.highcut = highcut
    
    def initialize_filter(self):
        nyquist = 0.5 * self.sampling_rate
        notch_freq_normalized = self.notch_freq / nyquist
        self.notch_b, self.notch_a = signal.iirnotch(notch_freq_normalized, Q=0.05, fs = self.sampling_rate)
        
        lowcut_normalized = self.lowcut / nyquist
        highcut_normalized = self.highcut / nyquist
        self.band_pass_b, self.band_pass_a = signal.butter(4, [lowcut_normalized, highcut_normalized], btype='band')
    
    def apply_filter(self, data):
        notch_filtered = signal.filtfilt(self.notch_b, self.notch_a, data)
        band_pass_filtered = signal.filtfilt(self.band_pass_b, self.band_pass_a, notch_filtered)        
        return band_pass_filtered
    
    
    def preprocess(self, data):
        self.initialize_filter()
        return self.apply_filter(data)    
        