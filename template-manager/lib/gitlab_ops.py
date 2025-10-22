"""
GitLab API operations module
Handles all interactions with GitLab API
"""

import gitlab
from datetime import datetime


class GitLabOperations:
    """Handle GitLab API operations"""

    def __init__(self, gitlab_url, private_token, project_id):
        """
        Initialize GitLab Operations

        Args:
            gitlab_url: GitLab instance URL
            private_token: GitLab API token
            project_id: GitLab project ID
        """
        self.gitlab_url = gitlab_url
        self.project_id = project_id

        try:
            self.gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
            self.gl.auth()
            self.project = self.gl.projects.get(project_id)
        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise Exception(f"GitLab authentication failed: {str(e)}")
        except gitlab.exceptions.GitlabGetError as e:
            raise Exception(f"Failed to get project {project_id}: {str(e)}")
        except Exception as e:
            raise Exception(f"GitLab initialization failed: {str(e)}")

    def get_branch_info(self, branch_name):
        """
        Get information about a branch

        Args:
            branch_name: Name of the branch

        Returns:
            dict: Branch information
        """
        try:
            branch = self.project.branches.get(branch_name)

            return {
                'success': True,
                'name': branch.name,
                'commit': {
                    'id': branch.commit['id'][:8],
                    'full_id': branch.commit['id'],
                    'message': branch.commit['message'].strip(),
                    'author_name': branch.commit.get('author_name', 'Unknown'),
                    'created_at': branch.commit.get('created_at', 'Unknown')
                },
                'protected': branch.protected
            }

        except gitlab.exceptions.GitlabGetError:
            return {
                'success': False,
                'error': f"Branch '{branch_name}' not found"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def compare_branches(self, from_branch, to_branch):
        """
        Compare two branches

        Args:
            from_branch: Source branch name
            to_branch: Target branch name

        Returns:
            dict: Comparison results including commits and diffs
        """
        try:
            # Get comparison
            comparison = self.project.repository_compare(from_branch, to_branch)

            # Format commits
            commits = []
            for commit in comparison['commits']:
                commits.append({
                    'id': commit['id'][:8],
                    'full_id': commit['id'],
                    'message': commit['message'].strip(),
                    'author_name': commit.get('author_name', 'Unknown'),
                    'created_at': commit.get('created_at', 'Unknown')
                })

            # Format diffs
            diffs = []
            for diff in comparison['diffs']:
                diffs.append({
                    'old_path': diff['old_path'],
                    'new_path': diff['new_path'],
                    'new_file': diff['new_file'],
                    'renamed_file': diff['renamed_file'],
                    'deleted_file': diff['deleted_file'],
                    'diff': diff.get('diff', '')
                })

            return {
                'success': True,
                'commits': commits,
                'diffs': diffs,
                'commits_count': len(commits),
                'files_changed': len(diffs)
            }

        except gitlab.exceptions.GitlabGetError as e:
            return {
                'success': False,
                'error': f"Comparison failed: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def merge_branches(self, source_branch, target_branch, merge_message=None):
        """
        Merge source branch into target branch

        Args:
            source_branch: Source branch to merge from
            target_branch: Target branch to merge into
            merge_message: Optional merge commit message

        Returns:
            dict: Merge result
        """
        try:
            # Create merge request
            if merge_message is None:
                merge_message = f"Merge {source_branch} into {target_branch}"

            # Check if branches are different
            comparison = self.compare_branches(source_branch, target_branch)
            if comparison['success'] and comparison['commits_count'] == 0:
                return {
                    'success': True,
                    'message': 'Branches are already in sync, no merge needed',
                    'already_synced': True
                }

            # Create merge request
            mr = self.project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': merge_message,
                'remove_source_branch': False
            })

            # Auto-merge if possible
            if mr.merge_status == 'can_be_merged':
                mr.merge()

                return {
                    'success': True,
                    'message': f"Successfully merged {source_branch} into {target_branch}",
                    'merge_request_id': mr.iid
                }
            else:
                return {
                    'success': False,
                    'error': f"Merge conflict detected. Merge request #{mr.iid} created but requires manual resolution",
                    'merge_request_id': mr.iid,
                    'merge_status': mr.merge_status
                }

        except gitlab.exceptions.GitlabCreateError as e:
            return {
                'success': False,
                'error': f"Failed to create merge request: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Merge failed: {str(e)}"
            }

    def get_commits(self, branch_name, limit=10):
        """
        Get recent commits from a branch

        Args:
            branch_name: Branch name
            limit: Maximum number of commits to retrieve

        Returns:
            dict: List of commits
        """
        try:
            commits = self.project.commits.list(ref_name=branch_name, per_page=limit)

            commit_list = []
            for commit in commits:
                commit_list.append({
                    'id': commit.id[:8],
                    'full_id': commit.id,
                    'message': commit.message.strip(),
                    'author_name': commit.author_name,
                    'created_at': commit.created_at
                })

            return {
                'success': True,
                'commits': commit_list
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_file_content(self, file_path, branch_name):
        """
        Get content of a file from a specific branch

        Args:
            file_path: Path to the file in repository
            branch_name: Branch name

        Returns:
            dict: File content
        """
        try:
            file_content = self.project.files.get(
                file_path=file_path,
                ref=branch_name
            )

            return {
                'success': True,
                'content': file_content.decode().decode('utf-8'),
                'file_path': file_path,
                'branch': branch_name
            }

        except gitlab.exceptions.GitlabGetError:
            return {
                'success': False,
                'error': f"File '{file_path}' not found in branch '{branch_name}'"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_branches(self):
        """
        List all branches in the project

        Returns:
            dict: List of branches
        """
        try:
            branches = self.project.branches.list(all=True)

            branch_list = []
            for branch in branches:
                branch_list.append({
                    'name': branch.name,
                    'commit_id': branch.commit['id'][:8],
                    'protected': branch.protected
                })

            return {
                'success': True,
                'branches': branch_list
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_project_info(self):
        """
        Get project information

        Returns:
            dict: Project information
        """
        try:
            return {
                'success': True,
                'name': self.project.name,
                'description': self.project.description,
                'web_url': self.project.web_url,
                'default_branch': self.project.default_branch,
                'created_at': self.project.created_at
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def check_connection(self):
        """
        Check if connection to GitLab is working

        Returns:
            dict: Connection status
        """
        try:
            user = self.gl.user
            return {
                'success': True,
                'connected': True,
                'user': user.username,
                'gitlab_url': self.gitlab_url
            }

        except Exception as e:
            return {
                'success': False,
                'connected': False,
                'error': str(e)
            }

    def get_merge_requests(self, state='opened', limit=10):
        """
        Get merge requests for the project

        Args:
            state: State of merge requests (opened, closed, merged, all)
            limit: Maximum number of merge requests to retrieve

        Returns:
            dict: List of merge requests
        """
        try:
            mrs = self.project.mergerequests.list(state=state, per_page=limit)

            mr_list = []
            for mr in mrs:
                mr_list.append({
                    'iid': mr.iid,
                    'title': mr.title,
                    'state': mr.state,
                    'source_branch': mr.source_branch,
                    'target_branch': mr.target_branch,
                    'author': mr.author.get('name', 'Unknown'),
                    'created_at': mr.created_at,
                    'web_url': mr.web_url
                })

            return {
                'success': True,
                'merge_requests': mr_list
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
