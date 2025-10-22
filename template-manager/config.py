"""
Configuration module for GitLab Template Manager
Load settings from environment variables or config file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration class for template manager"""

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 8080))
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Server role: 'train', 'test', or 'live'
    SERVER_ROLE = os.getenv('SERVER_ROLE', 'train').lower()

    # GitLab settings
    GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', '')
    GITLAB_PROJECT_ID = os.getenv('GITLAB_PROJECT_ID', '')

    # Repository settings
    REPO_PATH = os.getenv('REPO_PATH', '/var/www/html/templates')

    # Branch configuration
    TRAIN_BRANCH = os.getenv('TRAIN_BRANCH', 'train')
    TEST_BRANCH = os.getenv('TEST_BRANCH', 'test')
    LIVE_BRANCH = os.getenv('LIVE_BRANCH', 'live')

    # Get the branch for this server based on role
    @property
    def current_branch(self):
        """Return the branch name for current server role"""
        branch_map = {
            'train': self.TRAIN_BRANCH,
            'test': self.TEST_BRANCH,
            'live': self.LIVE_BRANCH
        }
        return branch_map.get(self.SERVER_ROLE, self.TRAIN_BRANCH)

    # Auto-termination settings (in seconds, 0 to disable)
    AUTO_TERMINATE_TIMEOUT = int(os.getenv('AUTO_TERMINATE_TIMEOUT', 3600))

    # Backup settings
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_DIR = os.getenv('BACKUP_DIR', '/var/backups/templates')

    # Logging
    LOG_FILE = os.getenv('LOG_FILE', '/var/log/template-manager.log')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.GITLAB_TOKEN:
            errors.append("GITLAB_TOKEN is required")

        if not cls.GITLAB_PROJECT_ID:
            errors.append("GITLAB_PROJECT_ID is required")

        if not os.path.exists(cls.REPO_PATH):
            errors.append(f"REPO_PATH does not exist: {cls.REPO_PATH}")

        if cls.SERVER_ROLE not in ['train', 'test', 'live']:
            errors.append(f"Invalid SERVER_ROLE: {cls.SERVER_ROLE}. Must be train, test, or live")

        return errors

    @classmethod
    def get_env_template(cls):
        """Return a template .env file content"""
        return """# GitLab Template Manager Configuration

# Server Settings
SERVER_ROLE=train  # Options: train, test, live
FLASK_PORT=8080
FLASK_HOST=0.0.0.0
DEBUG=False

# GitLab Settings
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your-gitlab-token-here
GITLAB_PROJECT_ID=your-project-id

# Repository Settings
REPO_PATH=/var/www/html/templates

# Branch Names
TRAIN_BRANCH=train
TEST_BRANCH=test
LIVE_BRANCH=live

# Auto-termination (seconds, 0 to disable)
AUTO_TERMINATE_TIMEOUT=3600

# Backup Settings
BACKUP_ENABLED=True
BACKUP_DIR=/var/backups/templates

# Logging
LOG_FILE=/var/log/template-manager.log
LOG_LEVEL=INFO

# Flask Secret Key (change in production)
SECRET_KEY=change-this-to-a-random-secret-key
"""
