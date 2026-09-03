"""
RIGEL GCS - Discovery

Discovery chịu trách nhiệm phát hiện các thiết bị MAVLink
thông qua UDP và Serial.
"""

from .udp_discovery import UDPDiscovery
from .serial_discovery import SerialDiscovery
from .unified_auto_discovery import UnifiedAutoDiscovery

__all__ = [
    "UDPDiscovery",
    "SerialDiscovery",
    "UnifiedAutoDiscovery",
]