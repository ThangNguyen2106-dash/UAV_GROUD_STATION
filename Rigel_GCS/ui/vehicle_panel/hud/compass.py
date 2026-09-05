from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget


class Compass(QWidget):
    """Horizontal HUD Heading Tape with Smooth Continuous Sliding Animation.

    Features:
    - Smooth animated scrolling across 360° using shortest-arc interpolation.
    - Continuous wrapping ribbon with precision tick marks (every 5°, 10°, 30°).
    - Cardinal labels ('N' in bright red, 'E', 'S', 'W' in cyan) + degree numbers.
    - Center Lubber pointer with glowing digital heading readout.
    - Compact height (~42px) designed for maximum vertical room for camera/HUD.
    """

    ANIM_INTERVAL_MS = 16  # ~60 FPS smooth interpolation

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._target_heading = 0.0
        self._current_heading = 0.0

        self.setMinimumHeight(40)
        self.setMaximumHeight(46)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # 60 FPS smooth animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(self.ANIM_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_timer.start()

    def set_heading(self, heading: Optional[float]) -> None:
        """Set target heading in degrees [0, 360)."""
        if heading is None:
            return

        try:
            val = float(heading) % 360.0
            if math.isfinite(val):
                self._target_heading = val
        except (TypeError, ValueError):
            pass

    def _animate_step(self) -> None:
        """Smoothly slide the heading tape toward target heading using shortest arc."""
        diff = (self._target_heading - self._current_heading + 540.0) % 360.0 - 180.0
        if abs(diff) > 0.03:
            # Smooth dampening easing for fluid sliding tape
            self._current_heading = (self._current_heading + diff * 0.22) % 360.0
            self.update()
        elif abs(diff) > 0.001:
            self._current_heading = self._target_heading
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            w = self.width()
            h = self.height()
            if w <= 0 or h <= 0:
                return

            # 1. Dark HUD Ribbon Background
            painter.fillRect(self.rect(), QBrush(QColor("#020617")))

            center_x = w / 2.0
            tape_baseline = h * 0.58

            # Responsive pixels per degree
            scale = max(0.9, min(1.4, w / 360.0))
            pixels_per_deg = 2.4 * scale

            # 2. Draw Sliding Scale with clipping
            painter.save()
            painter.setClipRect(0, 0, w, h)

            # Visible span in degrees (e.g. ±75° from center)
            half_span = int(math.ceil((w / 2.0) / pixels_per_deg)) + 10
            cur_hdg = self._current_heading

            # Draw ticks every 5 degrees
            start_deg = int(math.floor((cur_hdg - half_span) / 5.0) * 5)
            end_deg = int(math.ceil((cur_hdg + half_span) / 5.0) * 5)

            for deg_raw in range(start_deg, end_deg + 1, 5):
                offset = deg_raw - cur_hdg
                x = center_x + offset * pixels_per_deg

                if x < -30 or x > w + 30:
                    continue

                actual_deg = (deg_raw % 360 + 360) % 360
                is_major = (actual_deg % 30 == 0)
                is_medium = (actual_deg % 10 == 0)
                is_cardinal = (actual_deg % 90 == 0)

                # Tick mark lengths
                if is_major:
                    tick_len = 10.0
                    painter.setPen(QPen(QColor("#38bdf8" if is_cardinal else "#94a3b8"), 1.4 if is_cardinal else 1.0))
                elif is_medium:
                    tick_len = 6.0
                    painter.setPen(QPen(QColor("#64748b"), 0.9))
                else:
                    tick_len = 3.5
                    painter.setPen(QPen(QColor("#334155"), 0.8))

                painter.drawLine(QPointF(x, tape_baseline - tick_len), QPointF(x, tape_baseline))

                # Labels for Major / Cardinal ticks
                if is_major:
                    label = self._cardinal_or_degree(actual_deg)
                    if actual_deg == 0:
                        painter.setPen(QPen(QColor("#ef4444"), 1.0))
                        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    elif is_cardinal:
                        painter.setPen(QPen(QColor("#38bdf8"), 1.0))
                        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    else:
                        painter.setPen(QPen(QColor("#94a3b8"), 1.0))
                        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))

                    painter.drawText(
                        QRectF(x - 14, tape_baseline - tick_len - 13, 28, 13),
                        Qt.AlignmentFlag.AlignCenter,
                        label,
                    )

            # Tape bottom baseline
            painter.setPen(QPen(QColor("#1e293b"), 1.0))
            painter.drawLine(QPointF(0, tape_baseline), QPointF(w, tape_baseline))

            # Edge side fade gradients (left & right vignette)
            grad_left = QLinearGradient(0, 0, 45, 0)
            grad_left.setColorAt(0.0, QColor(2, 6, 23, 255))
            grad_left.setColorAt(1.0, QColor(2, 6, 23, 0))
            painter.fillRect(QRectF(0, 0, 45, h), QBrush(grad_left))

            grad_right = QLinearGradient(w - 45, 0, w, 0)
            grad_right.setColorAt(0.0, QColor(2, 6, 23, 0))
            grad_right.setColorAt(1.0, QColor(2, 6, 23, 255))
            painter.fillRect(QRectF(w - 45, 0, 45, h), QBrush(grad_right))

            painter.restore()

            # =========================================================
            # 3. CENTER LUBBER POINTER (Yellow Triangle pointing down)
            # =========================================================
            pointer = QPolygonF([
                QPointF(center_x, tape_baseline + 1),
                QPointF(center_x - 4, tape_baseline + 7),
                QPointF(center_x + 4, tape_baseline + 7),
            ])
            painter.setPen(QPen(QColor("#f59e0b"), 1.0))
            painter.setBrush(QBrush(QColor("#fbbf24")))
            painter.drawPolygon(pointer)

            # Center vertical indicator line
            painter.setPen(QPen(QColor("#f59e0b"), 1.5))
            painter.drawLine(QPointF(center_x, 2), QPointF(center_x, tape_baseline - 1))

            # =========================================================
            # 4. DIGITAL HEADING BOX AT BOTTOM
            # =========================================================
            hdg_int = int(round(self._current_heading)) % 360
            cardinal = self._get_cardinal_name(hdg_int)
            readout_text = f"{hdg_int:03d}° {cardinal}"

            badge_w = 64
            badge_rect = QRectF(center_x - badge_w / 2.0, h - 13, badge_w, 12)
            painter.setBrush(QBrush(QColor("#090e1f")))
            painter.setPen(QPen(QColor("#0284c7"), 0.8))
            painter.drawRoundedRect(badge_rect, 2, 2)

            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#38bdf8"), 1.0))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, readout_text)

        finally:
            painter.end()

    @staticmethod
    def _cardinal_or_degree(degrees: int) -> str:
        names = {
            0: "N",
            90: "E",
            180: "S",
            270: "W",
        }
        if degrees in names:
            return names[degrees]
        return f"{degrees // 10:02d}"

    @staticmethod
    def _get_cardinal_name(degrees: int) -> str:
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = int((degrees + 11.25) / 22.5) % 16
        return dirs[idx]
