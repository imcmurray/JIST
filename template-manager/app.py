#!/usr/bin/env python3
"""
GitLab Template Manager - Main Flask Application
Provides web UI for managing templates across environments
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from lib.git_ops import GitOperations
from lib.gitlab_ops import GitLabOperations
from lib.sync_checker import SyncChecker


# Initialize Flask app
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE) if os.access(os.path.dirname(Config.LOG_FILE), os.W_OK) else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
try:
    # Validate configuration
    config_errors = Config.validate()
    if config_errors:
        logger.error("Configuration errors:")
        for error in config_errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Initialize Git operations
    git_ops = GitOperations(
        repo_path=Config.REPO_PATH,
        backup_dir=Config.BACKUP_DIR if Config.BACKUP_ENABLED else None
    )

    # Initialize GitLab operations
    gitlab_ops = GitLabOperations(
        gitlab_url=Config.GITLAB_URL,
        private_token=Config.GITLAB_TOKEN,
        project_id=Config.GITLAB_PROJECT_ID
    )

    # Initialize sync checker
    sync_checker = SyncChecker(
        git_ops=git_ops,
        gitlab_ops=gitlab_ops,
        train_branch=Config.TRAIN_BRANCH,
        test_branch=Config.TEST_BRANCH,
        live_branch=Config.LIVE_BRANCH
    )

    logger.info(f"Template Manager initialized for {Config.SERVER_ROLE} environment")

except Exception as e:
    logger.error(f"Failed to initialize: {str(e)}")
    sys.exit(1)


@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get dashboard status
        dashboard = sync_checker.get_dashboard_status(Config.current_branch)

        # Determine which template to use based on server role
        if Config.SERVER_ROLE == 'train':
            template = 'train.html'
        else:
            template = 'deploy.html'

        return render_template(
            template,
            server_role=Config.SERVER_ROLE,
            current_branch=Config.current_branch,
            dashboard=dashboard,
            config=Config
        )

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return render_template('error.html', error=str(e)), 500


@app.route('/status')
def status():
    """Get current status as JSON"""
    try:
        dashboard = sync_checker.get_dashboard_status(Config.current_branch)
        return jsonify(dashboard)

    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/local-status')
def local_status():
    """Get local repository status"""
    try:
        status = git_ops.get_status()
        return jsonify(status)

    except Exception as e:
        logger.error(f"Local status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/diff')
def diff():
    """Get diff of current changes"""
    try:
        staged_only = request.args.get('staged', 'false').lower() == 'true'
        diff = git_ops.get_diff(staged_only=staged_only)
        return jsonify(diff)

    except Exception as e:
        logger.error(f"Diff error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/commit', methods=['POST'])
def commit():
    """Commit local changes"""
    try:
        data = request.get_json()
        message = data.get('message', '')

        if not message:
            return jsonify({'success': False, 'error': 'Commit message is required'}), 400

        # Add timestamp to commit message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"{message}\n\n[{Config.SERVER_ROLE.upper()}] {timestamp}"

        result = git_ops.commit_changes(message=full_message, add_all=True)

        if result['success']:
            logger.info(f"Committed changes: {message}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Commit error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/push', methods=['POST'])
def push():
    """Push changes to remote"""
    try:
        data = request.get_json()
        branch = data.get('branch', Config.current_branch)

        result = git_ops.push_changes(branch=branch)

        if result['success']:
            logger.info(f"Pushed changes to {branch}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Push error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/pull', methods=['POST'])
def pull():
    """Pull changes from remote"""
    try:
        data = request.get_json()
        branch = data.get('branch', Config.current_branch)

        result = git_ops.pull_changes(
            branch=branch,
            create_backup=Config.BACKUP_ENABLED
        )

        if result['success']:
            logger.info(f"Pulled changes from {branch}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Pull error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/promote', methods=['POST'])
def promote():
    """Promote train branch to test or live"""
    try:
        data = request.get_json()
        target = data.get('target', '')

        if target not in ['test', 'live']:
            return jsonify({'success': False, 'error': 'Invalid target. Must be test or live'}), 400

        # Get target branch name
        target_branch = Config.TEST_BRANCH if target == 'test' else Config.LIVE_BRANCH

        # Merge train branch into target branch
        result = gitlab_ops.merge_branches(
            source_branch=Config.TRAIN_BRANCH,
            target_branch=target_branch,
            merge_message=f"Promote from {Config.TRAIN_BRANCH} to {target_branch}"
        )

        if result['success']:
            logger.info(f"Promoted {Config.TRAIN_BRANCH} to {target_branch}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Promote error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/compare')
def compare():
    """Compare branches"""
    try:
        from_branch = request.args.get('from', Config.TRAIN_BRANCH)
        to_branch = request.args.get('to', Config.TEST_BRANCH)

        result = gitlab_ops.compare_branches(from_branch, to_branch)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Compare error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/branch-info/<branch_name>')
def branch_info(branch_name):
    """Get information about a specific branch"""
    try:
        result = gitlab_ops.get_branch_info(branch_name)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Branch info error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/sync-status')
def sync_status():
    """Get synchronization status of all branches"""
    try:
        result = sync_checker.check_all_branches()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Sync status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/local-remote-sync')
def local_remote_sync():
    """Check if local is in sync with remote"""
    try:
        result = sync_checker.check_local_vs_remote(Config.current_branch)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Local/remote sync error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/preview-changes')
def preview_changes():
    """Preview pending changes"""
    try:
        from_branch = request.args.get('from', Config.TRAIN_BRANCH)
        to_branch = request.args.get('to', Config.current_branch)
        limit = int(request.args.get('limit', 5))

        result = sync_checker.get_pending_changes_preview(from_branch, to_branch, limit)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Preview changes error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/commits/<branch_name>')
def commits(branch_name):
    """Get recent commits from a branch"""
    try:
        limit = int(request.args.get('limit', 10))
        result = gitlab_ops.get_commits(branch_name, limit)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Commits error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/project-info')
def project_info():
    """Get GitLab project information"""
    try:
        result = gitlab_ops.get_project_info()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Project info error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check GitLab connection
        gitlab_status = gitlab_ops.check_connection()

        # Check local repository
        local_status = git_ops.get_status()

        health_status = {
            'status': 'healthy' if gitlab_status['success'] and local_status['success'] else 'unhealthy',
            'gitlab': gitlab_status,
            'local_repo': local_status,
            'server_role': Config.SERVER_ROLE,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(health_status)

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {str(error)}")
    return render_template('error.html', error='Internal server error'), 500


def main():
    """Main entry point"""
    logger.info(f"Starting Template Manager on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    logger.info(f"Server role: {Config.SERVER_ROLE}")
    logger.info(f"Repository: {Config.REPO_PATH}")
    logger.info(f"Branch: {Config.current_branch}")

    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )


if __name__ == '__main__':
    main()
