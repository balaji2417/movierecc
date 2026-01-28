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

# Register authentication routes
from auth import auth_bp

app.register_blueprint(auth_bp)

# =============================================================================
# DATABASE CONNECTION POOL
# =============================================================================
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "movie_recommender"),
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="movie_pool",
    pool_size=5,
    **db_config
)


def get_db():
    return connection_pool.get_connection()


# =============================================================================
# LOAD ML MODEL ON STARTUP
# =============================================================================
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'best_movie_recommendation_model.pkl')

with open(MODEL_PATH, 'rb') as f:
    model_artifacts = pickle.load(f)

model = model_artifacts['model']
feature_names = model_artifacts['feature_names']
model_name = model_artifacts.get('model_name', 'Unknown')

print(f"✓ Loaded model: {model_name}")
print(f"✓ Features: {len(feature_names)}")

# =============================================================================
# GENRE LIST (must match your training data)
# =============================================================================
GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "Foreign", "History", "Horror", "Music",
    "Mystery", "Romance", "Science Fiction", "TV Movie", "Thriller", "War", "Western"
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_movies_df():
    """Fetch all movies from database into a DataFrame."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM movies")
    movies = cursor.fetchall()
    cursor.close()
    conn.close()
    return pd.DataFrame(movies)


def prepare_features(movie_row, user_mean=3.5):
    """
    Build feature vector for a single movie.
    Must match the feature order from training.
    """
    features = {}

    # Z-scored features (use stored values or calculate)
    z_cols = [c for c in feature_names if c.endswith('__z')]
    for col in z_cols:
        base_col = col.replace('__z', '')
        if base_col in movie_row:
            features[col] = movie_row.get(base_col, 0)

    # Genre one-hot encoding
    movie_genres = str(movie_row.get('genres', '')).split('|')
    for genre in GENRES:
        features[genre] = 1 if genre in movie_genres else 0

    # Mean features
    if 'user_mean' in feature_names:
        features['user_mean'] = user_mean
    if 'movie_mean' in feature_names:
        features['movie_mean'] = movie_row.get('movie_mean', 3.5)

    # Build vector in correct order
    feature_vector = [features.get(f, 0) for f in feature_names]
    return np.array(feature_vector, dtype=np.float32).reshape(1, -1)


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "model": model_name,
        "features": len(feature_names)
    })


@app.route('/api/movies', methods=['GET'])
def get_movies():
    """Get all movies with optional filters."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Query params
    genre = request.args.get('genre')
    min_rating = request.args.get('min_rating', type=float)
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = "SELECT * FROM movies WHERE 1=1"
    params = []

    if genre:
        query += " AND genres LIKE %s"
        params.append(f"%{genre}%")

    if min_rating:
        query += " AND vote_average >= %s"
        params.append(min_rating)

    query += " ORDER BY popularity DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    movies = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"movies": movies, "count": len(movies)})


@app.route('/api/movies/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    """Get a single movie by ID."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
    movie = cursor.fetchone()
    cursor.close()
    conn.close()

    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    return jsonify(movie)


@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """
    Get personalized movie recommendations.

    Request body:
    {
        "user_mean": 3.5,
        "genres": ["Action", "Sci-Fi"],
        "min_rating": 3.5,
        "era": "modern",
        "limit": 10
    }
    """
    data = request.json or {}

    user_mean = data.get('user_mean', 3.5)
    preferred_genres = data.get('genres', [])
    min_rating = data.get('min_rating', 3.5)
    era = data.get('era', 'any')
    limit = data.get('limit', 10)

    # Fetch movies
    movies_df = get_movies_df()

    # Filter by era
    if era == 'classic':
        movies_df = movies_df[movies_df['release_year'] < 1980]
    elif era == 'retro':
        movies_df = movies_df[(movies_df['release_year'] >= 1980) & (movies_df['release_year'] < 2000)]
    elif era == 'modern':
        movies_df = movies_df[(movies_df['release_year'] >= 2000) & (movies_df['release_year'] < 2016)]
    elif era == 'recent':
        movies_df = movies_df[movies_df['release_year'] >= 2016]

    # Filter by genres
    if preferred_genres:
        def has_genre(genres_str):
            movie_genres = str(genres_str).split('|')
            return any(g in movie_genres for g in preferred_genres)

        movies_df = movies_df[movies_df['genres'].apply(has_genre)]

    if movies_df.empty:
        return jsonify({"recommendations": [], "message": "No movies match your criteria"})

    # Predict ratings for each movie
    predictions = []
    for _, movie in movies_df.iterrows():
        features = prepare_features(movie.to_dict(), user_mean)
        pred_rating = model.predict(features)[0]

        if pred_rating >= min_rating:
            predictions.append({
                "movie_id": int(movie['movie_id']),
                "title": movie['title'],
                "genres": movie['genres'],
                "release_year": int(movie['release_year']) if pd.notna(movie['release_year']) else None,
                "vote_average": float(movie['vote_average']) if pd.notna(movie['vote_average']) else None,
                "popularity": float(movie['popularity']) if pd.notna(movie['popularity']) else None,
                "predicted_rating": round(float(pred_rating), 2)
            })

    # Sort by predicted rating and limit
    predictions.sort(key=lambda x: x['predicted_rating'], reverse=True)
    recommendations = predictions[:limit]

    return jsonify({
        "recommendations": recommendations,
        "count": len(recommendations),
        "filters_applied": {
            "genres": preferred_genres,
            "era": era,
            "min_rating": min_rating
        }
    })


@app.route('/api/genres', methods=['GET'])
def get_genres():
    """Return list of available genres."""
    return jsonify({"genres": GENRES})


# =============================================================================
# RUN SERVER
# =============================================================================
if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🎬 Movie Recommendation API Starting...")
    print("=" * 50)
    app.run(debug=True, port=5000)