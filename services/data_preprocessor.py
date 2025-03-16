from scipy import signal
import numpy as np

class PreprocessEEG:
    def __init__(self,sampling_rate = 512,notch_freq = 50, lowcut = 0.5, highcut = 30):
        self.sampling_rate = sampling_rate
        self.notch_freq = notch_freq
        self.lowcut = lowcut
        self.highcut = highcut
    
    def clean_data(self,data):
        data = np.array(data, dtype=np.float64)
        data[data == 0] = np.nan
        data[data > 4096] = np.nan
        indices = np.arange(len(data))
        valid_indices = indices[~np.isnan(data)] 
        invalid_indices = indices[np.isnan(data)]  
        if len(invalid_indices) > 0:
            data[invalid_indices] = np.interp(invalid_indices, valid_indices, data[valid_indices])
        return data.tolist()

    
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
        data = self.clean_data(data)
        filtered_data = self.apply_filter(data)
        return filtered_data   

if __name__ == '__main__':
    data = [1,2,4090,4098,500,3,4,5,6,7,8,9,10,0,0,0,4095]
    preprocessor = PreprocessEEG()
    cleaned_data = preprocessor.clean_data(data)
    print(cleaned_data)