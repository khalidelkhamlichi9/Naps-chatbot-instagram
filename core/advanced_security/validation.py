import re
import html
from typing import Any
from fastapi import HTTPException
import logging

logger = logging.getLogger("naps-chatbot-security")

def sanitize_input(data: str) -> str:
    """
    Sanitize input to prevent XSS and generic injection attacks.
    Escapes HTML characters.
    """
    if not isinstance(data, str):
        return data
    # Escape HTML to prevent XSS
    sanitized = html.escape(data)
    return sanitized

def detect_anomaly(input_str: str) -> bool:
    """
    Basic behavior anomaly detection for injection patterns.
    In a fully realized futuristic system, this would call out to an ML model.
    For now, it uses heuristic checks for common obfuscation and injection markers.
    """
    if not isinstance(input_str, str):
        return False
    
    # Common SQLi / XSS patterns
    suspicious_patterns = [
        r"(?i)(union\s+select|select\s+.*\s+from)",
        r"(?i)(<script>|javascript:|onerror=)",
        r"(?i)(\bexec\s*\(|\bsystem\s*\()",
        r"(--|#|\/\*)", # SQL Comments
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, input_str):
            logger.warning(f"[SEC_ANOMALY] Detected potential malicious payload matching pattern: {pattern}")
            return True
            
    return False

def validate_and_sanitize(payload: dict) -> dict:
    """
    Recursively sanitize and check payload for anomalies.
    """
    sanitized_payload = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            sanitized_payload[key] = validate_and_sanitize(value)
        elif isinstance(value, list):
            sanitized_payload[key] = [
                validate_and_sanitize(item) if isinstance(item, dict) else sanitize_input(str(item)) 
                for item in value
            ]
        elif isinstance(value, str):
            if detect_anomaly(value):
                raise HTTPException(status_code=400, detail="Malformed or suspicious input detected.")
            sanitized_payload[key] = sanitize_input(value)
        else:
            sanitized_payload[key] = value
    return sanitized_payload
