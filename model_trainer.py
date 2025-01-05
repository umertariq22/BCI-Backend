import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix
from sklearn.preprocessing import StandardScaler
import joblib

class Model:
    def __init__(self):
        self.C = 100
        self.gamma = 'auto'
        self.kernel = 'rbf'
        self.model = SVC(C=self.C, gamma=self.gamma, kernel=self.kernel,probability=True)
        self.scaler = StandardScaler()
    
    def train_with_split(self,X,y):
        data = pd.DataFrame(X).values
        label = pd.DataFrame(y).values
        data = self.scale_data(data)
        X_train, X_test, y_train, y_test = train_test_split(data, label, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        return self.evaluate(X_test, y_test)
    
    def train(self,X,y):
        data = pd.DataFrame(X).values
        label = pd.DataFrame(y).values
        data = self.scale_data(data)
        self.model.fit(data, label)
        return True
    
    def predict(self, X):
        X = pd.DataFrame(X).values
        X = self.scale_data(X)
        
        return self.model.predict(X)
    
    def evaluate(self, X, y):
        y_pred = self.predict(X)
        accuracy = accuracy_score(y, y_pred)
        report = classification_report(y, y_pred)
        matrix = confusion_matrix(y, y_pred)
        
        return accuracy, report, matrix
    
    def scale_data(self,X:pd.DataFrame):
        return self.scaler.fit_transform(X)
    
    def save_model(self,email):
        joblib.dump(self.model, f'models/{email}.joblib')
        joblib.dump(self.scaler, f'models/{email}_scaler.joblib')
        return True
        