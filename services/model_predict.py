import joblib
from .data_preprocessor import PreprocessEEG
from .feature_selection import FeatureExtractor
from .eeg_collect import SensorReader
import pickle

sensor_reader = SensorReader(port='COM3')
preprocessor = PreprocessEEG()
feature_extractor = FeatureExtractor()


class ModelPredict:
    def __init__(self):
        self.email = None
        self.model = None
        self.scaler = None
    
    def load_model(self,email):
        self.email = email
        with open(f'models/{self.email}.pkl', 'rb') as f:
            self.model = pickle.load(f)
        with open(f'models/{self.email}_scaler.pkl', 'rb') as f:
            self.scaler = pickle.load(f)
            
    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

if __name__ == '__main__':

    model=ModelPredict("ali@gmail.com")
    sensor_reader.connect()
    sensor_reader.start_reading()
    try:
        model.load_model()
        while True:
            generator_data = sensor_reader.read_one_second_data()
            data = list(next(generator_data, []))
            print(data)
            preprocessed_data = preprocessor.preprocess(data)
            feature = feature_extractor.calculate_features(preprocessed_data)
            prediction = model.predict([list(feature.values())])
            if prediction == 0:
                prediction = "Relaxing"
            else:
                prediction = "Focused"
            print(f"Prediction: {prediction}")    
    except KeyboardInterrupt:
        sensor_reader.stop_reading()
        sensor_reader.disconnect()
        print("Disconnected")        