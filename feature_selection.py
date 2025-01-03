import numpy as np
import pandas as pd
from scipy import signal


class FeatureExtractor:
    def __init__(self,sampling_rate = 512):
        self.columns = ['energy_alpha', 'energy_beta', 'energy_theta', 'energy_delta', 'alpha_beta_ratio', 'max_freq', 'spectral_centroid', 'spectral_slope']
        self.sampling_rate = sampling_rate
    
    def calculate_psd_features(self,data):
        freqs, psd = signal.welch(data, fs = self.sampling_rate, nperseg = len(data))
        
        energy_alpha = np.sum(psd[(freqs >= 8) & (freqs <= 12)])
        energy_beta = np.sum(psd[(freqs >= 14) & (freqs <= 30)])
        energy_theta = np.sum(psd[(freqs >= 4) & (freqs <= 7)])
        energy_delta = np.sum(psd[(freqs >= 0.5) & (freqs <= 3)])
        
        alpha_beta_ratio = energy_alpha / energy_beta if energy_beta != 0 else 0
        
        return {
            'energy_alpha': energy_alpha,
            'energy_beta': energy_beta,
            'energy_theta': energy_theta,
            'energy_delta': energy_delta,
            'alpha_beta_ratio': alpha_beta_ratio
        }
    
    def calculate_spectral_features(self,data):
        freqs, psd = signal.welch(data, fs = self.sampling_rate, nperseg = len(data))
        max_freq = freqs[np.argmax(psd)]
        spectral_centroid = np.sum(freqs * psd) / np.sum(psd)
        log_freqs = np.log(freqs[1:])
        log_psd = np.log(psd[1:])
        spectral_slope = np.polyfit(log_freqs, log_psd, 1)[0]
        
        return {
            'max_freq': max_freq,
            'spectral_centroid': spectral_centroid,
            'spectral_slope': spectral_slope
        }
    
    def calculate_features(self,data):
        psd_features = self.calculate_psd_features(data)
        spectral_features = self.calculate_spectral_features(data)
        
        features =  {**psd_features, **spectral_features}
        return features
    