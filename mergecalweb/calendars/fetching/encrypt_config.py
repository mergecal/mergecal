#!/usr/bin/env python
"""
Helper script to encrypt domain configurations.

Usage:
    python encrypt_config.py create  # Interactive mode to create new config
    python encrypt_config.py list    # List all existing encrypted configs

This script will prompt for domain configuration details and output
an encrypted string that can be added to ENCRYPTED_CONFIGS in
domain_configs.py.

The encryption key will be read from the CALENDAR_CONFIG_KEY environment
variable. If not set, a new key will be generated.
"""

import json
import os
import re
from pathlib import Path

import typer
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from rich.console import Console
from rich.prompt import Confirm
from rich.prompt import Prompt
from rich.table import Table

app = typer.Typer(help="Manage encrypted calendar domain configurations")
console = Console()


def generate_key() -> bytes:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key()


def get_or_create_key() -> bytes:
    """Get encryption key from environment or generate a new one."""
    key = os.environ.get("CALENDAR_CONFIG_KEY")
    if key:
        console.print("[green]Using CALENDAR_CONFIG_KEY from environment[/green]")
        return key.encode()

    console.print("\n[yellow]⚠️  CALENDAR_CONFIG_KEY not found in environment[/yellow]")
    if Confirm.ask("Generate a new key?"):
        new_key = generate_key()
        console.print("\n[bold cyan]NEW ENCRYPTION KEY GENERATED[/bold cyan]")
        console.print("\nAdd this to your .env file:")
        console.print(f"\n[green]CALENDAR_CONFIG_KEY={new_key.decode()}[/green]\n")
        console.print(
            "[yellow]⚠️  IMPORTANT: Save this key securely! "
            "You'll need it to decrypt configs.[/yellow]\n",
        )
        return new_key

    console.print("[red]Cannot proceed without encryption key[/red]")
    raise typer.Exit(1)


def encrypt_config(config: dict, key: bytes) -> str:
    """Encrypt a configuration dictionary."""
    fernet = Fernet(key)
    json_data = json.dumps(config, separators=(",", ":"))
    encrypted = fernet.encrypt(json_data.encode())
    return encrypted.decode()


def decrypt_config(encrypted_blob: str, key: bytes) -> dict | None:
    """Decrypt a configuration string."""
    try:
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_blob.encode())
        return json.loads(decrypted_data)
    except (InvalidToken, json.JSONDecodeError):
        return None


@app.command()
def list_configs():
    """List all existing encrypted domain configurations."""
    # Read ENCRYPTED_CONFIGS from domain_configs.py file directly
    script_dir = Path(__file__).parent
    config_file = script_dir / "domain_configs.py"

    if not config_file.exists():
        console.print(f"[red]❌ Error: {config_file} not found[/red]")
        raise typer.Exit(1)

    content = config_file.read_text()

    # Extract ENCRYPTED_CONFIGS list
    match = re.search(
        r"ENCRYPTED_CONFIGS:\s*list\[str\]\s*=\s*\[(.*?)\]",
        content,
        re.DOTALL,
    )
    if not match:
        console.print(
            "[yellow]No ENCRYPTED_CONFIGS found in domain_configs.py[/yellow]",
        )
        return

    # Parse encrypted strings
    config_strings = re.findall(r'"([^"]+)"', match.group(1))

    if not config_strings:
        console.print(
            "[yellow]No encrypted configs found in ENCRYPTED_CONFIGS[/yellow]",
        )
        return

    key = os.environ.get("CALENDAR_CONFIG_KEY")
    if not key:
        console.print("[red]❌ Error: CALENDAR_CONFIG_KEY not set in environment[/red]")
        console.print("Cannot decrypt configs without the key.")
        raise typer.Exit(1)

    # Create table
    table = Table(
        title=f"Encrypted Domain Configurations ({len(config_strings)} total)",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Domain", style="cyan bold")
    table.add_column("User-Agent", style="green")
    table.add_column("Accept", style="magenta")
    table.add_column("Notes", style="yellow")

    ua_max_length = 50
    for i, encrypted_blob in enumerate(config_strings):
        config = decrypt_config(encrypted_blob, key.encode())
        if config:
            domain = config.pop("domain", "unknown")
            ua = config.get("user_agent", "-")
            ua_preview = (ua[:ua_max_length] + "...") if len(ua) > ua_max_length else ua
            accept_header = config.get("accept", "-")
            notes = config.get("notes", "-")

            table.add_row(str(i), domain, ua_preview, accept_header, notes)
        else:
            table.add_row(
                str(i),
                "[red]Failed to decrypt[/red]",
                "-",
                "-",
                "[red]Invalid key or corrupted data[/red]",
            )

    console.print(table)


@app.command()
def create():
    """Create a new encrypted domain configuration (interactive)."""
    console.print("[bold cyan]Calendar Domain Configuration Encryptor[/bold cyan]\n")

    # Get or create encryption key
    key = get_or_create_key()

    # Gather configuration
    console.print("\n[bold]Enter domain configuration:[/bold]")

    domain = Prompt.ask("Domain (e.g., 'example.com')")
    if not domain:
        console.print("[red]Domain is required[/red]")
        raise typer.Exit(1)

    config = {"domain": domain}

    # Optional fields
    user_agent = Prompt.ask("User-Agent", default="")
    if user_agent:
        config["user_agent"] = user_agent

    accept = Prompt.ask("Accept header", default="")
    if accept:
        config["accept"] = accept

    notes = Prompt.ask("Notes/reason for this config", default="")
    if notes:
        config["notes"] = notes

    # Additional headers
    if Confirm.ask("Add additional headers?", default=False):
        additional = {}
        while True:
            header_name = Prompt.ask("Header name (press Enter when done)", default="")
            if not header_name:
                break
            header_value = Prompt.ask(f"Value for {header_name}")
            additional[header_name] = header_value
        if additional:
            config["additional_headers"] = additional

    # Show what will be encrypted
    console.print("\n[bold]Configuration to encrypt:[/bold]")
    console.print_json(json.dumps(config, indent=2))

    if not Confirm.ask("\nEncrypt this configuration?", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    # Encrypt
    encrypted = encrypt_config(config, key)

    # Output result
    console.print("\n[bold green]ENCRYPTED CONFIGURATION[/bold green]\n")
    console.print("Add this line to ENCRYPTED_CONFIGS in domain_configs.py:\n")
    console.print(f'[cyan]    "{encrypted}",[/cyan]\n')


if __name__ == "__main__":
    app()
