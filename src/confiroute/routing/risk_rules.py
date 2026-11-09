"""Risk detection and high-risk safety rules for medical queries."""

from typing import List, Optional, Tuple
import re
from confiroute.config import get_config


def get_default_risk_patterns() -> List[str]:
    """Return default compiled regex patterns for high-risk medical keywords."""
    config = get_config()
    keywords = config.risk_keywords
    return keywords


def check_risk(
    text: str,
    options_text: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Tuple[bool, Optional[str]]:
    """Inspect medical text for critical safety-risk keywords or patterns.

    Args:
        text: Question or medical prompt string.
        options_text: Optional combined text of options.
        enabled: If False, bypass risk checks (for ablation experiments).

    Returns:
        (is_high_risk, matched_reason)
    """
    config = get_config()
    if enabled is None:
        enabled = config.enable_risk_override

    if not enabled:
        return False, None

    full_text = text.lower()
    if options_text:
        full_text += " " + options_text.lower()

    # Domain specific regex checks
    high_risk_patterns = [
        (r"\b(?:dose|dosage|mg/kg|mcg|units/kg|bolus)\b", "Medication dosage / calculation"),
        (r"\b(?:overdose|poisoning|toxicity|antidote|toxic)\b", "Overdose / Toxicology"),
        (r"\b(?:cardiac arrest|defibrillat\w*|ventricular fibrillation|infarction|cpr|resuscitat\w*)\b", "Cardiac / Life-threatening emergency"),
        (r"\b(?:emergency|triage|anaphylaxis|epinephrine|status epilepticus)\b", "Acute emergency / Anaphylaxis"),
        (r"\b(?:pregnancy|teratogenic|breastfeeding|lactation)\b", "Pregnancy / Teratogenic contraindication"),
        (r"\b(?:suicide|self-harm|lethal dose)\b", "Self-harm / Crisis risk"),
    ]

    for pattern, reason in high_risk_patterns:
        if re.search(pattern, full_text):
            return True, reason

    # Also check any additional raw keywords from config
    for kw in config.risk_keywords:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, full_text):
            return True, f"High-risk keyword: '{kw}'"

    return False, None
