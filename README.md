# 🎬 Movie Recommendation System

A full-stack movie recommendation web application that predicts personalized movie ratings using machine learning. Built with React, Flask, MySQL, and XGBoost — deployed across Netlify, Render, and Railway.

**Live Demo:** [https://your-app.netlify.app](https://your-app.netlify.app)  
**Backend API:** [https://movie-recommender-api-0sbx.onrender.com](https://movie-recommender-api-0sbx.onrender.com)

---

## 🎯 Motivation

Most movie recommenders are black boxes — they suggest movies but never explain *why*. Many also require mandatory account creation before you can get any recommendations at all.

This project takes a different approach: transparent predictions, no sign-up required, and a hybrid experience that works for both anonymous and registered users.

### How It's Different

| Traditional Recommenders | This Project |
|--------------------------|--------------|
| Requires account creation | Works anonymously OR with an account |
| Black-box suggestions | Shows predicted ratings (0.5–5.0 scale) |
| Cold-start problem for new users | Preference-based input solves this instantly |
| Collaborative filtering only | Hybrid: content features + user behavior |

---

## ✨ Features

- **Hybrid User Experience** — Anonymous users get instant recommendations by selecting genre preferences; registered users build a rating history for increasingly personalized results
- **Rating Predictions** — Predicts how much you'd enjoy a movie on a 0.5–5.0 scale using XGBoost regression (~0.82 RMSE)
- **Feedback Loop** — Rate recommended movies and immediately get improved future recommendations by recalculating your user profile
- **Session Migration** — Start as a guest, then register to save your anonymous session ratings permanently
- **Watchlist** — Save movies to watch later
- **JWT Authentication** — Secure registration and login with bcrypt password hashing
- **9,000+ Movie Catalog** — Trained on MovieLens and TMDB datasets

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│   Database   │
│  React +     │     │  Flask REST  │     │   MySQL      │
│  Tailwind    │     │  API + ML    │     │  (Railway)   │
│  (Netlify)   │◀────│  (Render)    │◀────│              │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                     ┌─────┴─────┐
                     │  XGBoost  │
                     │  Model    │
                     │  (.pkl)   │
                     └───────────┘
```

---

## 🔧 Tech Stack

**Frontend:** React, Tailwind CSS, JavaScript  
**Backend:** Flask, Flask-CORS, Gunicorn  
**Database:** MySQL  
**ML Model:** XGBoost regression (trained in Google Colab)  
**Authentication:** JWT (PyJWT) + bcrypt  
**Deployment:** Netlify (frontend), Render (backend), Railway (database)  
**DevOps:** Docker containerization  
**Data Sources:** MovieLens, TMDB

---

## 📁 Project Structure

```
movie-recommender/
├── backend/
│   ├── models/
│   │   └── best_movie_recommendation_model.pkl
│   ├── app.py                  # Main Flask app + recommendation endpoints
│   ├── auth.py                 # Authentication blueprint (register/login)
│   ├── ratings.py              # Rating endpoints blueprint
│   ├── config.py               # Config with environment variable loading
│   ├── requirements.txt
│   ├── Procfile                # Gunicorn start command for Render
│   ├── runtime.txt             # Python version spec
│   ├── Dockerfile
│   └── .env                    # Local environment variables (not committed)
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthModal.jsx   # Login/Register modal
│   │   │   └── Dashboard.jsx   # Main dashboard with recommendations
│   │   ├── context/
│   │   │   └── AuthContext.jsx  # Auth state management
│   │   ├── App.js
│   │   ├── config.js           # API URL config (dev/production)
│   │   └── index.css           # Tailwind imports
│   ├── tailwind.config.js
│   └── package.json
├── data/
│   └── movies_processed.csv
├── docker-compose.yml
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- MySQL 8.0+
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/movie-recommender.git
cd movie-recommender
```

### 2. Set Up the Database

Start MySQL and create the database:

```sql
CREATE DATABASE movie_recommender;
USE movie_recommender;
```

Run the schema to create all tables:

```sql
CREATE TABLE movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    genres VARCHAR(500),
    popularity FLOAT,
    vote_average FLOAT,
    vote_count INT,
    release_year INT,
    movie_mean FLOAT
);

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    user_mean FLOAT DEFAULT 3.5,
    rating_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ratings (
    rating_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    rating FLOAT NOT NULL,
    rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    UNIQUE KEY unique_rating (user_id, movie_id)
);

CREATE TABLE watchlist (
    watchlist_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    UNIQUE KEY unique_watchlist (user_id, movie_id)
);
```

Import the movie data:

```bash
mysql -u root -p movie_recommender < data/movies_processed.csv
```

### 3. Set Up the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=movie_recommender
JWT_SECRET=your-secret-key-here
```

Make sure the trained model pickle file is in `backend/models/`:

```
backend/models/best_movie_recommendation_model.pkl
```

Start the backend:

```bash
python app.py
```

The API will be running at `http://localhost:5000`. Verify with:

```bash
curl http://localhost:5000/api/health
```

### 4. Set Up the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm start
```

The app will open at `http://localhost:3000`.

### 5. Run with Docker (Alternative)

If you prefer Docker, you can spin up the entire stack:

```bash
docker-compose up --build
```

This starts the frontend, backend, and MySQL database in containers with all environment variables pre-configured.

---

## 🔌 API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Check API status |

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/register` | No | Create new user account |
| POST | `/api/login` | No | Login and receive JWT token |

### Recommendations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/recommend` | Optional | Get movie recommendations (works for both anonymous and registered users) |
| GET | `/api/genres` | No | Get available genre list |

### Ratings

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/ratings` | Yes | Submit a movie rating |
| GET | `/api/ratings` | Yes | Get user's rating history |

### Watchlist

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/watchlist` | Yes | Add movie to watchlist |
| GET | `/api/watchlist` | Yes | Get user's watchlist |

### User

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/user/stats` | Yes | Get user statistics (rating count, avg, top genres) |

---

## 🤖 ML Model Details

The recommendation engine uses an **XGBoost regression model** trained on MovieLens and TMDB datasets.

**Training Environment:** Google Colab  
**Algorithm:** XGBoost Regressor  
**Target:** Movie rating (0.5–5.0 scale)  
**Performance:** ~0.82 RMSE on test set  
**Catalog Size:** 9,000+ movies  
**Training Time:** ~10–15 minutes (optimized from hours)

### Feature Engineering (28 Features)

The model uses a combination of user features, movie features, and genre flags:

- **User features:** `user_mean` (average rating given by the user)
- **Movie features:** `movie_mean`, `popularity`, `vote_average`, `vote_count`, `release_year` — all z-score normalized
- **Genre flags:** Binary indicators for each genre (Action, Comedy, Drama, Sci-Fi, etc.)

### How Predictions Work

1. For **anonymous users**, `user_mean` defaults to the global average (~3.5)
2. For **registered users**, `user_mean` is calculated from their actual rating history
3. Each candidate movie's features are constructed and fed through the model
4. Movies with predicted rating ≥ 4.0 are returned, sorted by predicted score

### Retraining the Model

The model can be retrained in Google Colab using the provided notebook. After training:

```python
import pickle
from google.colab import files

model_artifacts = {
    'model': best_model,
    'model_name': best_model_name,
    'feature_names': X_cols,
    'test_rmse': results[best_model_name]['test_rmse']
}

with open('best_movie_recommendation_model.pkl', 'wb') as f:
    pickle.dump(model_artifacts, f)

files.download('best_movie_recommendation_model.pkl')
```

Place the downloaded `.pkl` file in `backend/models/` and redeploy.

---

## 🌐 Deployment

The application is deployed across three cloud services:

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Netlify | `https://your-app.netlify.app` |
| Backend | Render | `https://movie-recommender-api-0sbx.onrender.com` |
| Database | Railway | MySQL instance |

### Deploying the Backend (Render)

1. Push backend code to GitHub
2. Create a new Web Service on [Render](https://render.com)
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn app:app`
6. Add environment variables: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `JWT_SECRET`

### Deploying the Database (Railway)

1. Create a new MySQL service on [Railway](https://railway.app)
2. Enable public networking to get the external connection string
3. Import your schema and movie data
4. Copy the connection details to Render's environment variables

### Deploying the Frontend (Netlify)

1. Update `frontend/src/config.js` with your Render backend URL
2. Push to GitHub
3. Create a new site on [Netlify](https://netlify.com)
4. Set base directory: `frontend`
5. Set build command: `npm run build`
6. Set publish directory: `frontend/build`

### Important: CORS Configuration

After deploying the frontend, update `app.py` to allow your Netlify domain:

```python
CORS(app, resources={r"/api/*": {
    "origins": [
        "http://localhost:3000",
        "https://your-app.netlify.app"
    ]
}}, supports_credentials=True)
```

---

## ⚠️ Version Compatibility

A critical lesson from this project: **the training environment and deployment environment must use the same package versions** for the pickle model to deserialize correctly.

### Required Versions

```
numpy==2.0.2
pandas==2.2.2
scikit-learn==1.6.1
xgboost==3.1.3
```

Check your Colab versions before deploying:

```python
import numpy, pandas, sklearn, xgboost
print(f"numpy: {numpy.__version__}")
print(f"pandas: {pandas.__version__}")
print(f"sklearn: {sklearn.__version__}")
print(f"xgboost: {xgboost.__version__}")
```

Match these exactly in `requirements.txt`.

---

## 🐳 Docker

Docker containerization ensures consistent environments between development and deployment:

```bash
# Build and run all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Stop all services
docker-compose down
```

---

## 📚 Lessons Learned

- **Version pinning is critical** — NumPy 1.x vs 2.x caused silent model loading failures in production due to changes in internal module paths (`numpy._core`)
- **Feature preprocessing must be identical** in training and inference — the model expects z-scored features, not raw values
- **Hybrid anonymous + registered UX** lowers the barrier to entry while building toward personalization
- **Pickle serialization** is environment-sensitive; always pin exact package versions between training and deployment
- **CORS configuration** requires explicit origin whitelisting when deploying frontend and backend on different domains

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 📬 Contact

**Balaji** — [GitHub]([https://github.com/YOUR_USERNAME](https://github.com/balaji2417)) · [LinkedIn]([https://linkedin.com/in/YOUR_PROFILE](https://www.linkedin.com/in/balajisundaranand/))

Built with guidance from Claude (Anthropic) across the full development lifecycle.
