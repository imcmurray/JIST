"""
Branch synchronization checker module
Compares branches and determines sync status
"""

from lib.git_ops import GitOperations
from lib.gitlab_ops import GitLabOperations


class SyncChecker:
    """Check synchronization status between branches"""

    def __init__(self, git_ops, gitlab_ops, train_branch, test_branch, live_branch):
        """
        Initialize SyncChecker

        Args:
            git_ops: GitOperations instance
            gitlab_ops: GitLabOperations instance
            train_branch: Train branch name
            test_branch: Test branch name
            live_branch: Live branch name
        """
        self.git_ops = git_ops
        self.gitlab_ops = gitlab_ops
        self.train_branch = train_branch
        self.test_branch = test_branch
        self.live_branch = live_branch

    def check_all_branches(self):
        """
        Check synchronization status of all branches

        Returns:
            dict: Comprehensive sync status
        """
        try:
            # Get branch information from GitLab
            train_info = self.gitlab_ops.get_branch_info(self.train_branch)
            test_info = self.gitlab_ops.get_branch_info(self.test_branch)
            live_info = self.gitlab_ops.get_branch_info(self.live_branch)

            # Check if all branches exist
            if not all([train_info['success'], test_info['success'], live_info['success']]):
                return {
                    'success': False,
                    'error': 'One or more branches not found'
                }

            # Compare branches
            train_vs_test = self.gitlab_ops.compare_branches(self.train_branch, self.test_branch)
            train_vs_live = self.gitlab_ops.compare_branches(self.train_branch, self.live_branch)
            test_vs_live = self.gitlab_ops.compare_branches(self.test_branch, self.live_branch)

            # Determine sync status
            branches_status = {
                'train': {
                    'branch': self.train_branch,
                    'commit': train_info['commit'],
                    'status': 'active'  # Train is always the source
                },
                'test': {
                    'branch': self.test_branch,
                    'commit': test_info['commit'],
                    'status': self._get_sync_status(train_vs_test),
                    'commits_behind': train_vs_test.get('commits_count', 0) if train_vs_test['success'] else None,
                    'files_different': train_vs_test.get('files_changed', 0) if train_vs_test['success'] else None
                },
                'live': {
                    'branch': self.live_branch,
                    'commit': live_info['commit'],
                    'status': self._get_sync_status(train_vs_live),
                    'commits_behind': train_vs_live.get('commits_count', 0) if train_vs_live['success'] else None,
                    'files_different': train_vs_live.get('files_changed', 0) if train_vs_live['success'] else None
                }
            }

            # Overall sync status
            all_synced = (
                branches_status['test']['status'] == 'synced' and
                branches_status['live']['status'] == 'synced'
            )

            return {
                'success': True,
                'all_synced': all_synced,
                'branches': branches_status,
                'comparisons': {
                    'train_vs_test': train_vs_test,
                    'train_vs_live': train_vs_live,
                    'test_vs_live': test_vs_live
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _get_sync_status(self, comparison):
        """
        Determine sync status from comparison

        Args:
            comparison: Comparison result from compare_branches

        Returns:
            str: Status (synced, ahead, behind, diverged)
        """
        if not comparison['success']:
            return 'error'

        commits_count = comparison.get('commits_count', 0)

        if commits_count == 0:
            return 'synced'
        else:
            return 'behind'  # In our case, target is behind source

    def check_local_vs_remote(self, branch_name):
        """
        Check if local repository is in sync with remote branch

        Args:
            branch_name: Branch name to check

        Returns:
            dict: Local vs remote sync status
        """
        try:
            # Fetch latest from remote
            fetch_result = self.git_ops.fetch_remote()

            if not fetch_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to fetch from remote: {fetch_result['error']}"
                }

            # Compare local with remote
            remote_branch = f"origin/{branch_name}"
            comparison = self.git_ops.compare_with_remote(remote_branch)

            if not comparison['success']:
                return {
                    'success': False,
                    'error': comparison['error']
                }

            # Get remote branch info from GitLab
            remote_info = self.gitlab_ops.get_branch_info(branch_name)

            if not remote_info['success']:
                return {
                    'success': False,
                    'error': f"Failed to get remote branch info: {remote_info['error']}"
                }

            # Determine status
            if comparison['up_to_date']:
                status = 'synced'
                message = 'Local repository is up to date with remote'
            elif comparison['behind'] > 0 and comparison['ahead'] == 0:
                status = 'behind'
                message = f"Local is {comparison['behind']} commit(s) behind remote"
            elif comparison['ahead'] > 0 and comparison['behind'] == 0:
                status = 'ahead'
                message = f"Local is {comparison['ahead']} commit(s) ahead of remote"
            else:
                status = 'diverged'
                message = f"Local has diverged from remote (ahead: {comparison['ahead']}, behind: {comparison['behind']})"

            return {
                'success': True,
                'status': status,
                'message': message,
                'ahead': comparison.get('ahead', 0),
                'behind': comparison.get('behind', 0),
                'local_commit': comparison.get('local_commit'),
                'remote_commit': comparison.get('remote_commit'),
                'remote_info': remote_info
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_pending_changes_preview(self, from_branch, to_branch, limit=5):
        """
        Get a preview of pending changes between branches

        Args:
            from_branch: Source branch
            to_branch: Target branch
            limit: Maximum number of commits to show

        Returns:
            dict: Preview of pending changes
        """
        try:
            # Get comparison
            comparison = self.gitlab_ops.compare_branches(from_branch, to_branch)

            if not comparison['success']:
                return {
                    'success': False,
                    'error': comparison['error']
                }

            # Limit commits for preview
            commits = comparison['commits'][:limit]
            total_commits = comparison['commits_count']

            # Get summary of file changes
            file_changes = {
                'added': [],
                'modified': [],
                'deleted': []
            }

            for diff in comparison['diffs']:
                if diff['new_file']:
                    file_changes['added'].append(diff['new_path'])
                elif diff['deleted_file']:
                    file_changes['deleted'].append(diff['old_path'])
                else:
                    file_changes['modified'].append(diff['new_path'])

            return {
                'success': True,
                'commits': commits,
                'total_commits': total_commits,
                'showing_limited': total_commits > limit,
                'file_changes': file_changes,
                'files_changed': comparison['files_changed']
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_dashboard_status(self, current_branch):
        """
        Get comprehensive dashboard status

        Args:
            current_branch: Current server's branch

        Returns:
            dict: Dashboard status information
        """
        try:
            # Get local repository status
            local_status = self.git_ops.get_status()

            # Get local vs remote sync status
            local_remote_sync = self.check_local_vs_remote(current_branch)

            # Get all branches sync status
            all_branches_sync = self.check_all_branches()

            # Get GitLab connection status
            gitlab_connection = self.gitlab_ops.check_connection()

            return {
                'success': True,
                'local_status': local_status,
                'local_remote_sync': local_remote_sync,
                'all_branches_sync': all_branches_sync,
                'gitlab_connection': gitlab_connection,
                'current_branch': current_branch
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
