"""Unit tests for confidence calibration and meta-model module."""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from confiroute.confidence.calibration import (
    ConfidenceCalibrator,
    create_synthetic_validation_features,
)


def test_synthetic_data_generation():
    """Verify create_synthetic_validation_features generates expected shapes and labels."""
    X, y = create_synthetic_validation_features(n_samples=40, seed=123)
    assert X.shape == (40, 3)
    assert y.shape == (40,)
    assert set(np.unique(y)).issubset({0, 1})
    assert len(np.unique(y)) == 2


def test_impute_features():
    """Verify _impute_features handles None, NaN, and normal values."""
    cal = ConfidenceCalibrator(impute_value=0.5)
    
    # Normal values
    feat = cal._impute_features(0.8, 0.9, 0.7)
    np.testing.assert_allclose(feat, [0.8, 0.9, 0.7])

    # None and NaN
    feat_missing = cal._impute_features(None, np.nan, 0.6)
    np.testing.assert_allclose(feat_missing, [0.5, 0.5, 0.6])


def test_platt_scaling_fit_and_predict():
    """Verify Platt scaling (Logistic Regression) fits and predicts probabilities."""
    X, y = create_synthetic_validation_features(n_samples=50, seed=42)
    cal = ConfidenceCalibrator(method="platt")
    assert not cal.is_fitted

    cal.fit(X, y)
    assert cal.is_fitted
    assert cal.model is not None
    assert cal.fit_metadata["n_samples"] == 50

    # Prediction should be in [0.0, 1.0]
    p1 = cal.predict_proba(0.9, 1.0, 0.95)
    assert 0.0 <= p1 <= 1.0
    p2 = cal.predict_proba(0.2, 0.33, 0.3)
    assert 0.0 <= p2 <= 1.0
    # Higher signals should yield higher calibrated probability
    assert p1 > p2


def test_isotonic_fit_and_predict():
    """Verify Isotonic regression fits and predicts monotonic bounded probabilities."""
    X, y = create_synthetic_validation_features(n_samples=50, seed=42)
    cal = ConfidenceCalibrator(method="isotonic")
    cal.fit(X, y)
    assert cal.is_fitted
    assert cal.model is not None

    p_high = cal.predict_proba(0.95, 1.0, 0.9)
    p_low = cal.predict_proba(0.2, 0.3, 0.2)
    assert 0.0 <= p_high <= 1.0
    assert 0.0 <= p_low <= 1.0
    assert p_high >= p_low


def test_missing_signal_imputation_during_predict():
    """Verify predict_proba works seamlessly when one or more signals are missing (e.g. S1=None)."""
    X, y = create_synthetic_validation_features(n_samples=40, seed=42)
    cal = ConfidenceCalibrator(method="platt")
    cal.fit(X, y)

    # Missing S1
    p_no_s1 = cal.predict_proba(None, 1.0, 0.8)
    assert isinstance(p_no_s1, float)
    assert 0.0 <= p_no_s1 <= 1.0

    # Missing S1 and S2
    p_s3_only = cal.predict_proba(None, None, 0.9)
    assert isinstance(p_s3_only, float)
    assert 0.0 <= p_s3_only <= 1.0

    # All missing
    p_all_missing = cal.predict_proba(None, None, None)
    assert isinstance(p_all_missing, float)
    assert 0.0 <= p_all_missing <= 1.0


def test_cross_fit_predict():
    """Verify K-fold cross-fitting generates out-of-fold calibrated probabilities."""
    X, y = create_synthetic_validation_features(n_samples=30, seed=42)
    cal = ConfidenceCalibrator(method="platt")
    preds = cal.cross_fit_predict(X, y, n_splits=3)

    assert len(preds) == 30
    assert np.all(preds >= 0.0)
    assert np.all(preds <= 1.0)


def test_save_and_load_joblib():
    """Verify calibrator can be serialized to disk and reloaded without loss of behavior."""
    X, y = create_synthetic_validation_features(n_samples=40, seed=42)
    cal = ConfidenceCalibrator(method="platt")
    cal.fit(X, y)

    orig_p = cal.predict_proba(0.85, 1.0, 0.9)

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "calibrator.joblib"
        saved_path = cal.save(model_path)
        assert saved_path.exists()

        # Load back
        loaded = ConfidenceCalibrator.load(saved_path)
        assert loaded.is_fitted
        assert loaded.method == "platt"
        loaded_p = loaded.predict_proba(0.85, 1.0, 0.9)
        assert loaded_p == orig_p


def test_fit_validation_errors():
    """Verify fit raises ValueError when data is insufficient or degenerate."""
    cal = ConfidenceCalibrator()

    # Fewer than 5 samples
    with pytest.raises(ValueError, match="Insufficient samples"):
        cal.fit([[0.8, 0.8, 0.8]], [1])

    # Only one class
    with pytest.raises(ValueError, match="Both positive and negative"):
        cal.fit([[0.8, 0.8, 0.8]] * 6, [1] * 6)


def test_load_nonexistent_file():
    """Verify FileNotFoundError when loading missing model."""
    with pytest.raises(FileNotFoundError):
        ConfidenceCalibrator.load(Path("nonexistent_model.joblib"))
