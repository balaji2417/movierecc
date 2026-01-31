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

# Better CORS configuration
CORS(app, resources={r"/api/*": {
    "origins": [
        "http://localhost:3000",
        "https://your-app-name.netlify.app"  # Update after deploying
    ]
}}, supports_credentials=True)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Register authentication routes
from auth import auth_bp
from ratings import ratings_bp

app.register_blueprint(auth_bp)
app.register_blueprint(ratings_bp)



# =============================================================================
# DATABASE CONNECTION POOL
# =============================================================================
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 53462)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Context manager for database connections - ensures proper cleanup."""
    conn = connection_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()

def get_db():
    """Get a database connection from the pool."""
    return connection_pool.get_connection()

connection_pool = pooling.MySQLConnectionPool(
    pool_name="movie_pool",
    pool_size=10,  # Increased from 5
    pool_reset_session=True,
    **db_config
)


def get_db():
    return connection_pool.get_connection()


# =============================================================================
# LOAD ML MODEL ON STARTUP
# =============================================================================
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'Models', 'best_movie_recommendation_model.pkl')
import os

# Add this near the top to debug
print("Current directory:", os.getcwd())
print("Files in current directory:", os.listdir('.'))
print("Files in models folder:", os.listdir('models') if os.path.exists('models') else 'models folder not found')

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'Models', 'best_movie_recommendation_model.pkl')
print("MODEL_PATH:", MODEL_PATH)
print("Model file exists:", os.path.exists(MODEL_PATH))

with open(MODEL_PATH, 'rb') as f:
    model_artifacts = pickle.load(f)

model = model_artifacts['model']
feature_names = model_artifacts['feature_names']
model_name = model_artifacts.get('model_name', 'Unknown')

print(f"✓ Loaded model: {model_name}")
print(f"✓ Features: {len(feature_names)}")

print("All 28 features:")
for i, name in enumerate(model_artifacts['feature_names']):
    print(f"{i+1}. {name}")

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


FEATURE_STATS = {
    'popularity_log1p': {'mean': 2.438942, 'std': 0.626967},
    'vote_average': {'mean': 6.874639, 'std': 0.839685},
    'vote_count_log1p': {'mean': 6.388657, 'std': 1.605040},
    'year': {'mean': 1991.810726, 'std': 15.101007},
    'month': {'mean': 7.274652, 'std': 3.258403},
    'day': {'mean': 15.649785, 'std': 8.482775},
}

def z_score(value, mean, std):
    """Calculate z-score: (value - mean) / std"""
    if std == 0:
        return 0.0
    return (value - mean) / std


def prepare_features(movie_row, user_mean=3.5):
    """
    Build feature vector for a single movie.
    Must match the feature order from training (28 features).
    """
    import math

    features = {}

    # 1. popularity_log1p__z
    popularity = float(movie_row.get('popularity', 0) or 0)
    popularity_log1p = math.log1p(popularity)  # log(1 + popularity)
    features['popularity_log1p__z'] = z_score(
        popularity_log1p,
        FEATURE_STATS['popularity_log1p']['mean'],
        FEATURE_STATS['popularity_log1p']['std']
    )

    # 2. vote_average__z
    vote_average = float(movie_row.get('vote_average', 0) or 0)
    features['vote_average__z'] = z_score(
        vote_average,
        FEATURE_STATS['vote_average']['mean'],
        FEATURE_STATS['vote_average']['std']
    )

    # 3. vote_count_log1p__z
    vote_count = float(movie_row.get('vote_count', 0) or 0)
    vote_count_log1p = math.log1p(vote_count)
    features['vote_count_log1p__z'] = z_score(
        vote_count_log1p,
        FEATURE_STATS['vote_count_log1p']['mean'],
        FEATURE_STATS['vote_count_log1p']['std']
    )

    # 4. year__z
    year = float(movie_row.get('release_year', 2000) or 2000)
    features['year__z'] = z_score(
        year,
        FEATURE_STATS['year']['mean'],
        FEATURE_STATS['year']['std']
    )

    # 5. month__z (default to 6 if not available)
    features['month__z'] = z_score(6, FEATURE_STATS['month']['mean'], FEATURE_STATS['month']['std'])

    # 6. day__z (default to 15 if not available)
    features['day__z'] = z_score(15, FEATURE_STATS['day']['mean'], FEATURE_STATS['day']['std'])

    # 7-26. Genre one-hot encoding
    movie_genres = str(movie_row.get('genres', '')).split('|')
    for genre in GENRES:
        features[genre] = 1.0 if genre in movie_genres else 0.0

    # 27. user_mean
    features['user_mean'] = float(user_mean)

    # 28. movie_mean
    features['movie_mean'] = float(movie_row.get('movie_mean', 3.5) or 3.5)

    # Build vector in correct order (must match feature_names)
    feature_vector = [features.get(f, 0.0) for f in feature_names]

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
    data = request.json or {}

    user_mean = data.get('user_mean', 3.5)
    preferred_genres = data.get('genres', [])
    min_rating = data.get('min_rating', 3.5)
    era = data.get('era', 'any')
    limit = data.get('limit', 10)

    # Fetch movies
    movies_df = get_movies_df()
    print(f"DEBUG: Total movies in DB: {len(movies_df)}")

    # Filter by era
    if era != 'any':
        if era == 'classic':
            movies_df = movies_df[movies_df['release_year'] < 1980]
        elif era == 'retro':
            movies_df = movies_df[(movies_df['release_year'] >= 1980) & (movies_df['release_year'] < 2000)]
        elif era == 'modern':
            movies_df = movies_df[(movies_df['release_year'] >= 2000) & (movies_df['release_year'] < 2016)]
        elif era == 'recent':
            movies_df = movies_df[movies_df['release_year'] >= 2016]

    print(f"DEBUG: After era filter: {len(movies_df)}")

    # Filter by genres
    if preferred_genres:
        def has_genre(genres_str):
            movie_genres = str(genres_str).split('|')
            return any(g in movie_genres for g in preferred_genres)

        movies_df = movies_df[movies_df['genres'].apply(has_genre)]

    print(f"DEBUG: After genre filter: {len(movies_df)}")

    if movies_df.empty:
        return jsonify({"recommendations": [], "message": "No movies match your criteria"})

    # Predict ratings - TEST FIRST 3 MOVIES
    print(f"DEBUG: Testing predictions on first 3 movies...")
    for i, (_, movie) in enumerate(movies_df.head(3).iterrows()):
        movie_dict = movie.to_dict()
        print(f"\nMovie {i + 1}: {movie_dict.get('title')}")
        print(f"  - genres: {movie_dict.get('genres')}")
        print(f"  - popularity: {movie_dict.get('popularity')}")
        print(f"  - vote_average: {movie_dict.get('vote_average')}")
        print(f"  - movie_mean: {movie_dict.get('movie_mean')}")

        features = prepare_features(movie_dict, user_mean)
        print(f"  - feature_vector (first 6): {features[0][:6]}")
        print(f"  - feature_vector (last 2): {features[0][-2:]}")

        pred = model.predict(features)[0]
        print(f"  - PREDICTED RATING: {pred}")

    # Now do all predictions
        # Predict ratings for each movie
        predictions = []

        for _, movie in movies_df.iterrows():
            features = prepare_features(movie.to_dict(), user_mean)
            raw_pred = model.predict(features)[0]

            # Scale prediction from model's range (0-1) to rating range (0.5-5.0)
            pred_rating = (raw_pred * 4.5) + 0.5
            pred_rating = max(0.5, min(5.0, pred_rating))  # Clamp to valid range

            if pred_rating >= min_rating:
                predictions.append({
                    "movie_id": int(movie['movie_id']),
                    "title": movie['title'],
                    "genres": movie['genres'],
                    "release_year": int(movie['release_year']) if pd.notna(movie['release_year']) else None,
                    "vote_average": float(movie['vote_average']) if pd.notna(movie['vote_average']) else None,
                    "popularity": float(movie['popularity']) if pd.notna(movie['popularity']) else None,
                    "poster_url": movie.get('poster_url', ''),
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