"""Persistent disk cache for LLM calls."""

from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json
from confiroute.config import get_config


class LLMDiskCache:
    """Stores and retrieves LLM responses on disk keyed by sha256 hash of query params."""

    def __init__(self, cache_dir: Optional[Path] = None):
        config = get_config()
        self.cache_dir = cache_dir or config.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, model_key: str, prompt: str, temperature: float, n: int, logprobs: bool, **kwargs: Any) -> str:
        payload = {
            "model_key": model_key,
            "prompt": prompt,
            "temperature": round(float(temperature), 4),
            "n": int(n),
            "logprobs": bool(logprobs),
            "extra": kwargs,
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get(self, model_key: str, prompt: str, temperature: float, n: int, logprobs: bool, **kwargs: Any) -> Optional[Dict[str, Any]]:
        key = self._make_key(model_key, prompt, temperature, n, logprobs, **kwargs)
        file_path = self.cache_dir / f"{key}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["cached"] = True
                    return data
            except Exception:
                return None
        return None

    def put(self, model_key: str, prompt: str, temperature: float, n: int, logprobs: bool, response_data: Dict[str, Any], **kwargs: Any) -> None:
        key = self._make_key(model_key, prompt, temperature, n, logprobs, **kwargs)
        file_path = self.cache_dir / f"{key}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2)
        except Exception as e:
            print(f"[CACHE WARNING] Failed to write cache entry: {e}")

    def clear(self) -> int:
        """Clear all cached responses and return count of deleted files."""
        count = 0
        for p in self.cache_dir.glob("*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        return count
