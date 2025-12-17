"""
Device Registry - Manages IoT device lifecycle.

BUG INVENTORY:
- BUG-029: Device status not updated on heartbeat timeout
- BUG-030: Concurrent device registration causes duplicate IDs
- BUG-031: No rate limiting on device telemetry ingestion
- BUG-032: Firmware version comparison uses string sort (not semver)
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class Device:
    def __init__(self, device_id: str, device_type: str, firmware: str,
                 location: str = ""):
        self.device_id = device_id
        self.device_type = device_type
        self.firmware = firmware
        self.location = location
        self.status = DeviceStatus.ONLINE
        self.registered_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.telemetry_count = 0
        self.error_count = 0
        self.metadata: Dict = {}


class DeviceRegistry:
    """Central registry for all IoT devices."""

    def __init__(self, heartbeat_timeout: int = 60):
        self.devices: Dict[str, Device] = {}
        self.heartbeat_timeout = heartbeat_timeout
        self._counter = 0
        # BUG-030: No lock for concurrent access
        # self._lock = threading.Lock()

    def register_device(self, device_type: str, firmware: str,
                        location: str = "") -> Device:
        """
        Register a new IoT device.

        BUG-030: No atomic ID generation - concurrent calls can
        generate duplicate device IDs.
        """
        # BUG-030: Non-atomic counter increment
        self._counter += 1
        device_id = f"DEV-{device_type[:3].upper()}-{self._counter:06d}"

        device = Device(device_id, device_type, firmware, location)
        self.devices[device_id] = device
        return device

    def heartbeat(self, device_id: str) -> bool:
        """
        Process device heartbeat.

        BUG-029: Updates heartbeat timestamp but never checks for
        devices that MISSED heartbeats. No background checker.
        """
        device = self.devices.get(device_id)
        if not device:
            return False

        device.last_heartbeat = datetime.utcnow()
        # BUG-029: Sets status to ONLINE but never sets to OFFLINE
        # when heartbeats stop. No timeout checker exists.
        device.status = DeviceStatus.ONLINE
        return True

    def check_firmware_update_needed(self, device_id: str,
                                      latest_version: str) -> bool:
        """
        Check if device needs firmware update.

        BUG-032: String comparison instead of semantic versioning.
        "2.9.0" > "2.10.0" with string comparison (wrong).
        """
        device = self.devices.get(device_id)
        if not device:
            return False

        # BUG-032: String comparison - "2.9.0" appears > "2.10.0"
        return device.firmware < latest_version

    def ingest_telemetry(self, device_id: str, data: dict) -> bool:
        """
        Ingest telemetry data from a device.

        BUG-031: No rate limiting - a misbehaving device can flood
        the system with telemetry data.
        """
        device = self.devices.get(device_id)
        if not device:
            return False

        # BUG-031: No throttling/rate check
        device.telemetry_count += 1
        device.last_heartbeat = datetime.utcnow()
        return True

    def get_offline_devices(self) -> List[Device]:
        """
        Get devices that haven't sent heartbeat within timeout.

        Note: This method works correctly but is NEVER called
        automatically - there's no background scheduler.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)
        offline = []
        for device in self.devices.values():
            if device.last_heartbeat < cutoff and device.status != DeviceStatus.DECOMMISSIONED:
                offline.append(device)
        return offline

    def get_fleet_status(self) -> dict:
        """Get overall fleet status summary."""
        status_counts = {}
        for device in self.devices.values():
            status = device.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_devices": len(self.devices),
            "status_breakdown": status_counts,
            "total_telemetry_events": sum(
                d.telemetry_count for d in self.devices.values()
            ),
            "total_errors": sum(
                d.error_count for d in self.devices.values()
            ),
        }
