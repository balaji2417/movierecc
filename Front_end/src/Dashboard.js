import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './App.css';
import config from './config';

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

function Dashboard() {
  const navigate = useNavigate();
  
  // User state
  const [user, setUser] = useState(null);
  const [userStats, setUserStats] = useState({ user_mean: 3.5, rating_count: 0 });
  
  // Movies & Recommendations
  const [recommendations, setRecommendations] = useState([]);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  
  // Filters
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [minRating, setMinRating] = useState(3.5);
  const [era, setEra] = useState('any');
  
  // Available genres
  const [genres, setGenres] = useState([]);
  
  // User ratings
  const [userRatings, setUserRatings] = useState({});
  
  // Active tab
  const [activeTab, setActiveTab] = useState('recommendations');
  
  // Watchlist
  const [watchlist, setWatchlist] = useState([]);
  
  // Rating modal
  const [ratingModal, setRatingModal] = useState({ show: false, movie: null });
  const [tempRating, setTempRating] = useState(0);

  // Check auth on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      setUser(JSON.parse(userData));
      fetchUserStats();
      fetchUserRatings();
      fetchWatchlist();
    } else {
      navigate('/login');
    }
    
    fetchGenres();
  }, [navigate]);

  // Fetch genres
  const fetchGenres = async () => {
    try {
      const res = await fetch(`${config.API_URL}/api/genres`);
      const data = await res.json();
      setGenres(data.genres);
    } catch (error) {
      console.error('Failed to fetch genres:', error);
    }
  };

  // Fetch user stats
  const fetchUserStats = async () => {
    try {
      const res = await fetch(`${config.API_URL}/api/user/stats`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (res.ok) {
        setUserStats({
          user_mean: data.rating_stats.user_mean || 3.5,
          rating_count: data.rating_stats.total_ratings || 0
        });
      }
    } catch (error) {
      console.error('Failed to fetch user stats:', error);
    }
  };

  // Fetch user's ratings
  const fetchUserRatings = async () => {
    try {
      const res = await fetch(`${config.API_URL}/api/ratings`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (res.ok) {
        const ratingsMap = {};
        data.ratings.forEach(r => {
          ratingsMap[r.movie_id] = r.rating;
        });
        setUserRatings(ratingsMap);
      }
    } catch (error) {
      console.error('Failed to fetch ratings:', error);
    }
  };

  // Fetch watchlist
  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${config.API_URL}/api/watchlist`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (res.ok) {
        setWatchlist(data.watchlist);
      }
    } catch (error) {
      console.error('Failed to fetch watchlist:', error);
    }
  };

  // Get recommendations
  const fetchRecommendations = async () => {
    setIsLoadingRecs(true);
    try {
      const res = await fetch(`${config.API_URL}/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_mean: userStats.user_mean,
          genres: selectedGenres,
          min_rating: minRating,
          era: era,
          limit: 20
        })
      });
      const data = await res.json();
      if (res.ok) {
        setRecommendations(data.recommendations);
      }
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
    } finally {
      setIsLoadingRecs(false);
    }
  };

  // Rate a movie
  const rateMovie = async (movieId, rating) => {
    try {
      const res = await fetch(`${config.API_URL}/api/ratings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ movie_id: movieId, rating: rating })
      });
      const data = await res.json();
      if (res.ok) {
        setUserRatings(prev => ({ ...prev, [movieId]: rating }));
        setUserStats({
          user_mean: data.user_stats.user_mean,
          rating_count: data.user_stats.rating_count
        });
        setRatingModal({ show: false, movie: null });
      }
    } catch (error) {
      console.error('Failed to rate movie:', error);
    }
  };

  // Add to watchlist
  const addToWatchlist = async (movieId) => {
    try {
      const res = await fetch(`${config.API_URL}/api/watchlist`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ movie_id: movieId })
      });
      if (res.ok) {
        fetchWatchlist();
      }
    } catch (error) {
      console.error('Failed to add to watchlist:', error);
    }
  };

  // Toggle genre selection
  const toggleGenre = (genre) => {
    setSelectedGenres(prev =>
      prev.includes(genre)
        ? prev.filter(g => g !== genre)
        : [...prev, genre]
    );
  };

  // Logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  // Star rating component
  const StarRating = ({ rating, onRate, interactive = false }) => {
    const [hover, setHover] = useState(0);
    
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            disabled={!interactive}
            onClick={() => interactive && onRate(star)}
            onMouseEnter={() => interactive && setHover(star)}
            onMouseLeave={() => interactive && setHover(0)}
            className={`text-2xl ${interactive ? 'cursor-pointer' : 'cursor-default'}`}
          >
            <span className={
              (hover || rating) >= star
                ? 'text-yellow-400'
                : 'text-slate-600'
            }>
              ★
            </span>
          </button>
        ))}
      </div>
    );
  };

  // Movie Card component
  const MovieCard = ({ movie, showPredicted = true }) => (
    <div className="bg-slate-800/50 rounded-xl overflow-hidden border border-slate-700/50 hover:border-purple-500/50 transition-all duration-300 group">
      {/* Poster */}
      <div className="relative aspect-[2/3] bg-slate-700">
        {movie.poster_url ? (
          <img
            src={`${TMDB_IMAGE_BASE}${movie.poster_url}`}
            alt={movie.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-500">
            No Image
          </div>
        )}
        
        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-4">
          <div className="flex gap-2">
            <button
              onClick={() => {
                setTempRating(userRatings[movie.movie_id] || 0);
                setRatingModal({ show: true, movie });
              }}
              className="flex-1 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-white text-sm font-medium transition-colors"
            >
              {userRatings[movie.movie_id] ? 'Update Rating' : 'Rate'}
            </button>
            <button
              onClick={() => addToWatchlist(movie.movie_id)}
              className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      
      {/* Info */}
      <div className="p-4">
        <h3 className="text-white font-semibold truncate">{movie.title}</h3>
        <p className="text-slate-400 text-sm">{movie.release_year}</p>
        
        <div className="flex items-center justify-between mt-2">
          {showPredicted && movie.predicted_rating && (
            <span className="text-sm text-purple-400">
              Predicted: {movie.predicted_rating}★
            </span>
          )}
          {userRatings[movie.movie_id] && (
            <span className="text-sm text-yellow-400">
              Your: {userRatings[movie.movie_id]}★
            </span>
          )}
        </div>
        
        <p className="text-xs text-slate-500 mt-2 truncate">
          {movie.genres?.replace(/\|/g, ', ')}
        </p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">
            🎬 Movie Recommender
          </h1>
          
          <div className="flex items-center gap-6">
            {/* User Stats */}
            <div className="text-sm text-slate-400">
              <span className="text-purple-400 font-medium">{userStats.rating_count}</span> ratings
              {userStats.user_mean && (
                <span className="ml-3">
                  Avg: <span className="text-yellow-400">{userStats.user_mean}★</span>
                </span>
              )}
            </div>
            
            {/* User Menu */}
            <div className="flex items-center gap-3">
              <span className="text-white">{user?.name || user?.username}</span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-4 mb-8">
          {['recommendations', 'my-ratings', 'watchlist'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800/50 text-slate-400 hover:text-white'
              }`}
            >
              {tab === 'recommendations' && '🎯 Recommendations'}
              {tab === 'my-ratings' && '⭐ My Ratings'}
              {tab === 'watchlist' && '📋 Watchlist'}
            </button>
          ))}
        </div>

        {/* Recommendations Tab */}
        {activeTab === 'recommendations' && (
          <>
            {/* Filters */}
            <div className="bg-slate-800/30 rounded-2xl p-6 mb-8 border border-slate-700/50">
              <h2 className="text-lg font-semibold text-white mb-4">Find Movies</h2>
              
              {/* Genre Selection */}
              <div className="mb-4">
                <label className="block text-sm text-slate-400 mb-2">Genres</label>
                <div className="flex flex-wrap gap-2">
                  {genres.map((genre) => (
                    <button
                      key={genre}
                      onClick={() => toggleGenre(genre)}
                      className={`px-3 py-1 rounded-full text-sm transition-all ${
                        selectedGenres.includes(genre)
                          ? 'bg-purple-600 text-white'
                          : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
                      }`}
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Era & Rating */}
              <div className="flex gap-6 mb-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Era</label>
                  <select
                    value={era}
                    onChange={(e) => setEra(e.target.value)}
                    className="px-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white"
                  >
                    <option value="any">Any Era</option>
                    <option value="classic">Classic (pre-1980)</option>
                    <option value="retro">Retro (1980-1999)</option>
                    <option value="modern">Modern (2000-2015)</option>
                    <option value="recent">Recent (2016+)</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm text-slate-400 mb-2">
                    Min Predicted Rating: {minRating}★
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="0.5"
                    value={minRating}
                    onChange={(e) => setMinRating(parseFloat(e.target.value))}
                    className="w-48"
                  />
                </div>
              </div>
              
              <button
                onClick={fetchRecommendations}
                disabled={isLoadingRecs}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-lg shadow-lg transition-all"
              >
                {isLoadingRecs ? 'Finding Movies...' : '🔍 Get Recommendations'}
              </button>
            </div>
            
            {/* Results */}
            {recommendations.length > 0 && (
              <div>
                <h2 className="text-xl font-semibold text-white mb-4">
                  Recommended for You ({recommendations.length})
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
                  {recommendations.map((movie) => (
                    <MovieCard key={movie.movie_id} movie={movie} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* My Ratings Tab */}
        {activeTab === 'my-ratings' && (
          <div>
            <h2 className="text-xl font-semibold text-white mb-4">
              Your Rated Movies ({Object.keys(userRatings).length})
            </h2>
            <p className="text-slate-400 mb-6">
              Rate more movies to improve your recommendations!
            </p>
            {/* You can add a list of rated movies here */}
          </div>
        )}

        {/* Watchlist Tab */}
        {activeTab === 'watchlist' && (
          <div>
            <h2 className="text-xl font-semibold text-white mb-4">
              Your Watchlist ({watchlist.length})
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
              {watchlist.map((movie) => (
                <MovieCard key={movie.movie_id} movie={movie} showPredicted={false} />
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Rating Modal */}
      {ratingModal.show && ratingModal.movie && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-2xl p-6 max-w-md w-full mx-4 border border-slate-700">
            <h3 className="text-xl font-semibold text-white mb-2">
              Rate: {ratingModal.movie.title}
            </h3>
            <p className="text-slate-400 text-sm mb-6">
              {ratingModal.movie.release_year} • {ratingModal.movie.genres?.replace(/\|/g, ', ')}
            </p>
            
            <div className="flex justify-center mb-6">
              <StarRating
                rating={tempRating}
                onRate={setTempRating}
                interactive={true}
              />
            </div>
            
            <p className="text-center text-2xl text-white mb-6">
              {tempRating > 0 ? `${tempRating} / 5` : 'Select a rating'}
            </p>
            
            <div className="flex gap-3">
              <button
                onClick={() => setRatingModal({ show: false, movie: null })}
                className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => rateMovie(ratingModal.movie.movie_id, tempRating)}
                disabled={tempRating === 0}
                className="flex-1 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                Save Rating
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;