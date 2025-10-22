"""
Local Git operations module
Handles all local repository operations
"""

import os
import shutil
from datetime import datetime
from git import Repo, GitCommandError
from pathlib import Path


class GitOperations:
    """Handle local git repository operations"""

    def __init__(self, repo_path, backup_dir=None):
        """
        Initialize GitOperations

        Args:
            repo_path: Path to the local git repository
            backup_dir: Path to backup directory (optional)
        """
        self.repo_path = repo_path
        self.backup_dir = backup_dir

        try:
            self.repo = Repo(repo_path)
        except Exception as e:
            raise Exception(f"Failed to open repository at {repo_path}: {str(e)}")

    def get_status(self):
        """
        Get current repository status

        Returns:
            dict: Status information including branch, modified files, untracked files
        """
        try:
            # Get current branch
            current_branch = self.repo.active_branch.name

            # Get modified files
            modified_files = [item.a_path for item in self.repo.index.diff(None)]

            # Get staged files
            staged_files = [item.a_path for item in self.repo.index.diff("HEAD")]

            # Get untracked files
            untracked_files = self.repo.untracked_files

            # Check if working tree is clean
            is_clean = not (modified_files or staged_files or untracked_files)

            # Get last commit info
            last_commit = None
            if self.repo.heads:
                commit = self.repo.head.commit
                last_commit = {
                    'hash': commit.hexsha[:8],
                    'full_hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                }

            return {
                'success': True,
                'branch': current_branch,
                'modified_files': modified_files,
                'staged_files': staged_files,
                'untracked_files': untracked_files,
                'is_clean': is_clean,
                'last_commit': last_commit
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_diff(self, staged_only=False):
        """
        Get diff of current changes

        Args:
            staged_only: If True, only show staged changes

        Returns:
            dict: Diff information
        """
        try:
            if staged_only:
                diff = self.repo.index.diff("HEAD", create_patch=True)
            else:
                diff = self.repo.index.diff(None, create_patch=True)

            diff_text = ""
            for item in diff:
                diff_text += f"\n--- {item.a_path}\n"
                if item.diff:
                    diff_text += item.diff.decode('utf-8', errors='replace')

            return {
                'success': True,
                'diff': diff_text
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def commit_changes(self, message, add_all=True):
        """
        Commit local changes

        Args:
            message: Commit message
            add_all: If True, stage all modified and untracked files

        Returns:
            dict: Result of commit operation
        """
        try:
            if add_all:
                # Stage all modified and untracked files
                self.repo.git.add(A=True)

            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
                return {
                    'success': False,
                    'error': 'No changes to commit'
                }

            # Commit changes
            commit = self.repo.index.commit(message)

            return {
                'success': True,
                'commit_hash': commit.hexsha[:8],
                'message': 'Changes committed successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Commit failed: {str(e)}"
            }

    def push_changes(self, remote='origin', branch=None):
        """
        Push changes to remote repository

        Args:
            remote: Remote name (default: origin)
            branch: Branch name (default: current branch)

        Returns:
            dict: Result of push operation
        """
        try:
            if branch is None:
                branch = self.repo.active_branch.name

            # Push to remote
            origin = self.repo.remote(remote)
            push_info = origin.push(branch)

            return {
                'success': True,
                'message': f"Successfully pushed to {remote}/{branch}"
            }

        except GitCommandError as e:
            return {
                'success': False,
                'error': f"Push failed: {str(e)}"
            }

    def pull_changes(self, remote='origin', branch=None, create_backup=True):
        """
        Pull changes from remote repository

        Args:
            remote: Remote name (default: origin)
            branch: Branch name (default: current branch)
            create_backup: Create backup before pulling

        Returns:
            dict: Result of pull operation
        """
        try:
            if branch is None:
                branch = self.repo.active_branch.name

            # Create backup if enabled
            backup_path = None
            if create_backup and self.backup_dir:
                backup_path = self._create_backup()

            # Fetch from remote
            origin = self.repo.remote(remote)
            fetch_info = origin.fetch()

            # Pull changes
            pull_info = origin.pull(branch)

            return {
                'success': True,
                'message': f"Successfully pulled from {remote}/{branch}",
                'backup_path': backup_path
            }

        except GitCommandError as e:
            return {
                'success': False,
                'error': f"Pull failed: {str(e)}"
            }

    def fetch_remote(self, remote='origin'):
        """
        Fetch updates from remote without merging

        Args:
            remote: Remote name (default: origin)

        Returns:
            dict: Result of fetch operation
        """
        try:
            origin = self.repo.remote(remote)
            fetch_info = origin.fetch()

            return {
                'success': True,
                'message': f"Successfully fetched from {remote}"
            }

        except GitCommandError as e:
            return {
                'success': False,
                'error': f"Fetch failed: {str(e)}"
            }

    def get_branch_commits(self, branch, limit=10):
        """
        Get recent commits from a branch

        Args:
            branch: Branch name
            limit: Maximum number of commits to retrieve

        Returns:
            dict: List of commits
        """
        try:
            commits = []
            for commit in self.repo.iter_commits(branch, max_count=limit):
                commits.append({
                    'hash': commit.hexsha[:8],
                    'full_hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                })

            return {
                'success': True,
                'commits': commits
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def compare_with_remote(self, remote_branch):
        """
        Compare local branch with remote branch

        Args:
            remote_branch: Remote branch name (e.g., 'origin/train')

        Returns:
            dict: Comparison result
        """
        try:
            # Get local and remote commits
            local_commit = self.repo.head.commit
            remote_commit = self.repo.commit(remote_branch)

            # Check if they're the same
            if local_commit.hexsha == remote_commit.hexsha:
                return {
                    'success': True,
                    'up_to_date': True,
                    'ahead': 0,
                    'behind': 0
                }

            # Count commits ahead and behind
            ahead = list(self.repo.iter_commits(f'{remote_branch}..HEAD'))
            behind = list(self.repo.iter_commits(f'HEAD..{remote_branch}'))

            return {
                'success': True,
                'up_to_date': False,
                'ahead': len(ahead),
                'behind': len(behind),
                'local_commit': local_commit.hexsha[:8],
                'remote_commit': remote_commit.hexsha[:8]
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _create_backup(self):
        """
        Create a backup of the repository

        Returns:
            str: Path to backup
        """
        if not self.backup_dir:
            return None

        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)

        # Generate backup name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"template_backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)

        # Copy repository (excluding .git)
        shutil.copytree(
            self.repo_path,
            backup_path,
            ignore=shutil.ignore_patterns('.git')
        )

        return backup_path

    def get_remote_url(self, remote='origin'):
        """
        Get remote repository URL

        Args:
            remote: Remote name (default: origin)

        Returns:
            dict: Remote URL information
        """
        try:
            origin = self.repo.remote(remote)
            urls = list(origin.urls)

            return {
                'success': True,
                'url': urls[0] if urls else None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
