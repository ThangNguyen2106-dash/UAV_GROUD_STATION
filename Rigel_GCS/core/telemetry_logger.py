from __future__ import annotations

import csv
import math
import os
import time
from datetime import datetime
from typing import Any, Optional


class TelemetryLogger:
    """Thread-safe CSV Telemetry Logger and Safety Monitor."""

    def __init__(self, log_dir: str = "captures/logs") -> None:
        self.log_dir = log_dir
        self._current_file: Optional[str] = None
        self._file_handle = None
        self._csv_writer = None
        self._last_log_time = 0.0
        self._log_interval = 0.2  # 5 Hz logging

        os.makedirs(self.log_dir, exist_ok=True)
        self._start_new_session()

    def _start_new_session(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_file = os.path.join(self.log_dir, f"telemetry_{timestamp}.csv")
        try:
            self._file_handle = open(self._current_file, mode="w", newline="", encoding="utf-8")
            self._csv_writer = csv.writer(self._file_handle)
            self._csv_writer.writerow([
                "timestamp",
                "sysid",
                "transport",
                "latitude",
                "longitude",
                "altitude",
                "relative_altitude",
                "roll_deg",
                "pitch_deg",
                "yaw_deg",
                "ground_speed",
                "climb",
                "voltage_battery",
                "battery_remaining",
                "flight_mode",
                "armed",
                "fix_type",
                "satellites",
            ])
            self._file_handle.flush()
            print(f"[LOGGER] Telemetry log started: {self._current_file}")
        except Exception as exc:
            print(f"[LOGGER ERROR] Failed to start log file: {exc}")

    def log_state(self, state: Any) -> None:
        """Sample and write telemetry row."""
        now = time.monotonic()
        if now - self._last_log_time < self._log_interval or self._csv_writer is None:
            return

        self._last_log_time = now

        roll = getattr(state, "roll", None)
        pitch = getattr(state, "pitch", None)
        yaw = getattr(state, "yaw", None)

        roll_deg = math.degrees(float(roll)) if roll is not None and math.isfinite(float(roll)) else ""
        pitch_deg = math.degrees(float(pitch)) if pitch is not None and math.isfinite(float(pitch)) else ""
        yaw_deg = math.degrees(float(yaw)) if yaw is not None and math.isfinite(float(yaw)) else ""

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            getattr(state, "sysid", ""),
            getattr(state, "transport", ""),
            getattr(state, "latitude", "") or "",
            getattr(state, "longitude", "") or "",
            getattr(state, "altitude", "") or "",
            getattr(state, "relative_altitude", "") or "",
            f"{roll_deg:.2f}" if roll_deg != "" else "",
            f"{pitch_deg:.2f}" if pitch_deg != "" else "",
            f"{yaw_deg:.2f}" if yaw_deg != "" else "",
            getattr(state, "ground_speed", "") or getattr(state, "groundspeed", "") or "",
            getattr(state, "climb", "") or getattr(state, "velocity_z", "") or "",
            getattr(state, "voltage_battery", "") or "",
            getattr(state, "battery_remaining", "") or "",
            getattr(state, "flight_mode", "") or getattr(state, "mode", "") or "",
            "1" if getattr(state, "armed", False) else "0",
            getattr(state, "fix_type", "") or "",
            getattr(state, "satellites_visible", "") or "",
        ]

        try:
            self._csv_writer.writerow(row)
            self._file_handle.flush()
        except Exception as exc:
            print(f"[LOGGER WRITE ERROR] {exc}")

    def close(self) -> None:
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None
            self._csv_writer = None
