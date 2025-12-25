"""Configuration loader for YAML config files"""
import yaml
from pathlib import Path
from functools import lru_cache


class ConfigLoader:
    """Load and manage YAML configuration files"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config_agent.yaml"
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self):
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_agent_config(self, agent_name: str):
        """Get configuration for a specific agent"""
        if agent_name not in self._config:
            raise KeyError(f"No config found for agent '{agent_name}' in {self.config_path}")
        return self._config[agent_name]


# Singleton
_config_loader = None


@lru_cache(maxsize=1)
def get_config_loader():
    """Get or create config loader singleton"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

