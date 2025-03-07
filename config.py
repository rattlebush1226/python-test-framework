import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'test_framework.db')
SECRET_KEY = 'your-secret-key-here'
SCHEDULER_API_ENABLED = False