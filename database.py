from pymongo import MongoClient, errors
import os

class Database:
    def __init__(self):
        self.client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'))
        self.db = self.client[os.environ.get('MONGO_DB', 'bci')]

    def get_collection(self, collection_name):
        return self.db[collection_name]
    
    
    def close(self):
        self.client.close()

db_instance = Database()