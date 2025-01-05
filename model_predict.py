import joblib

class ModelPredict:
    def __init__(self,email):
        self.email = email
        self.model = None
        self.scaler = None
    
    def load_model(self):
        model_path = f"models/{self.email}.joblib"
        scaler_path = f"models/{self.email}_scaler.joblib"
        
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
