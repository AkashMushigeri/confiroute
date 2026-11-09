"""Confidence calibration and meta-model module for ConfiRoute.

Supports:
1. Weighted-average baseline confidence.
2. Logistic regression meta-model (Platt scaling).
3. Isotonic regression calibration.
4. Dynamic imputation for missing signals (e.g., when S1 is unavailable).
5. Cross-fitted validation to avoid overfitting on small datasets.
6. Persistence via joblib.

Scientific Note:
Calibration matches raw confidence scores to empirical clinical accuracy.
Fitting must occur strictly on VALIDATION records to prevent test set data leakage.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold

from confiroute.confidence.combiner import combine_signals


class ConfidenceCalibrator:
    """Manages training, cross-fitting, calibration, and persistence of confidence scores."""

    def __init__(
        self,
        method: str = "platt",  # "platt", "isotonic", "weighted_average"
        impute_value: float = 0.5,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.method = method.lower()
        self.impute_value = float(impute_value)
        self.weights = weights
        self.is_fitted = False
        self.model: Optional[Union[LogisticRegression, IsotonicRegression]] = None
        self.fit_metadata: Dict[str, Any] = {}

    def _impute_features(
        self,
        s1: Optional[float],
        s2: Optional[float],
        s3: Optional[float],
    ) -> np.ndarray:
        """Convert signals to a 3-element feature vector, imputing missing values."""
        v1 = float(s1) if s1 is not None and not np.isnan(s1) else self.impute_value
        v2 = float(s2) if s2 is not None and not np.isnan(s2) else self.impute_value
        v3 = float(s3) if s3 is not None and not np.isnan(s3) else self.impute_value
        return np.array([v1, v2, v3], dtype=np.float64)

    def fit(
        self,
        features: Union[np.ndarray, List[List[Optional[float]]]],
        labels: Union[np.ndarray, List[int]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConfidenceCalibrator":
        """Fit calibration meta-model on validation features and binary correctness labels.

        Args:
            features: 2D array-like of shape (N, 3) representing [S1, S2, S3].
            labels: 1D array-like of shape (N,) containing binary labels (1=correct, 0=wrong).
            metadata: Optional dictionary of experiment metadata.
        """
        X_raw = np.array(features, dtype=object)
        y = np.array(labels, dtype=np.int32)

        if len(y) < 5:
            raise ValueError(f"Insufficient samples to fit calibrator (minimum 5 required, got {len(y)})")

        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            raise ValueError(f"Both positive and negative correctness classes are required to fit calibration. Found: {unique_classes}")

        # Impute missing values
        N = X_raw.shape[0]
        X = np.zeros((N, 3), dtype=np.float64)
        for i in range(N):
            row = X_raw[i]
            s1 = row[0] if len(row) > 0 else None
            s2 = row[1] if len(row) > 1 else None
            s3 = row[2] if len(row) > 2 else None
            X[i] = self._impute_features(s1, s2, s3)

        if self.method == "platt":
            # Logistic Regression meta-model (Platt scaling across 3 signals)
            lr = LogisticRegression(C=1.0, max_iter=200, random_state=42)
            lr.fit(X, y)
            self.model = lr

        elif self.method == "isotonic":
            # Monotonic isotonic regression on composite weighted average
            raw_scores = np.array([
                combine_signals(X[i, 0], X[i, 1], X[i, 2], weights=self.weights)[0]
                for i in range(N)
            ])
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            iso.fit(raw_scores, y)
            self.model = iso

        elif self.method == "weighted_average":
            self.model = None

        else:
            raise ValueError(f"Unknown calibration method: {self.method}")

        self.is_fitted = True
        self.fit_metadata = {
            "n_samples": int(N),
            "method": self.method,
            "classes": unique_classes.tolist(),
            "class_distribution": {int(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
            "extra": metadata or {},
        }

        return self

    def predict_proba(
        self,
        s1: Optional[float],
        s2: Optional[float],
        s3: Optional[float],
    ) -> float:
        """Produce calibrated confidence score in [0.0, 1.0]."""
        # If not fitted or method is weighted average, fall back to combiner
        if not self.is_fitted or self.method == "weighted_average" or self.model is None:
            score, _ = combine_signals(s1, s2, s3, weights=self.weights)
            return float(score)

        if self.method == "platt" and isinstance(self.model, LogisticRegression):
            feat = self._impute_features(s1, s2, s3).reshape(1, -1)
            proba = float(self.model.predict_proba(feat)[0, 1])
            return round(max(0.0, min(1.0, proba)), 4)

        elif self.method == "isotonic" and isinstance(self.model, IsotonicRegression):
            raw_score, _ = combine_signals(s1, s2, s3, weights=self.weights)
            proba = float(self.model.predict([raw_score])[0])
            return round(max(0.0, min(1.0, proba)), 4)

        score, _ = combine_signals(s1, s2, s3, weights=self.weights)
        return float(score)

    def cross_fit_predict(
        self,
        features: Union[np.ndarray, List[List[Optional[float]]]],
        labels: Union[np.ndarray, List[int]],
        n_splits: int = 5,
    ) -> np.ndarray:
        """K-Fold cross-fitted predictions to calibrate validation data without data leakage."""
        X_raw = np.array(features, dtype=object)
        y = np.array(labels, dtype=np.int32)
        N = len(y)

        # Impute features
        X = np.zeros((N, 3), dtype=np.float64)
        for i in range(N):
            row = X_raw[i]
            s1 = row[0] if len(row) > 0 else None
            s2 = row[1] if len(row) > 1 else None
            s3 = row[2] if len(row) > 2 else None
            X[i] = self._impute_features(s1, s2, s3)

        calibrated_preds = np.zeros(N, dtype=np.float64)
        kf = KFold(n_splits=min(n_splits, N // 2), shuffle=True, random_state=42)

        for train_idx, val_idx in kf.split(X, y):
            fold_calibrator = ConfidenceCalibrator(
                method=self.method,
                impute_value=self.impute_value,
                weights=self.weights,
            )
            # Only fit if both classes exist in train fold
            if len(np.unique(y[train_idx])) >= 2:
                fold_calibrator.fit(X[train_idx], y[train_idx])
                for idx in val_idx:
                    calibrated_preds[idx] = fold_calibrator.predict_proba(
                        X[idx, 0], X[idx, 1], X[idx, 2]
                    )
            else:
                for idx in val_idx:
                    calibrated_preds[idx] = combine_signals(
                        X[idx, 0], X[idx, 1], X[idx, 2], weights=self.weights
                    )[0]

        return calibrated_preds

    def save(self, file_path: Union[str, Path]) -> Path:
        """Serialize calibrator model to disk using joblib."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "ConfidenceCalibrator":
        """Deserialize calibrator model from disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Calibrator file not found at: {path}")
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not a {cls.__name__} (got {type(obj)})")
        return obj


def create_synthetic_validation_features(
    n_samples: int = 50,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic [S1, S2, S3] features and labels for unit tests."""
    rng = np.random.RandomState(seed)
    X = np.zeros((n_samples, 3), dtype=np.float64)
    y = np.zeros(n_samples, dtype=np.int32)

    for i in range(n_samples):
        # Generate correlated confidence and correctness
        prob_correct = rng.uniform(0.2, 0.9)
        is_corr = 1 if rng.uniform(0, 1) < prob_correct else 0
        y[i] = is_corr

        if is_corr:
            # High confidence when correct
            s1 = rng.uniform(0.65, 0.98) if rng.uniform(0, 1) > 0.1 else np.nan
            s2 = rng.choice([0.67, 1.0])
            s3 = rng.uniform(0.70, 0.95)
        else:
            # Lower confidence when incorrect
            s1 = rng.uniform(0.20, 0.60) if rng.uniform(0, 1) > 0.1 else np.nan
            s2 = rng.choice([0.33, 0.67])
            s3 = rng.uniform(0.25, 0.65)

        X[i] = [s1, s2, s3]

    return X, y
