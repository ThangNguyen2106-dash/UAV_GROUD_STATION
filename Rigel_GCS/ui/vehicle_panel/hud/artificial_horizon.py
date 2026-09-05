from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class ArtificialHorizon(QWidget):
    """Clear and responsive roll/pitch attitude indicator.

    Positive pitch = nose up.
    Positive roll = right wing down / clockwise aircraft bank.
    The horizon and pitch ladder move with attitude while the aircraft
    reference symbol remains fixed at the center.
    """

    # Pixel movement per degree of pitch. A larger value makes pitch
    # changes visually stronger.
    PITCH_PIXELS_PER_DEGREE = 4.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._roll = 0.0
        self._pitch = 0.0

        self.setMinimumSize(220, 220)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    # ------------------------------------------------------------------
    # TELEMETRY INPUT
    # ------------------------------------------------------------------

    def set_attitude(
        self,
        roll: Optional[float],
        pitch: Optional[float],
    ) -> None:
        changed = False

        if roll is not None:
            try:
                value = float(roll)
                if math.isfinite(value) and value != self._roll:
                    self._roll = value
                    changed = True
            except (TypeError, ValueError):
                pass

        if pitch is not None:
            try:
                value = float(pitch)
                if math.isfinite(value):
                    clamped = max(-89.9, min(89.9, value))
                    if clamped != self._pitch:
                        self._pitch = clamped
                        changed = True
            except (TypeError, ValueError):
                pass

        if changed:
            self.update()

    def set_roll(self, roll: Optional[float]) -> None:
        if roll is None:
            return

        try:
            value = float(roll)
            if math.isfinite(value) and value != self._roll:
                self._roll = value
                self.update()
        except (TypeError, ValueError):
            return

    def set_pitch(self, pitch: Optional[float]) -> None:
        if pitch is None:
            return

        try:
            value = float(pitch)
            if math.isfinite(value):
                clamped = max(-89.9, min(89.9, value))
                if clamped != self._pitch:
                    self._pitch = clamped
                    self.update()
        except (TypeError, ValueError):
            return

    # ------------------------------------------------------------------
    # PAINTING
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)

        try:
            # Keep anti-aliasing only for the important geometry.
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True,
            )

            w = self.width()
            h = self.height()

            if w <= 0 or h <= 0:
                return

            cx = w * 0.5
            cy = h * 0.48

            # Leave room for digital values at the bottom.
            radius = min(w, h - 22) * 0.44

            # ==========================================================
            # BACKGROUND
            # ==========================================================

            painter.fillRect(
                self.rect(),
                QBrush(QColor("#0b0f14")),
            )

            # ==========================================================
            # MOVING HORIZON + PITCH LADDER
            # ==========================================================

            painter.save()
            try:
                # Circular clipping for a clean attitude-indicator face.
                clip_radius = radius

                painter.setClipRect(
                    int(cx - clip_radius),
                    int(cy - clip_radius),
                    int(clip_radius * 2),
                    int(clip_radius * 2),
                )

                painter.translate(cx, cy)

                # Positive roll = right wing down.
                # Therefore the outside world rotates opposite the aircraft.
                painter.rotate(-self._roll)

                # Positive pitch (nose up) moves the horizon DOWN.
                pitch_offset = (
                    self._pitch * self.PITCH_PIXELS_PER_DEGREE
                )
                painter.translate(0.0, pitch_offset)

                extent = max(w, h) * 3.0

                # Sky.
                painter.fillRect(
                    int(-extent),
                    int(-extent * 2),
                    int(extent * 2),
                    int(extent * 2),
                    QBrush(QColor("#2e638c")),
                )

                # Ground.
                painter.fillRect(
                    int(-extent),
                    0,
                    int(extent * 2),
                    int(extent * 2),
                    QBrush(QColor("#70543a")),
                )

                # Strong 0-degree horizon.
                painter.setPen(
                    QPen(QColor("#ffffff"), 2.5)
                )
                painter.drawLine(
                    int(-extent),
                    0,
                    int(extent),
                    0,
                )

                # ======================================================
                # PITCH LADDER
                # ======================================================

                label_size = max(9, min(13, int(radius * 0.075)))
                painter.setFont(
                    QFont(
                        "Arial",
                        label_size,
                        QFont.Weight.Bold,
                    )
                )

                major_half_width = radius * 0.30
                minor_half_width = radius * 0.18

                for pitch_deg in range(-40, 41, 5):
                    if pitch_deg == 0:
                        continue

                    y = -pitch_deg * self.PITCH_PIXELS_PER_DEGREE

                    # Skip completely invisible lines.
                    if y < -h * 1.5 or y > h * 1.5:
                        continue

                    major = abs(pitch_deg) % 10 == 0
                    half_width = (
                        major_half_width
                        if major
                        else minor_half_width
                    )

                    painter.setPen(
                        QPen(
                            QColor("#ffffff"),
                            2.0 if major else 1.2,
                        )
                    )

                    # Main pitch line.
                    painter.drawLine(
                        int(-half_width),
                        int(y),
                        int(half_width),
                        int(y),
                    )

                    # Small vertical end caps make the ladder easier
                    # to read when the drone is strongly pitched.
                    cap = 5 if major else 3

                    painter.drawLine(
                        int(-half_width),
                        int(y - cap),
                        int(-half_width),
                        int(y + cap),
                    )

                    painter.drawLine(
                        int(half_width),
                        int(y - cap),
                        int(half_width),
                        int(y + cap),
                    )

                    if major:
                        text = f"{abs(pitch_deg)}"

                        painter.drawText(
                            int(-half_width - 38),
                            int(y - label_size * 0.1),
                            30,
                            label_size + 8,
                            Qt.AlignmentFlag.AlignRight,
                            text,
                        )

                        painter.drawText(
                            int(half_width + 8),
                            int(y - label_size * 0.1),
                            30,
                            label_size + 8,
                            Qt.AlignmentFlag.AlignLeft,
                            text,
                        )

            finally:
                painter.restore()

            # ==========================================================
            # ROLL SCALE
            # ==========================================================

            painter.save()
            try:
                painter.translate(cx, cy)

                marker_radius = radius * 0.92

                # Tick marks.
                painter.setPen(
                    QPen(QColor("#e9eef2"), 2.0)
                )

                for angle in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
                    rad = math.radians(angle)

                    sin_a = math.sin(rad)
                    cos_a = math.cos(rad)

                    outer_x = sin_a * marker_radius
                    outer_y = -cos_a * marker_radius

                    tick_length = (
                        radius * 0.105
                        if angle in (-30, 0, 30)
                        else radius * 0.065
                    )

                    inner_x = sin_a * (marker_radius - tick_length)
                    inner_y = -cos_a * (marker_radius - tick_length)

                    painter.drawLine(
                        int(outer_x),
                        int(outer_y),
                        int(inner_x),
                        int(inner_y),
                    )

                # Fixed roll pointer.
                painter.setPen(
                    QPen(QColor("#f3c64d"), 3.0)
                )
                painter.setBrush(QColor("#f3c64d"))

                pointer = [
                    (0, int(-marker_radius + 1)),
                    (
                        -int(radius * 0.035),
                        int(-marker_radius + radius * 0.085),
                    ),
                    (
                        int(radius * 0.035),
                        int(-marker_radius + radius * 0.085),
                    ),
                ]

                polygon = QPolygonF(
                    [QPointF(float(x), float(y)) for x, y in pointer]
                )
                painter.drawPolygon(polygon)

                # Current roll number near the top.
                painter.setPen(
                    QPen(QColor("#f3c64d"), 1.5)
                )
                painter.setFont(
                    QFont(
                        "Arial",
                        max(9, min(12, int(radius * 0.07))),
                        QFont.Weight.Bold,
                    )
                )
                painter.drawText(
                    int(-radius * 0.18),
                    int(-radius * 0.72),
                    int(radius * 0.36),
                    18,
                    Qt.AlignmentFlag.AlignCenter,
                    f"{self._roll:+.1f}°",
                )

            finally:
                painter.restore()

            # ==========================================================
            # FIXED AIRCRAFT / WINGS
            # ==========================================================

            painter.save()
            try:
                painter.translate(cx, cy)

                aircraft_pen = QPen(
                    QColor("#f3c64d"),
                    max(3.0, radius * 0.025),
                )
                painter.setPen(aircraft_pen)

                wing = radius * 0.47
                inner = radius * 0.10

                # Strong central aircraft reference.
                painter.drawLine(
                    int(-wing),
                    0,
                    int(-inner),
                    0,
                )
                painter.drawLine(
                    int(inner),
                    0,
                    int(wing),
                    0,
                )

                # Center fuselage.
                painter.drawLine(
                    0,
                    int(-radius * 0.08),
                    0,
                    int(radius * 0.08),
                )

                # Center dot.
                painter.setBrush(QColor("#f3c64d"))
                painter.drawEllipse(
                    int(-radius * 0.025),
                    int(-radius * 0.025),
                    int(radius * 0.05),
                    int(radius * 0.05),
                )

            finally:
                painter.restore()

            # ==========================================================
            # DIGITAL READOUT
            # ==========================================================

            painter.setPen(
                QPen(QColor("#f2f5f7"), 1.0)
            )
            painter.setFont(
                QFont(
                    "Arial",
                    max(9, min(12, int(radius * 0.075))),
                    QFont.Weight.Bold,
                )
            )

            painter.drawText(
                0,
                h - 18,
                w,
                18,
                Qt.AlignmentFlag.AlignCenter,
                f"ROLL {self._roll:+06.1f}°    PITCH {self._pitch:+06.1f}°",
            )

        finally:
            painter.end()
