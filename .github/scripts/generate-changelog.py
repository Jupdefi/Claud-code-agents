#!/usr/bin/env python3
"""
Changelog Generator for Claude Code Agents Marketplace

Generates changelog from git commits following conventional commits format:
- feat: New features
- fix: Bug fixes
- docs: Documentation changes
- chore: Maintenance tasks
- refactor: Code refactoring
- test: Test updates
- ci: CI/CD changes
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class ChangelogGenerator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def get_latest_tag(self) -> Optional[str]:
        """Get the latest git tag."""
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def get_commits_since(self, since_ref: Optional[str] = None) -> List[Dict]:
        """Get commits since a reference (tag, commit, etc)."""
        cmd = ['git', 'log', '--pretty=format:%H|%s|%an|%ae|%ad', '--date=short']

        if since_ref:
            cmd.append(f'{since_ref}..HEAD')

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'message': parts[1],
                        'author': parts[2],
                        'email': parts[3],
                        'date': parts[4]
                    })

            return commits
        except Exception as e:
            print(f"Error getting commits: {e}", file=sys.stderr)
            return []

    def parse_conventional_commit(self, message: str) -> Dict:
        """Parse conventional commit message."""
        # Pattern: type(scope)!: message
        pattern = r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$'
        match = re.match(pattern, message)

        if match:
            commit_type, scope, breaking, description = match.groups()
            return {
                'type': commit_type,
                'scope': scope,
                'breaking': breaking == '!',
                'description': description
            }
        else:
            return {
                'type': 'other',
                'scope': None,
                'breaking': False,
                'description': message
            }

    def categorize_commits(self, commits: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize commits by type."""
        categories = {
            'breaking': [],
            'feat': [],
            'fix': [],
            'docs': [],
            'refactor': [],
            'perf': [],
            'test': [],
            'ci': [],
            'chore': [],
            'other': []
        }

        for commit in commits:
            parsed = self.parse_conventional_commit(commit['message'])
            commit['parsed'] = parsed

            if parsed['breaking']:
                categories['breaking'].append(commit)
            elif parsed['type'] in categories:
                categories[parsed['type']].append(commit)
            else:
                categories['other'].append(commit)

        return categories

    def generate_markdown_changelog(
        self,
        version: str,
        commits: List[Dict],
        include_all: bool = False
    ) -> str:
        """Generate changelog in markdown format."""
        categories = self.categorize_commits(commits)

        lines = []
        lines.append(f"# Changelog - {version}")
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d')}\n")

        # Breaking changes first
        if categories['breaking']:
            lines.append("## ⚠️ BREAKING CHANGES\n")
            for commit in categories['breaking']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Features
        if categories['feat']:
            lines.append("## ✨ New Features\n")
            for commit in categories['feat']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Bug fixes
        if categories['fix']:
            lines.append("## 🐛 Bug Fixes\n")
            for commit in categories['fix']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Performance improvements
        if categories['perf']:
            lines.append("## ⚡ Performance Improvements\n")
            for commit in categories['perf']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Refactoring
        if categories['refactor']:
            lines.append("## ♻️ Code Refactoring\n")
            for commit in categories['refactor']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Documentation
        if categories['docs']:
            lines.append("## 📚 Documentation\n")
            for commit in categories['docs']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # CI/CD changes (only if include_all)
        if include_all and categories['ci']:
            lines.append("## 🔧 CI/CD\n")
            for commit in categories['ci']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Tests (only if include_all)
        if include_all and categories['test']:
            lines.append("## ✅ Tests\n")
            for commit in categories['test']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Chores (only if include_all)
        if include_all and categories['chore']:
            lines.append("## 🧹 Maintenance\n")
            for commit in categories['chore']:
                parsed = commit['parsed']
                scope_str = f"**{parsed['scope']}**: " if parsed['scope'] else ""
                lines.append(f"- {scope_str}{parsed['description']} ({commit['hash'][:7]})")
            lines.append("")

        # Other commits (only if include_all)
        if include_all and categories['other']:
            lines.append("## 📝 Other Changes\n")
            for commit in categories['other']:
                lines.append(f"- {commit['message']} ({commit['hash'][:7]})")
            lines.append("")

        # Statistics
        total_commits = len(commits)
        lines.append("---")
        lines.append(f"\n**Total commits**: {total_commits}")

        return "\n".join(lines)

    def detect_version_bump(self, commits: List[Dict]) -> str:
        """Detect what kind of version bump is needed based on commits."""
        categories = self.categorize_commits(commits)

        if categories['breaking']:
            return 'major'
        elif categories['feat']:
            return 'minor'
        elif categories['fix'] or any(categories[k] for k in ['docs', 'refactor', 'perf', 'test', 'ci', 'chore']):
            return 'patch'
        else:
            return 'none'


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate changelog from git commits')
    parser.add_argument('--since', type=str, help='Generate changelog since this ref (tag/commit)')
    parser.add_argument('--version', type=str, help='Version for changelog (default: auto-detect)')
    parser.add_argument('--output', type=str, help='Output file (default: stdout)')
    parser.add_argument('--include-all', action='store_true',
                       help='Include all commit types (CI, tests, chores)')
    parser.add_argument('--detect-bump', action='store_true',
                       help='Only output suggested version bump (major/minor/patch/none)')

    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.parent
    if 'REPO_ROOT' in os.environ:
        repo_root = Path(os.environ['REPO_ROOT'])

    generator = ChangelogGenerator(repo_root)

    # Determine since reference
    since_ref = args.since
    if not since_ref:
        since_ref = generator.get_latest_tag()
        if since_ref:
            print(f"ℹ️ Generating changelog since latest tag: {since_ref}", file=sys.stderr)
        else:
            print("ℹ️ No tags found, generating changelog for all commits", file=sys.stderr)

    # Get commits
    commits = generator.get_commits_since(since_ref)

    if not commits:
        print("ℹ️ No commits found", file=sys.stderr)
        sys.exit(0)

    # Detect version bump mode
    if args.detect_bump:
        bump_type = generator.detect_version_bump(commits)
        print(bump_type)
        sys.exit(0)

    # Determine version
    version = args.version or 'Unreleased'

    # Generate changelog
    changelog = generator.generate_markdown_changelog(version, commits, args.include_all)

    # Output
    if args.output:
        Path(args.output).write_text(changelog, encoding='utf-8')
        print(f"✅ Generated changelog: {args.output}", file=sys.stderr)
    else:
        print(changelog)


if __name__ == '__main__':
    main()
