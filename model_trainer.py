import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix

class Model:
    def __init__(self):
        self.C = 100
        self.gamma = 'auto'
        self.kernel = 'rbf'
        self.model = SVC(C=self.C, gamma=self.gamma, kernel=self.kernel,probability=True)
    
    def train_with_split(self,X,y):
        data = pd.DataFrame(X).values
        label = pd.DataFrame(y).values
        X_train, X_test, y_train, y_test = train_test_split(data, label, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        
        
    def train(self, X, y):
        self.model.fit(X, y)
    
    def predict(self, X):
        return self.model.predict(X)
    
    def evaluate(self, X, y):
        y_pred = self.predict(X)
        accuracy = accuracy_score(y, y_pred)
        report = classification_report(y, y_pred)
        matrix = confusion_matrix(y, y_pred)
        
        return accuracy, report, matrix
        