import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database configuration
    DB_SERVER = os.getenv('DB_SERVER', '192.168.151.20')
    DB_DATABASE = os.getenv('DB_DATABASE', 'hkdb_data_bkp')
    DB_USERNAME = os.getenv('DB_USERNAME', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_DRIVER = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', '06a6b9650ed4735af56c5c9df216c3e20d52317e9b2a1883c9000f0a19d37f21')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
