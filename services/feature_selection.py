import numpy as np
import pandas as pd
from scipy import signal


class FeatureExtractor:
    def __init__(self,sampling_rate = 512):
        self.COLUMNS = ["energy_alpha", "energy_beta", "energy_theta", "energy_delta", "alpha_beta_ratio",
                        "max_freq", "spectral_centroid", "spectral_slope",
                        "mean", "variance", "rms", "zero_crossings", "hjorth_mobility", "hjorth_complexity"]
        self.sampling_rate = sampling_rate
    
    def calculate_psd_features(self,data):
        freqs, psd = signal.welch(data, fs = self.sampling_rate, nperseg = len(data))
        
        energy_alpha = np.sum(psd[(freqs >= 8) & (freqs <= 12)])
        energy_beta = np.sum(psd[(freqs >= 14) & (freqs <= 30)])
        energy_theta = np.sum(psd[(freqs >= 4) & (freqs <= 7)])
        energy_delta = np.sum(psd[(freqs >= 0.5) & (freqs <= 3)])
        
        alpha_beta_ratio = energy_alpha / energy_beta if energy_beta != 0 else 0
        
        features = {
            'energy_alpha': float(energy_alpha),
            'energy_beta': float(energy_beta),
            'energy_theta': float(energy_theta),
            'energy_delta': float(energy_delta),
            'alpha_beta_ratio': float(alpha_beta_ratio)
        }
        
        return features
    
    def calculate_spectral_features(self,data):
        freqs, psd = signal.welch(data, fs = self.sampling_rate, nperseg = len(data))
        max_freq = freqs[np.argmax(psd)]
        spectral_centroid = np.sum(freqs * psd) / np.sum(psd)
        log_freqs = np.log(freqs[1:])
        log_psd = np.log(psd[1:])
        spectral_slope = np.polyfit(log_freqs, log_psd, 1)[0]
        
        features ={
            'max_freq': float(max_freq),
            'spectral_centroid': float(spectral_centroid),
            'spectral_slope': float(spectral_slope)
        }
        
        return features
        


    def calculate_temporal_features(self,data):
        mean_value =  np.mean(data)
        variance = np.var(data)
        
        rms = np.sqrt(np.mean(np.square(data)))
        zero_crossings = np.sum(np.diff(np.sign(data)) != 0)
        mobility = np.std(np.diff(data)) / np.std(data)
        complexity = (np.std(np.diff(np.diff(data))) / np.std(np.diff(data))) / mobility
        features = {
            "mean": float(mean_value),
            "variance": float(variance),
            "rms": float(rms),
            "zero_crossings": float(zero_crossings),
            "hjorth_mobility": float(mobility),
            "hjorth_complexity": float(complexity),
        }
        
        return features

    
    def calculate_features(self,data):
        psd_features = self.calculate_psd_features(data)
        spectral_features = self.calculate_spectral_features(data)
        temporal_features = self.calculate_temporal_features(data)
        
        features =  {**psd_features, **spectral_features, **temporal_features}
        features_row = []
        
        for key in self.COLUMNS:
            features_row.append(features[key])
        return features_row, self.COLUMNS
    