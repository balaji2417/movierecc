from flask import Blueprint, request, jsonify
from auth import token_required

ratings_bp = Blueprint('ratings', __name__)


def get_db():
    from app import get_db as app_get_db
    return app_get_db()


# =============================================================================
# RATE A MOVIE
# =============================================================================

@ratings_bp.route('/api/ratings', methods=['POST'])
@token_required
def rate_movie():
    """
    Rate a movie (creates or updates rating).

    Request body:
    {
        "movie_id": 862,
        "rating": 4.5
    }
    """
    user_id = request.current_user['user_id']
    data = request.json

    movie_id = data.get('movie_id')
    rating = data.get('rating')

    # Validate
    if not movie_id:
        return jsonify({'error': 'movie_id is required'}), 400

    if rating is None:
        return jsonify({'error': 'rating is required'}), 400

    try:
        rating = float(rating)
        if rating < 0.5 or rating > 5.0:
            return jsonify({'error': 'Rating must be between 0.5 and 5.0'}), 400
        # Round to nearest 0.5
        rating = round(rating * 2) / 2
    except ValueError:
        return jsonify({'error': 'Invalid rating value'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if movie exists
        cursor.execute("SELECT movie_id FROM movies WHERE movie_id = %s", (movie_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Movie not found'}), 404

        # Insert or update rating
        cursor.execute("""
            INSERT INTO ratings (user_id, movie_id, rating, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE rating = %s, updated_at = NOW()
        """, (user_id, movie_id, rating, rating))

        conn.commit()

        # Get updated user stats (trigger should update this, but let's fetch it)
        cursor.execute("""
            SELECT AVG(rating) as user_mean, COUNT(*) as rating_count
            FROM ratings WHERE user_id = %s
        """, (user_id,))
        stats = cursor.fetchone()

        return jsonify({
            'message': 'Rating saved successfully',
            'rating': {
                'movie_id': movie_id,
                'rating': rating
            },
            'user_stats': {
                'user_mean': round(float(stats['user_mean']), 2) if stats['user_mean'] else 3.5,
                'rating_count': stats['rating_count']
            }
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Failed to save rating: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# GET USER'S RATINGS
# =============================================================================

@ratings_bp.route('/api/ratings', methods=['GET'])
@token_required
def get_user_ratings():
    """Get all ratings by current user."""
    user_id = request.current_user['user_id']

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT r.movie_id, r.rating, r.created_at, r.updated_at,
                   m.title, m.genres, m.poster_url, m.release_year
            FROM ratings r
            JOIN movies m ON r.movie_id = m.movie_id
            WHERE r.user_id = %s
            ORDER BY r.updated_at DESC
        """, (user_id,))

        ratings = cursor.fetchall()

        # Get user stats
        cursor.execute("""
            SELECT AVG(rating) as user_mean, COUNT(*) as rating_count
            FROM ratings WHERE user_id = %s
        """, (user_id,))
        stats = cursor.fetchone()

        return jsonify({
            'ratings': ratings,
            'count': len(ratings),
            'user_mean': round(float(stats['user_mean']), 2) if stats['user_mean'] else None,
            'rating_count': stats['rating_count']
        })

    finally:
        cursor.close()
        conn.close()


# =============================================================================
# DELETE A RATING
# =============================================================================

@ratings_bp.route('/api/ratings/<int:movie_id>', methods=['DELETE'])
@token_required
def delete_rating(movie_id):
    """Delete a rating."""
    user_id = request.current_user['user_id']

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM ratings WHERE user_id = %s AND movie_id = %s
        """, (user_id, movie_id))

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Rating not found'}), 404

        return jsonify({'message': 'Rating deleted successfully'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Failed to delete rating: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# GET USER STATS
# =============================================================================

@ratings_bp.route('/api/user/stats', methods=['GET'])
@token_required
def get_user_stats():
    """Get current user's statistics."""
    user_id = request.current_user['user_id']

    conn = None  # Initialize to None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get rating stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_ratings,
                AVG(rating) as user_mean,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating
            FROM ratings WHERE user_id = %s
        """, (user_id,))
        rating_stats = cursor.fetchone()

        # Get watchlist count
        cursor.execute("""
            SELECT COUNT(*) as watchlist_count FROM watchlist WHERE user_id = %s
        """, (user_id,))
        watchlist = cursor.fetchone()

        return jsonify({
            'rating_stats': {
                'total_ratings': rating_stats['total_ratings'] or 0,
                'user_mean': round(float(rating_stats['user_mean']), 2) if rating_stats['user_mean'] else None,
                'min_rating': float(rating_stats['min_rating']) if rating_stats['min_rating'] else None,
                'max_rating': float(rating_stats['max_rating']) if rating_stats['max_rating'] else None
            },
            'watchlist_count': watchlist['watchlist_count'] or 0
        })

    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()  # Always close, even on error

# =============================================================================
# WATCHLIST
# =============================================================================

@ratings_bp.route('/api/watchlist', methods=['GET'])
@token_required
def get_watchlist():
    """Get user's watchlist."""
    user_id = request.current_user['user_id']

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT w.movie_id, w.added_at,
                   m.title, m.genres, m.poster_url, m.release_year, 
                   m.vote_average, m.popularity
            FROM watchlist w
            JOIN movies m ON w.movie_id = m.movie_id
            WHERE w.user_id = %s
            ORDER BY w.added_at DESC
        """, (user_id,))

        watchlist = cursor.fetchall()

        return jsonify({
            'watchlist': watchlist,
            'count': len(watchlist)
        })

    finally:
        cursor.close()
        conn.close()


@ratings_bp.route('/api/watchlist', methods=['POST'])
@token_required
def add_to_watchlist():
    """Add movie to watchlist."""
    user_id = request.current_user['user_id']
    data = request.json
    movie_id = data.get('movie_id')

    if not movie_id:
        return jsonify({'error': 'movie_id is required'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT IGNORE INTO watchlist (user_id, movie_id, added_at)
            VALUES (%s, %s, NOW())
        """, (user_id, movie_id))

        conn.commit()

        return jsonify({'message': 'Added to watchlist'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Failed to add to watchlist: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


@ratings_bp.route('/api/watchlist/<int:movie_id>', methods=['DELETE'])
@token_required
def remove_from_watchlist(movie_id):
    """Remove movie from watchlist."""
    user_id = request.current_user['user_id']

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM watchlist WHERE user_id = %s AND movie_id = %s
        """, (user_id, movie_id))

        conn.commit()

        return jsonify({'message': 'Removed from watchlist'})

    finally:
        cursor.close()
        conn.close()