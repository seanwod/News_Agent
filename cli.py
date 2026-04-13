#!/usr/bin/env python3
"""CLI for the News Agent."""

from urllib.parse import urlparse

import click
import yaml

import agent


@click.group()
def cli():
    """News Agent - Daily morning digest from monitored websites."""


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show per-article progress.")
def run(verbose):
    """Fetch latest news and write summaries to Notion."""
    click.echo("Running News Agent...")
    results = agent.run(verbose=verbose)
    click.echo(f"\nDone. Added {len(results)} new article(s) to Notion.")


@cli.group()
def sites():
    """Add, remove, or list monitored websites."""


@sites.command(name="list")
def sites_list():
    """List all configured sites."""
    config = agent.load_config()
    site_list = config.get("sites", [])
    if not site_list:
        click.echo("No sites configured.")
        return
    click.echo(f"Monitored sites ({len(site_list)}):")
    for s in site_list:
        rss = f"  RSS: {s['rss_url']}" if s.get("rss_url") else "  (HTML scrape)"
        click.echo(f"  • {s['name']}: {s['url']}{rss}")


@sites.command(name="add")
@click.argument("name")
@click.argument("url")
@click.option("--rss", default=None, help="RSS feed URL (if available).")
@click.option("--label", default=None, help="Notion Site label (defaults to NAME).")
def sites_add(name, url, rss, label):
    """Add NAME and URL to the monitored sites list."""
    config = agent.load_config()
    for s in config.get("sites", []):
        if s["name"].lower() == name.lower():
            click.echo(f"ERROR: site '{name}' already exists.", err=True)
            raise SystemExit(1)

    new_site: dict = {
        "name": name,
        "url": url,
        "rss_url": rss,
        "notion_label": label or name,
    }
    if not rss:
        parsed = urlparse(url)
        new_site["scrape"] = {
            "articles_selector": "a",
            "base_url": f"{parsed.scheme}://{parsed.netloc}",
        }

    config.setdefault("sites", []).append(new_site)
    with open(agent.CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    click.echo(f"Added '{name}' ({url})")
    if label and label not in {"Anthropic", "OpenAI", "Google DeepMind", "Other"}:
        click.echo(
            f"Tip: '{label}' will be auto-created as a new Site option in your Notion database."
        )


@sites.command(name="remove")
@click.argument("name")
def sites_remove(name):
    """Remove a site from monitoring by NAME."""
    config = agent.load_config()
    original = config.get("sites", [])
    config["sites"] = [s for s in original if s["name"].lower() != name.lower()]

    if len(config["sites"]) == len(original):
        click.echo(f"ERROR: site '{name}' not found.", err=True)
        raise SystemExit(1)

    with open(agent.CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    click.echo(f"Removed '{name}'.")


if __name__ == "__main__":
    cli()
