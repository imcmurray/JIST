#!/bin/bash
# GitLab Template Manager - Git Repository Checker
# Helper script to detect and analyze existing git repositories

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a directory has a git repository
check_git_repo() {
    local repo_path="$1"

    echo -e "${BLUE}Checking for existing git repository in: $repo_path${NC}"
    echo ""

    if [ ! -d "$repo_path/.git" ]; then
        echo -e "${YELLOW}No git repository found.${NC}"
        return 1
    fi

    echo -e "${GREEN}Git repository detected!${NC}"
    echo ""

    # Get git information
    cd "$repo_path" || return 1

    # Current branch
    if current_branch=$(git branch --show-current 2>/dev/null); then
        echo -e "  Current branch: ${GREEN}$current_branch${NC}"
    else
        echo -e "  Current branch: ${YELLOW}(detached HEAD or no commits)${NC}"
    fi

    # Remote information
    echo ""
    echo "  Configured remotes:"
    if git remote -v | grep -q .; then
        git remote -v | while read -r line; do
            echo -e "    ${BLUE}$line${NC}"
        done
    else
        echo -e "    ${YELLOW}No remotes configured${NC}"
    fi

    # Check for automation indicators
    echo ""
    echo "  Checking for external management indicators..."

    indicators_found=0

    # Check git hooks
    if [ -d ".git/hooks" ]; then
        hook_count=$(find .git/hooks -type f ! -name "*.sample" 2>/dev/null | wc -l)
        if [ "$hook_count" -gt 0 ]; then
            echo -e "    ${YELLOW}⚠${NC}  Found $hook_count active git hook(s)"
            find .git/hooks -type f ! -name "*.sample" -exec basename {} \; | sed 's/^/        - /'
            indicators_found=$((indicators_found + 1))
        fi
    fi

    # Check git config for automation markers
    if [ -f ".git/config" ]; then
        if grep -qi 'jenkins\|gitlab-runner\|github-actions\|ansible\|puppet\|chef\|automation' .git/config 2>/dev/null; then
            echo -e "    ${YELLOW}⚠${NC}  Found automation tool references in git config"
            indicators_found=$((indicators_found + 1))
        fi
    fi

    # Check for recent automated commits
    if git log -5 --pretty=format:'%an|%ae' 2>/dev/null | grep -qi 'bot\|automation\|jenkins\|gitlab'; then
        echo -e "    ${YELLOW}⚠${NC}  Recent commits by automation tools detected"
        indicators_found=$((indicators_found + 1))
    fi

    echo ""

    if [ $indicators_found -gt 0 ]; then
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}WARNING: This repository appears to be managed externally!${NC}"
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "Found $indicators_found indicator(s) of external management."
        echo ""
        echo "Recommended configuration:"
        echo "  MANAGE_LOCAL_GIT=False  (disable local git operations)"
        echo "  USE_EXISTING_REMOTE=True (use existing remote configuration)"
        echo ""
        echo "This will prevent conflicts with external automation while still"
        echo "allowing GitLab API operations (promote, compare branches)."
        echo ""
        return 2  # Special return code for externally managed
    else
        echo -e "${GREEN}No external management indicators found.${NC}"
        echo ""
        echo "You can safely use Template Manager's git operations."
        echo ""
        return 0
    fi
}

# Main execution
if [ $# -eq 0 ]; then
    echo "Usage: $0 <repository-path>"
    echo ""
    echo "Example: $0 /var/www/html/templates"
    exit 1
fi

check_git_repo "$1"
exit_code=$?

if [ $exit_code -eq 1 ]; then
    echo "Recommendation: Initialize a new git repository during setup."
elif [ $exit_code -eq 2 ]; then
    echo "Recommendation: Use external git management mode."
else
    echo "Recommendation: Template Manager can safely manage this repository."
fi

exit $exit_code
