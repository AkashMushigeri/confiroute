"""Configuration manager for ConfiRoute."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import yaml
from dotenv import load_dotenv

# Automatically load .env if present
load_dotenv()

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"


class Config:
    """Provides structured, validated access to system configuration."""

    def __init__(self, config_dict: Dict[str, Any], config_path: Optional[Path] = None):
        self._raw = config_dict
        self.config_path = config_path

        # Core system
        system = config_dict.get("system", {})
        self.app_name: str = system.get("app_name", "ConfiRoute")
        self.version: str = system.get("version", "0.1.0")
        self.subtitle: str = system.get("subtitle", "Confidence-Aware LLM Routing System")
        self.is_mock_mode: bool = system.get("is_mock_mode", True)
        self.seed: int = int(system.get("seed", 42))

        # Root directory calculation
        if config_path:
            self.root_dir = config_path.parent
        else:
            self.root_dir = Path(__file__).resolve().parent.parent.parent

        self.database_path: Path = self.root_dir / system.get("database_path", "data/confiroute.db")
        self.cache_dir: Path = self.root_dir / system.get("cache_dir", ".cache/llm_cache")

        # Models
        self.models: Dict[str, Any] = config_dict.get("models", {})

        # Confidence weights & settings
        confidence = config_dict.get("confidence", {})
        weights = confidence.get("weights", {})
        self.weight_s1: float = float(weights.get("w_s1", 0.40))
        self.weight_s2: float = float(weights.get("w_s2", 0.30))
        self.weight_s3: float = float(weights.get("w_s3", 0.30))

        consistency = confidence.get("self_consistency", {})
        self.consistency_samples: int = int(consistency.get("samples", 3))
        self.consistency_temperature: float = float(consistency.get("temperature", 0.7))

        # Routing thresholds
        routing = config_dict.get("routing", {})
        thresholds = routing.get("thresholds", {})
        self.threshold_high: float = float(thresholds.get("high", 0.80))
        self.threshold_low: float = float(thresholds.get("low", 0.50))
        self.tier2_accept: float = float(thresholds.get("tier2_accept", 0.80))
        self.enable_risk_override: bool = bool(routing.get("enable_risk_override", True))

        # Risk keywords
        risk_rules = config_dict.get("risk_rules", {})
        self.risk_keywords: List[str] = [k.lower() for k in risk_rules.get("keywords", [])]

        # Dataset settings
        dataset = config_dict.get("dataset", {})
        self.hf_repo: str = dataset.get("hf_repo", "openlifescienceai/medmcqa")
        splits = dataset.get("splits", {})
        self.split_sizes: Dict[str, int] = {
            "dev": int(splits.get("dev", 50)),
            "val": int(splits.get("val", 200)),
            "test": int(splits.get("test", 300)),
            "test_removed": int(splits.get("test_removed", 200)),
        }
        self.raw_data_dir: Path = self.root_dir / dataset.get("raw_dir", "data/raw")
        self.processed_data_dir: Path = self.root_dir / dataset.get("processed_dir", "data/processed")

        # Alerts configuration
        alerts = config_dict.get("alerts", {})
        self.alerts_config: Dict[str, Any] = {
            "high_escalation_threshold": float(alerts.get("high_escalation_threshold", 0.50)),
            "window_size": int(alerts.get("window_size", 20)),
            "backlog_threshold": int(alerts.get("backlog_threshold", 10)),
            "repeated_low_confidence_threshold": int(alerts.get("repeated_low_confidence_threshold", 3)),
            "low_confidence_threshold": float(alerts.get("low_confidence_threshold", 0.50)),
        }

    def get_reference_pricing(self, model_key: str = "tier1") -> Dict[str, float]:
        """Return reference pricing per 1K tokens for equivalent cost calculations."""
        model_info = self.models.get(model_key, {})
        pricing = model_info.get("reference_pricing", {})
        return {
            "input_per_1k_tokens": float(pricing.get("input_per_1k_tokens", 0.0)),
            "output_per_1k_tokens": float(pricing.get("output_per_1k_tokens", 0.0)),
        }


_cached_config: Optional[Config] = None


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or use cached instance."""
    global _cached_config
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    _cached_config = Config(data, config_path=config_path)
    return _cached_config


def get_config() -> Config:
    """Return the global configuration instance."""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config
