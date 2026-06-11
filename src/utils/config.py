"""
Configuration Utility - Load and manage configuration.
"""

import os
from pathlib import Path
from typing import Dict, Any

import yaml
from dotenv import load_dotenv
from loguru import logger


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from file and environment variables."""
    
    # Load environment variables
    load_dotenv()
    
    # Determine config path
    if config_path is None:
        config_path = os.getenv(
            "CONFIG_PATH",
            "config/config.yaml"
        )
    
    # Load config file
    config_file = Path(config_path)
    
    if not config_file.exists():
        # Try example config
        example_path = config_file.parent / "config.example.yaml"
        if example_path.exists():
            logger.warning(f"Config file not found. Using example: {example_path}")
            config_file = example_path
        else:
            raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Load YAML config
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    # Replace environment variables
    config = _replace_env_vars(config)
    
    # Validate config
    _validate_config(config)
    
    logger.info(f"Configuration loaded from: {config_file}")
    return config


def _replace_env_vars(config: Any) -> Any:
    """Replace ${ENV_VAR} patterns with environment variable values."""
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        value = os.getenv(env_var)
        if value is None:
            logger.warning(f"Environment variable {env_var} not set")
        return value
    else:
        return config


def _validate_config(config: Dict[str, Any]):
    """Validate configuration."""
    required_sections = ["exchange", "trading", "strategy"]
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    # Validate exchange config
    exchange = config["exchange"]
    if "name" not in exchange:
        raise ValueError("Exchange name is required")
    
    # Validate trading config
    trading = config["trading"]
    if "pairs" not in trading or not trading["pairs"]:
        raise ValueError("Trading pairs are required")
    
    # Validate strategy config
    strategy = config["strategy"]
    if "name" not in strategy:
        raise ValueError("Strategy name is required")


def get_config_value(config: Dict, key_path: str, default=None):
    """Get a nested config value using dot notation."""
    keys = key_path.split(".")
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value
