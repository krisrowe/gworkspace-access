import click
import yaml
from . import config

@click.group()
def config_group():
    """Commands for managing gwsa configuration."""
    pass

@config_group.command('view')
def view_config():
    """Displays the current gwsa configuration."""
    config_data = config.load_config()
    click.echo(yaml.dump(config_data, default_flow_style=False))

@config_group.command('set')
@click.argument('key')
@click.argument('value')
def set_config(key, value):
    """Sets a configuration value."""
    # Basic type conversion for boolean and numbers
    if value.lower() in ['true', 'false']:
        value = value.lower() == 'true'
    elif value.isdigit():
        value = int(value)
    elif value.replace('.', '', 1).isdigit():
        try:
            value = float(value)
        except ValueError:
            pass # Keep as string if it's not a valid float

    config.set_config_value(key, value)
    click.echo(f"Set '{key}' to: {value}")

