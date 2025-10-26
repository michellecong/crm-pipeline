"""
Test database connection
"""
from app.database import test_connection

if __name__ == "__main__":
    print("Testing database connection...")
    test_connection()