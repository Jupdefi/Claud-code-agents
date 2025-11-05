#!/usr/bin/env python3
"""
Plugin Validation Script for Claude Code Agents Marketplace

Validates:
1. marketplace.json syntax and structure
2. All referenced files exist
3. YAML frontmatter in agent and skill files
4. Naming conventions (lowercase, hyphen-separated)
5. Version consistency
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# ANSI color codes for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


class ValidationError:
    def __init__(self, severity: str, message: str, file_path: str = None):
        self.severity = severity  # 'error', 'warning', 'info'
        self.message = message
        self.file_path = file_path

    def __str__(self):
        color = RED if self.severity == 'error' else YELLOW if self.severity == 'warning' else NC
        prefix = f"[{self.severity.upper()}]"
        location = f" in {self.file_path}" if self.file_path else ""
        return f"{color}{prefix}{NC}{location}: {self.message}"


class PluginValidator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.info: List[ValidationError] = []

    def add_error(self, message: str, file_path: str = None):
        self.errors.append(ValidationError('error', message, file_path))

    def add_warning(self, message: str, file_path: str = None):
        self.warnings.append(ValidationError('warning', message, file_path))

    def add_info(self, message: str, file_path: str = None):
        self.info.append(ValidationError('info', message, file_path))

    def validate_naming_convention(self, name: str, context: str) -> bool:
        """Validate lowercase, hyphen-separated naming."""
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
            self.add_error(
                f"Invalid naming convention for {context}: '{name}'. "
                f"Must be lowercase, hyphen-separated (e.g., 'my-plugin-name')"
            )
            return False
        return True

    def validate_semantic_version(self, version: str, context: str) -> bool:
        """Validate semantic versioning (x.y.z)."""
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            self.add_warning(
                f"Version '{version}' in {context} should follow semantic versioning (x.y.z)"
            )
            return False
        return True

    def validate_yaml_frontmatter(self, file_path: Path, required_fields: List[str]) -> Dict:
        """Extract and validate YAML frontmatter from markdown files."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            self.add_error(f"Cannot read file: {e}", str(file_path))
            return {}

        # Check for YAML frontmatter
        if not content.startswith('---\n'):
            self.add_error("Missing YAML frontmatter (must start with '---')", str(file_path))
            return {}

        # Extract frontmatter
        parts = content.split('---\n', 2)
        if len(parts) < 3:
            self.add_error("Invalid YAML frontmatter format", str(file_path))
            return {}

        frontmatter = {}
        try:
            # Simple YAML parsing for key: value pairs
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
        except Exception as e:
            self.add_error(f"Failed to parse YAML frontmatter: {e}", str(file_path))
            return {}

        # Validate required fields
        for field in required_fields:
            if field not in frontmatter:
                self.add_error(f"Missing required field '{field}' in YAML frontmatter", str(file_path))
            elif not frontmatter[field]:
                self.add_error(f"Empty value for required field '{field}'", str(file_path))

        return frontmatter

    def validate_agent_file(self, plugin_path: Path, agent_ref: str) -> bool:
        """Validate an agent markdown file."""
        agent_path = plugin_path / agent_ref.lstrip('./')

        if not agent_path.exists():
            self.add_error(f"Agent file not found: {agent_ref}", str(plugin_path))
            return False

        # Validate YAML frontmatter
        frontmatter = self.validate_yaml_frontmatter(
            agent_path,
            required_fields=['name', 'description', 'model']
        )

        if frontmatter:
            # Validate name matches filename
            expected_name = agent_path.stem
            if 'name' in frontmatter and frontmatter['name'] != expected_name:
                self.add_warning(
                    f"Agent name '{frontmatter['name']}' doesn't match filename '{expected_name}'",
                    str(agent_path)
                )

            # Validate naming convention
            if 'name' in frontmatter:
                self.validate_naming_convention(frontmatter['name'], f"agent name in {agent_path.name}")

            # Validate model value
            if 'model' in frontmatter:
                valid_models = ['sonnet', 'haiku']
                if frontmatter['model'] not in valid_models:
                    self.add_error(
                        f"Invalid model '{frontmatter['model']}'. Must be one of: {', '.join(valid_models)}",
                        str(agent_path)
                    )

        return True

    def validate_skill_directory(self, plugin_path: Path, skill_ref: str) -> bool:
        """Validate a skill directory and its SKILL.md file."""
        skill_path = plugin_path / skill_ref.lstrip('./')

        if not skill_path.exists():
            self.add_error(f"Skill directory not found: {skill_ref}", str(plugin_path))
            return False

        if not skill_path.is_dir():
            self.add_error(f"Skill reference must be a directory: {skill_ref}", str(plugin_path))
            return False

        # Check for SKILL.md file
        skill_md_path = skill_path / "SKILL.md"
        if not skill_md_path.exists():
            self.add_error(f"SKILL.md not found in skill directory", str(skill_path))
            return False

        # Validate YAML frontmatter
        frontmatter = self.validate_yaml_frontmatter(
            skill_md_path,
            required_fields=['name', 'description']
        )

        if frontmatter:
            # Validate name matches directory name
            expected_name = skill_path.name
            if 'name' in frontmatter and frontmatter['name'] != expected_name:
                self.add_warning(
                    f"Skill name '{frontmatter['name']}' doesn't match directory name '{expected_name}'",
                    str(skill_md_path)
                )

            # Validate naming convention
            if 'name' in frontmatter:
                self.validate_naming_convention(frontmatter['name'], f"skill name in {skill_path.name}")

        return True

    def validate_command_file(self, plugin_path: Path, command_ref: str) -> bool:
        """Validate a command markdown file."""
        command_path = plugin_path / command_ref.lstrip('./')

        if not command_path.exists():
            self.add_error(f"Command file not found: {command_ref}", str(plugin_path))
            return False

        # Commands may have YAML frontmatter but it's not strictly required
        # Just check that it's a readable file
        try:
            content = command_path.read_text(encoding='utf-8')
            if len(content.strip()) == 0:
                self.add_warning(f"Command file is empty", str(command_path))
        except Exception as e:
            self.add_error(f"Cannot read command file: {e}", str(command_path))
            return False

        return True

    def validate_plugin(self, plugin: Dict) -> bool:
        """Validate a single plugin definition."""
        plugin_name = plugin.get('name', 'UNKNOWN')

        # Validate required fields
        required_fields = ['name', 'source', 'description', 'version', 'author', 'license', 'category']
        for field in required_fields:
            if field not in plugin:
                self.add_error(f"Missing required field '{field}'", f"plugin '{plugin_name}'")

        # Validate plugin name
        if 'name' in plugin:
            self.validate_naming_convention(plugin['name'], "plugin name")

        # Validate version
        if 'version' in plugin:
            self.validate_semantic_version(plugin['version'], f"plugin '{plugin_name}'")

        # Validate plugin source directory exists
        if 'source' not in plugin:
            return False

        plugin_path = self.repo_root / plugin['source'].lstrip('./')
        if not plugin_path.exists():
            self.add_error(f"Plugin source directory not found: {plugin['source']}", f"plugin '{plugin_name}'")
            return False

        # Validate agents
        if 'agents' in plugin:
            if not isinstance(plugin['agents'], list):
                self.add_error("'agents' must be an array", f"plugin '{plugin_name}'")
            else:
                for agent_ref in plugin['agents']:
                    self.validate_agent_file(plugin_path, agent_ref)

        # Validate skills
        if 'skills' in plugin:
            if not isinstance(plugin['skills'], list):
                self.add_error("'skills' must be an array", f"plugin '{plugin_name}'")
            else:
                for skill_ref in plugin['skills']:
                    self.validate_skill_directory(plugin_path, skill_ref)

        # Validate commands
        if 'commands' in plugin:
            if not isinstance(plugin['commands'], list):
                self.add_error("'commands' must be an array", f"plugin '{plugin_name}'")
            else:
                for command_ref in plugin['commands']:
                    self.validate_command_file(plugin_path, command_ref)

        # Validate category
        valid_categories = [
            'documentation', 'development', 'workflows', 'testing', 'quality',
            'ai-ml', 'data', 'database', 'operations', 'performance',
            'infrastructure', 'security', 'languages', 'blockchain', 'finance',
            'payments', 'gaming', 'marketing', 'business', 'web3', 'embedded',
            'compliance', 'frameworks', 'shell-scripting'
        ]
        if 'category' in plugin and plugin['category'] not in valid_categories:
            self.add_warning(
                f"Unexpected category '{plugin['category']}'. Consider using one of: {', '.join(valid_categories)}",
                f"plugin '{plugin_name}'"
            )

        return True

    def validate_marketplace(self) -> bool:
        """Validate the entire marketplace.json file."""
        # Check if marketplace.json exists
        if not self.marketplace_path.exists():
            self.add_error(f"marketplace.json not found at {self.marketplace_path}")
            return False

        # Parse JSON
        try:
            with open(self.marketplace_path, 'r', encoding='utf-8') as f:
                marketplace = json.load(f)
        except json.JSONDecodeError as e:
            self.add_error(f"Invalid JSON syntax: {e}", str(self.marketplace_path))
            return False
        except Exception as e:
            self.add_error(f"Failed to read marketplace.json: {e}", str(self.marketplace_path))
            return False

        # Validate top-level structure
        required_top_level = ['name', 'owner', 'metadata', 'plugins']
        for field in required_top_level:
            if field not in marketplace:
                self.add_error(f"Missing required top-level field '{field}'", str(self.marketplace_path))

        # Validate plugins array
        if 'plugins' not in marketplace:
            self.add_error("Missing 'plugins' array", str(self.marketplace_path))
            return False

        if not isinstance(marketplace['plugins'], list):
            self.add_error("'plugins' must be an array", str(self.marketplace_path))
            return False

        # Validate each plugin
        plugin_names = set()
        for i, plugin in enumerate(marketplace['plugins']):
            if not isinstance(plugin, dict):
                self.add_error(f"Plugin at index {i} must be an object", str(self.marketplace_path))
                continue

            # Check for duplicate plugin names
            plugin_name = plugin.get('name')
            if plugin_name:
                if plugin_name in plugin_names:
                    self.add_error(f"Duplicate plugin name '{plugin_name}'", str(self.marketplace_path))
                plugin_names.add(plugin_name)

            self.validate_plugin(plugin)

        self.add_info(f"Validated {len(marketplace['plugins'])} plugins")
        return True

    def run(self) -> Tuple[int, int, int]:
        """Run all validations and return counts of errors, warnings, info."""
        print(f"🔍 Validating Claude Code Agents Marketplace...")
        print(f"Repository root: {self.repo_root}")
        print(f"Marketplace file: {self.marketplace_path}")
        print()

        self.validate_marketplace()

        # Print results
        for item in self.info:
            print(str(item))

        if self.warnings:
            print()
            for warning in self.warnings:
                print(str(warning))

        if self.errors:
            print()
            for error in self.errors:
                print(str(error))

        # Summary
        print()
        print("=" * 60)
        print(f"{GREEN}✓{NC} Passed: {len(self.info)}")
        print(f"{YELLOW}⚠{NC} Warnings: {len(self.warnings)}")
        print(f"{RED}✗{NC} Errors: {len(self.errors)}")
        print("=" * 60)

        return len(self.errors), len(self.warnings), len(self.info)


def main():
    # Determine repository root
    repo_root = Path(__file__).parent.parent.parent

    # Allow override via environment variable (useful for CI)
    if 'REPO_ROOT' in os.environ:
        repo_root = Path(os.environ['REPO_ROOT'])

    validator = PluginValidator(repo_root)
    error_count, warning_count, info_count = validator.run()

    # Exit with appropriate code
    if error_count > 0:
        print(f"\n{RED}❌ Validation failed with {error_count} error(s){NC}")
        sys.exit(1)
    elif warning_count > 0:
        print(f"\n{YELLOW}⚠️  Validation passed with {warning_count} warning(s){NC}")
        sys.exit(0)
    else:
        print(f"\n{GREEN}✅ All validations passed!{NC}")
        sys.exit(0)


if __name__ == '__main__':
    main()
