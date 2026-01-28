
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import pickle
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Balaji2k"),
    "database": os.getenv("DB_NAME", "movie_recommender"),
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="movie_pool",
    pool_size=5,
    **db_config
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'best_movie_recommendation_model.pkl')
with open(MODEL_PATH, 'rb') as f:
    model_artifacts = pickle.load(f)

model = model_artifacts['model']
feature_names = model_artifacts['feature_names']
model_name = model_artifacts.get('model_name', 'Unknown')

print(f"✓ Loaded model: {model_name}")
print(f"✓ Features: {feature_names}")