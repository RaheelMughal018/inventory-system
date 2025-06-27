import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = f"mysql://root:xila9093@127.0.0.1:3306/inventory_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    LOCAL_URL = os.getenv('LOCAL_URL')