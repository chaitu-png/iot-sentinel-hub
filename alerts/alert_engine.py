"""
Alert Rules Engine - Evaluates sensor data against alert conditions.

BUG INVENTORY:
- BUG-033: Alert deduplication uses exact match (ignores time window)
- BUG-034: Alert escalation timer never resets after acknowledgment
- BUG-035: Notification dispatch is fire-and-forget (no delivery guarantee)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from enum import Enum


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertRule:
    def __init__(self, rule_id: str, name: str, condition: str,
                 threshold: float, severity: AlertSeverity,
                 device_types: List[str] = None):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition  # "gt", "lt", "eq", "ne"
        self.threshold = threshold
        self.severity = severity
        self.device_types = device_types or []
        self.enabled = True
        self.cooldown_minutes = 5


class Alert:
    def __init__(self, rule: AlertRule, device_id: str, value: float,
                 message: str = ""):
        self.id = f"ALERT-{int(datetime.utcnow().timestamp() * 1000)}"
        self.rule_id = rule.rule_id
        self.device_id = device_id
        self.severity = rule.severity
        self.value = value
        self.message = message or f"Alert: {rule.name} triggered (value={value})"
        self.created_at = datetime.utcnow()
        self.acknowledged = False
        self.acknowledged_by = None
        self.resolved = False
        self.escalation_count = 0


class AlertEngine:
    """Evaluates sensor data against alert rules and dispatches notifications."""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self._notification_handlers: List[Callable] = []
        self._suppressed: Dict[str, datetime] = {}

    def add_rule(self, rule: AlertRule):
        """Register a new alert rule."""
        self.rules[rule.rule_id] = rule

    def evaluate(self, device_id: str, metric_name: str,
                 value: float) -> Optional[Alert]:
        """
        Evaluate a data point against all active rules.
        """
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            triggered = False
            if rule.condition == "gt" and value > rule.threshold:
                triggered = True
            elif rule.condition == "lt" and value < rule.threshold:
                triggered = True
            elif rule.condition == "eq" and value == rule.threshold:
                triggered = True
            elif rule.condition == "ne" and value != rule.threshold:
                triggered = True

            if triggered:
                # BUG-033: Deduplication only checks exact same device+rule
                # Doesn't consider time window - rapid evaluations create floods
                dedup_key = f"{device_id}:{rule.rule_id}"

                if dedup_key in self._suppressed:
                    last_alert = self._suppressed[dedup_key]
                    cooldown = timedelta(minutes=rule.cooldown_minutes)
                    if datetime.utcnow() - last_alert < cooldown:
                        continue

                alert = Alert(rule, device_id, value)
                self.active_alerts.append(alert)
                self._suppressed[dedup_key] = datetime.utcnow()

                # BUG-035: Fire and forget notifications
                self._dispatch_notification(alert)

                return alert

        return None

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """
        Acknowledge an alert.

        BUG-034: Doesn't reset escalation timer.
        Acknowledged alerts continue to escalate.
        """
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user
                # BUG-034: Missing escalation timer reset
                # alert.escalation_count = 0  # Should reset
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Move alert from active to history."""
        for i, alert in enumerate(self.active_alerts):
            if alert.id == alert_id:
                alert.resolved = True
                self.alert_history.append(alert)
                self.active_alerts.pop(i)
                return True
        return False

    def _dispatch_notification(self, alert: Alert):
        """
        Send alert notification.

        BUG-035: No error handling, no retry, no delivery confirmation.
        If notification fails, it's silently lost.
        """
        for handler in self._notification_handlers:
            try:
                # BUG-035: No retry on failure
                handler(alert)
            except Exception:
                # Silent failure - notification lost
                pass

    def get_alert_summary(self) -> dict:
        """Get alert engine summary."""
        severity_counts = {}
        for alert in self.active_alerts:
            sev = alert.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "active_alerts": len(self.active_alerts),
            "acknowledged": sum(1 for a in self.active_alerts if a.acknowledged),
            "unacknowledged": sum(1 for a in self.active_alerts if not a.acknowledged),
            "total_historical": len(self.alert_history),
            "active_rules": sum(1 for r in self.rules.values() if r.enabled),
            "by_severity": severity_counts,
        }
