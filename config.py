"""
Configuration management for VideoSearchRestV2 application.
This module provides a centralized configuration class that can be shared across all files.
"""

import os
from datetime import datetime

# try:
#     from dotenv import load_dotenv
#     DOTENV_AVAILABLE = True
# except ImportError:
#     DOTENV_AVAILABLE = False
#     print("Warning: python-dotenv not available. Using environment variables directly.")


class AppConfig:
    """
    Centralized configuration class for the application.
    This class holds all global configuration variables and provides methods to initialize them.
    """
    
    def __init__(self):
        # Scene detection and embedding parameters
        self.SCENE_DETECT_THRESHOLD = 27.0
        self.FRAMES_PER_CLIP_FOR_EMBEDDING = 8
        
        # Default configuration values (will be overridden by initialize_config)
        self.BATCH_SIZE = 32
        self.WORKING_DIR = 'work_dir'
        self.OUTPUT_DIR = 'work_dir/database'
        self.USER_ID_FILE = 'work_dir/client_hardware_info.txt'
        self.LICENCE_KEY_FILE = "work_dir/licence_key.txt"
        
        # Load environment variables
        # if DOTENV_AVAILABLE:
        #     load_dotenv(dotenv_path='.env')
        
        # License-related configuration
        startdate_str = os.getenv("STARTDATE", "2025-04-10T00:00:00")
        self.STARTDATE = datetime.fromisoformat(startdate_str)
        self.PASSWORD = os.getenv("PASSWORD", "Giuy439rfhcb$uix-b312")
        self.OFFLINE_LICENSE_LIMIT_HOURS = 0
        self.MONTHLY_RENEWAL_CREDITS = 0
        self.RECENT_DATE = self.STARTDATE
        self.EXPIRYDATE = None  # Will be set by license validation
        self.removal_in_progress = False
        self.registration_in_progress = False
        self.registration_errors = []
        
        # Database configuration
        self.DATABASE_URL = ''
        
        # Status tracking
        self.indexing_status = {
            'in_progress': False,
            'current_video': '',
            'processed_videos': 0,
            'processed_audios': 0,
            'partially_processed': 0,
            'video_queue': 0,
            'scenes_processed': 0,
            'total_scenes': 0,
            'overall_scenes_processed': 0,
            'overall_total_scenes': 0,
            'start_time': 0,
            'errors': []
        }

        # Model related
        self.model = None
        self.tokenizer = None

        # Model storage
        self.loaded_db = None

        self.prevResults = None
        self.prevImageResults = None
        self.prevAudioResults = None
    
    def initialize_config(self, app):
        """
        Initialize configuration from Flask app config.
        Args:
            app: Flask application instance
        """
        self.BATCH_SIZE = app.config.get('BATCH_SIZE', 32)
        self.WORKING_DIR = app.config.get('WORKING_DIR', 'work_dir')
        os.makedirs(self.WORKING_DIR, exist_ok=True)
        self.OUTPUT_DIR = os.path.join(self.WORKING_DIR, "database")
        self.USER_ID_FILE = os.path.join(self.WORKING_DIR, 'client_hardware_info.txt')
        self.LICENCE_KEY_FILE = os.path.join(self.WORKING_DIR, 'licence_key.txt')
    
    def initialize_db_config(self, app):
        """
        Initialize database configuration from Flask app config.
        Args:
            app: Flask application instance
        """
        self.DATABASE_URL = app.config.get('DATABASE_URL', '')
    
    def get_index_files(self, db_name="_default_db"):
        """
        Get index file paths for different types.
        Args:
            db_name: Database name
        Returns:
            Dictionary with paths for video and text indices
        """
        if db_name:
            base_name = db_name.replace(".index", "")
        else:
            base_name = "_default_db"
        return {
            'video': os.path.join(self.OUTPUT_DIR, f'{base_name}_video.index'),
            'text': os.path.join(self.OUTPUT_DIR, f'{base_name}_text.index'),
            # 'audio': os.path.join(self.OUTPUT_DIR, f'{base_name}_audio.index'),
        }
    
    def is_online(self):
        """Check if the application is running in online mode."""
        return False


# Global configuration instance
config = AppConfig()


def get_config():
    """
    Get the global configuration instance.
    Returns:
        AppConfig: The global configuration instance
    """
    return config