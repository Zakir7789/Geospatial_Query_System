# Flask App Factory & DB Connection Pool
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
import psycopg2.pool
import os
import logging
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Global Database Pool
db_pool = None

def create_app():
    app = Flask(__name__)
    
    # Configure Logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize DB Pool (Min 1, Max 10)
    global db_pool
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", "password"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "geospatial_db")
        )
        app.logger.info("Database connection pool created.")
    except Exception as e:
        app.logger.error(f"Error creating DB pool: {e}")

    # Register Routes
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Global Error Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Handle HTTP exceptions (404, 403, etc.) without logging stack traces
        if isinstance(e, HTTPException):
            return jsonify({"error": e.description}), e.code
        
        # Only log real crashes
        app.logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

    return app

def get_db_connection():
    """Helper to get a connection from the pool"""
    return db_pool.getconn()

def release_db_connection(conn):
    """Helper to return connection to pool"""
    if db_pool:
        db_pool.putconn(conn)