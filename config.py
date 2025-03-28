import os

class Config:
    # Clave secreta para proteger sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mi_clave_secreta'
    
    # Configuración de la base de datos (MySQL)
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_HOST = 'localhost'  # O la IP de tu servidor MySQL
    MYSQL_PORT = 3306  # El puerto por defecto de MySQL
    MYSQL_DB = 'avilach'
    
    # Cadena de conexión para SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f'mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
