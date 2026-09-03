from __future__ import annotations
from typing import Dict, Optional, Tuple
from .device import MAVLinkDevice
class DeviceRegistry:
    def __init__(self):self._devices:Dict[Tuple[str,int,int],MAVLinkDevice]={}
    @staticmethod
    def _make_key(sysid,compid,transport):return ((transport or 'UNKNOWN').upper(),int(sysid),int(compid))
    def get_or_create(self,sysid,compid,transport=None,rx_endpoint=None,tx_endpoint=None):
        key=self._make_key(sysid,compid,transport)
        if key not in self._devices:
            d=MAVLinkDevice(sysid=sysid,compid=compid,transport=transport.upper() if transport else None,rx_endpoint=rx_endpoint,tx_endpoint=tx_endpoint); self._devices[key]=d
            print(f'[DEVICE REGISTRY] New device ID={self.device_id(d)}')
        else:
            d=self._devices[key]
            if transport is not None:d.transport=transport.upper()
            if rx_endpoint is not None:d.rx_endpoint=rx_endpoint
            if tx_endpoint is not None:d.tx_endpoint=tx_endpoint
        return d
    def get(self,sysid,compid,transport=None)->Optional[MAVLinkDevice]:return self._devices.get(self._make_key(sysid,compid,transport))
    def get_by_id(self,device_id):
        for d in self._devices.values():
            if self.device_id(d)==device_id:return d
        return None
    @staticmethod
    def device_id(device):return f'{(device.transport or "UNKNOWN").upper()}:{device.sysid}:{device.compid}'
    def remove(self,sysid,compid,transport=None):self._devices.pop(self._make_key(sysid,compid,transport),None)
    def all(self):return list(self._devices.values())
    def count(self):return len(self._devices)
    def clear(self):self._devices.clear()
