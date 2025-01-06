from pymongo import MongoClient,errors
from model_trainer import Model
model = Model()
client = MongoClient("mongodb://localhost:27017")
db = client["bci"]
collection = db["users"]
eeg_collection = db["eegdata"]
 
data = eeg_collection.find({"email":"ali@gmail.com"})

X = []
y = []
for record in data:
    X.append(record["features"])
    y.append(record["label"])
print(len(X))    
model.train_with_split(X,y)
print("Model trained")
print(model.evaluate(X,y))
