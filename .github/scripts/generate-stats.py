#!/usr/bin/env python3
"""
Documentation Statistics Generator for Claude Code Agents Marketplace

Generates statistics and metadata from marketplace.json for documentation updates:
- Plugin counts by category
- Agent counts and distribution
- Skill counts per plugin
- Command/tool counts
- Model distribution (Sonnet vs Haiku)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


class StatsGenerator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
        self.marketplace = None

    def load_marketplace(self) -> bool:
        """Load and parse marketplace.json."""
        try:
            with open(self.marketplace_path, 'r', encoding='utf-8') as f:
                self.marketplace = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading marketplace.json: {e}", file=sys.stderr)
            return False

    def count_agents_by_model(self) -> Dict[str, int]:
        """Count agents by model type (sonnet/haiku)."""
        model_counts = defaultdict(int)

        for plugin in self.marketplace.get('plugins', []):
            plugin_path = self.repo_root / plugin['source'].lstrip('./')

            for agent_ref in plugin.get('agents', []):
                agent_path = plugin_path / agent_ref.lstrip('./')

                try:
                    content = agent_path.read_text(encoding='utf-8')
                    # Extract model from YAML frontmatter
                    if content.startswith('---\n'):
                        parts = content.split('---\n', 2)
                        if len(parts) >= 2:
                            for line in parts[1].strip().split('\n'):
                                if line.startswith('model:'):
                                    model = line.split(':', 1)[1].strip()
                                    model_counts[model] += 1
                                    break
                except Exception:
                    pass

        return dict(model_counts)

    def count_by_category(self) -> Dict[str, Dict]:
        """Count plugins, agents, skills, and commands by category."""
        categories = defaultdict(lambda: {
            'plugins': [],
            'agent_count': 0,
            'skill_count': 0,
            'command_count': 0
        })

        for plugin in self.marketplace.get('plugins', []):
            category = plugin.get('category', 'uncategorized')
            plugin_name = plugin.get('name', 'unknown')

            categories[category]['plugins'].append(plugin_name)
            categories[category]['agent_count'] += len(plugin.get('agents', []))
            categories[category]['skill_count'] += len(plugin.get('skills', []))
            categories[category]['command_count'] += len(plugin.get('commands', []))

        return dict(categories)

    def generate_stats(self) -> Dict:
        """Generate comprehensive statistics."""
        if not self.marketplace:
            if not self.load_marketplace():
                return {}

        plugins = self.marketplace.get('plugins', [])

        # Count totals
        total_plugins = len(plugins)
        total_agents = sum(len(p.get('agents', [])) for p in plugins)
        total_skills = sum(len(p.get('skills', [])) for p in plugins)
        total_commands = sum(len(p.get('commands', [])) for p in plugins)

        # Count by category
        categories = self.count_by_category()

        # Count agents by model
        model_distribution = self.count_agents_by_model()

        # Find plugins with most components
        plugin_components = []
        for plugin in plugins:
            components = (
                len(plugin.get('agents', [])) +
                len(plugin.get('skills', [])) +
                len(plugin.get('commands', []))
            )
            plugin_components.append({
                'name': plugin.get('name'),
                'components': components,
                'agents': len(plugin.get('agents', [])),
                'skills': len(plugin.get('skills', [])),
                'commands': len(plugin.get('commands', []))
            })

        plugin_components.sort(key=lambda x: x['components'], reverse=True)

        stats = {
            'totals': {
                'plugins': total_plugins,
                'agents': total_agents,
                'skills': total_skills,
                'commands': total_commands,
                'categories': len(categories)
            },
            'model_distribution': model_distribution,
            'categories': categories,
            'top_plugins': plugin_components[:10],
            'average_components_per_plugin': round(
                (total_agents + total_skills + total_commands) / total_plugins, 1
            ) if total_plugins > 0 else 0
        }

        return stats

    def generate_markdown_summary(self) -> str:
        """Generate a markdown summary of statistics."""
        stats = self.generate_stats()

        if not stats:
            return "Error: Could not generate statistics"

        md = ["# Claude Code Agents Marketplace Statistics\n"]

        # Totals
        md.append("## Overview\n")
        md.append(f"- **Total Plugins**: {stats['totals']['plugins']}")
        md.append(f"- **Total Agents**: {stats['totals']['agents']}")
        md.append(f"- **Total Skills**: {stats['totals']['skills']}")
        md.append(f"- **Total Commands**: {stats['totals']['commands']}")
        md.append(f"- **Categories**: {stats['totals']['categories']}")
        md.append(f"- **Average Components per Plugin**: {stats['average_components_per_plugin']}\n")

        # Model Distribution
        if stats['model_distribution']:
            md.append("## Agent Model Distribution\n")
            for model, count in sorted(stats['model_distribution'].items()):
                md.append(f"- **{model.title()}**: {count} agents")
            md.append("")

        # Categories
        md.append("## Plugins by Category\n")
        for category, data in sorted(stats['categories'].items()):
            plugin_count = len(data['plugins'])
            md.append(f"### {category.title()} ({plugin_count} plugins)")
            md.append(f"- Agents: {data['agent_count']}")
            md.append(f"- Skills: {data['skill_count']}")
            md.append(f"- Commands: {data['command_count']}")
            md.append("")

        # Top Plugins
        md.append("## Top Plugins by Component Count\n")
        for i, plugin in enumerate(stats['top_plugins'], 1):
            md.append(
                f"{i}. **{plugin['name']}**: {plugin['components']} components "
                f"({plugin['agents']} agents, {plugin['skills']} skills, "
                f"{plugin['commands']} commands)"
            )

        return "\n".join(md)

    def generate_json_stats(self) -> str:
        """Generate statistics as JSON."""
        stats = self.generate_stats()
        return json.dumps(stats, indent=2)

    def update_readme_badges(self, readme_path: Path) -> bool:
        """Update badge values in README.md."""
        stats = self.generate_stats()

        if not stats or not readme_path.exists():
            return False

        try:
            content = readme_path.read_text(encoding='utf-8')

            # Update count mentions in the overview section
            # This is a simple replacement - could be made more sophisticated
            totals = stats['totals']

            # Look for patterns like "85 specialized AI agents" and update
            import re

            # Update agent count
            content = re.sub(
                r'\*\*\d+ Specialized Agents\*\*',
                f"**{totals['agents']} Specialized Agents**",
                content
            )

            # Update plugin count
            content = re.sub(
                r'\*\*\d+ Focused Plugins\*\*',
                f"**{totals['plugins']} Focused Plugins**",
                content
            )

            # Update skill count
            content = re.sub(
                r'\*\*\d+ Agent Skills\*\*',
                f"**{totals['skills']} Agent Skills**",
                content
            )

            # Update command count
            content = re.sub(
                r'\*\*\d+ Development Tools\*\*',
                f"**{totals['commands']} Development Tools**",
                content
            )

            # Update in first paragraph
            content = re.sub(
                r'combining \*\*\d+ specialized AI agents\*\*',
                f"combining **{totals['agents']} specialized AI agents**",
                content
            )

            content = re.sub(
                r'\*\*\d+ agent skills\*\*',
                f"**{totals['skills']} agent skills**",
                content
            )

            content = re.sub(
                r'\*\*\d+ development tools\*\*',
                f"**{totals['commands']} development tools**",
                content
            )

            content = re.sub(
                r'into \*\*\d+ focused, single-purpose plugins\*\*',
                f"into **{totals['plugins']} focused, single-purpose plugins**",
                content
            )

            readme_path.write_text(content, encoding='utf-8')
            return True

        except Exception as e:
            print(f"Error updating README: {e}", file=sys.stderr)
            return False


def main():
    repo_root = Path(__file__).parent.parent.parent

    if 'REPO_ROOT' in os.environ:
        repo_root = Path(os.environ['REPO_ROOT'])

    generator = StatsGenerator(repo_root)

    import argparse
    parser = argparse.ArgumentParser(description='Generate marketplace statistics')
    parser.add_argument('--format', choices=['json', 'markdown'], default='markdown',
                       help='Output format')
    parser.add_argument('--update-readme', action='store_true',
                       help='Update README.md with current statistics')
    parser.add_argument('--output', type=str,
                       help='Output file (default: stdout)')

    args = parser.parse_args()

    if args.update_readme:
        readme_path = repo_root / "README.md"
        if generator.update_readme_badges(readme_path):
            print(f"✅ Updated {readme_path}")
        else:
            print(f"❌ Failed to update {readme_path}", file=sys.stderr)
            sys.exit(1)

    # Generate output
    if args.format == 'json':
        output = generator.generate_json_stats()
    else:
        output = generator.generate_markdown_summary()

    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"✅ Generated {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    import os
    main()
