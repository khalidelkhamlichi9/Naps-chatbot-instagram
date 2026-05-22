import logging
import json
import time
from typing import Optional
from fastapi import Request
from .encryption import encrypt_data

# Ensure logs directory exists
import os
os.makedirs("logs", exist_ok=True)

# Set up a secure file logger
sec_logger = logging.getLogger("security_audit")
sec_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/security_audit.enc.log")
sec_logger.addHandler(file_handler)

def log_audit_event(event_type: str, request: Request, user_id: Optional[str] = None, details: dict = None):
    """
    Logs an encrypted, immutable-style audit record.
    In a real system, these would be shipped to a SIEM.
    """
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    
    raw_event = {
        "timestamp": time.time(),
        "event_type": event_type,
        "ip": ip,
        "user_agent": ua,
        "user_id": user_id or "anonymous",
        "details": details or {}
    }
    
    # Encrypt the log entry before writing to disk
    encrypted_event = encrypt_data(json.dumps(raw_event))
    
    sec_logger.info(json.dumps(encrypted_event))
    
    # Check for critical events that need real-time alerting
    if event_type in ["AUTH_FAILURE_SPIKE", "INJECTION_ATTEMPT", "ZERO_TRUST_VIOLATION"]:
        trigger_realtime_alert(raw_event)

def trigger_realtime_alert(event: dict):
    """
    Stub for triggering real-time alerts to Threat Intelligence feeds or PagerDuty.
    """
    print(f"\n[CRITICAL ALERT] Security Event Triggered: {event['event_type']} from {event['ip']}")
    # e.g., requests.post("https://siem.internal/api/alerts", json=event)
