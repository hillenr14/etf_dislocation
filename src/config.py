import yaml
import os
from typing import Dict, Any, Optional

class Config:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def universe_profile(self) -> str:
        return self._data.get('universe_profile', 'vanguard_core')

    @property
    def universe_files(self) -> Dict[str, str]:
        return self._data.get('universe_files', {})

    @property
    def liquidity_filters(self) -> Dict[str, Any]:
        return self._data.get('liquidity', {})

    @property
    def windows(self) -> Dict[str, int]:
        return self._data.get('windows', {})

    @property
    def thresholds(self) -> Dict[str, float]:
        return self._data.get('thresholds', {})

    @property
    def weights(self) -> Dict[str, float]:
        return self._data.get('weights', {})
    
    @property
    def composite_action_map(self) -> Dict[str, float]:
        return self._data.get('composite_to_action', {})

    @property
    def costs(self) -> Dict[str, float]:
        return self._data.get('costs', {})

    @property
    def risk(self) -> Dict[str, Any]:
        return self._data.get('risk', {})

    @property
    def execution(self) -> Dict[str, Any]:
        return self._data.get('execution', {})

    @property
    def reporting(self) -> Dict[str, Any]:
        return self._data.get('reporting', {})

def load_config(path: str = "config/default.yaml") -> Config:
    return Config(path)
