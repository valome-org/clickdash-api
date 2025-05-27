#!/usr/bin/env python3
"""
Database initialization script
Run this script to create database tables
"""

import os
import sys
from pathlib import Path

# Add the parent directory to Python path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from database import create_tables
from database.connection import engine


def init_database():
    """Initialize the database and create all tables"""
    try:
        print("Creating database tables...")
        create_tables()
        print("Database tables created successfully!")

        # Test connection
        with engine.connect() as connection:
            print("Database connection successful!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
