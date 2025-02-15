import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    # Basic Flask config
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # File upload config
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # API Keys and endpoints
    ARK_API_KEY = os.getenv("ARK_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    ENDPOINT_ID = os.getenv("ENDPOINT_ID", "ep-20250212181835-cb6kv")
    
    # Allowed file extensions
    ALLOWED_CODE_EXTENSIONS = {
        'py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml', 
        'md', 'txt', 'ini', 'conf', 'sh', 'bat', 'ps1'
    }
    ALLOWED_DOC_EXTENSIONS = {
        'doc', 'docx', 'pdf', 'txt', 'md', 'rtf'
    }
    ALLOWED_IMAGE_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'
    }
    
    # Rate limiting
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
