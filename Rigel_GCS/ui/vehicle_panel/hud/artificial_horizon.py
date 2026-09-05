from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget


class ArtificialHorizon(QWidget):
    """Full-bleed high-resolution Attitude Director Indicator (Artificial Horizon).

    Fills 100% of the container width and height with dynamic scaling,
    smooth pitch ladder, roll arc, and aircraft reference reticle.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._roll = 0.0
        self._pitch = 0.0

        self.setMinimumSize(220, 160)
        self.setMaximumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

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
            pass

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
            pass

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)

        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            w = self.width()
            h = self.height()

            if w <= 0 or h <= 0:
                return

            cx = w * 0.5
            cy = h * 0.5

            # Dynamic pitch pixels scaling based on viewport height (15 deg per half-height)
            pitch_pixels_per_deg = max(2.5, h / 28.0)

            # 1. Full-Bleed Viewport Clip
            painter.setClipRect(0, 0, w, h)

            # ==========================================================
            # MOVING SKY / GROUND / HORIZON
            # ==========================================================
            painter.save()
            try:
                painter.translate(cx, cy)
                painter.rotate(-self._roll)

                pitch_offset = self._pitch * pitch_pixels_per_deg
                painter.translate(0.0, pitch_offset)

                extent = max(w, h) * 4.0

                # Sky Gradient (Deep Sky Blue to Horizon)
                sky_grad = QLinearGradient(0, -extent, 0, 0)
                sky_grad.setColorAt(0.0, QColor("#1e3a8a"))
                sky_grad.setColorAt(1.0, QColor("#0284c7"))
                painter.fillRect(
                    int(-extent),
                    int(-extent),
                    int(extent * 2),
                    int(extent),
                    QBrush(sky_grad),
                )

                # Ground Gradient (Horizon Earth Brown to Deep Brown)
                ground_grad = QLinearGradient(0, 0, 0, extent)
                ground_grad.setColorAt(0.0, QColor("#78350f"))
                ground_grad.setColorAt(1.0, QColor("#451a03"))
                painter.fillRect(
                    int(-extent),
                    0,
                    int(extent * 2),
                    int(extent),
                    QBrush(ground_grad),
                )

                # Horizon Dividing Line
                painter.setPen(QPen(QColor("#ffffff"), 2.5))
                painter.drawLine(int(-extent), 0, int(extent), 0)

                # ======================================================
                # PITCH LADDER
                # ======================================================
                major_half_w = min(w * 0.26, 75.0)
                minor_half_w = min(w * 0.15, 42.0)
                font_size = max(8, min(11, int(h * 0.07)))
                painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))

                for pitch_deg in range(-40, 41, 5):
                    if pitch_deg == 0:
                        continue

                    y = -pitch_deg * pitch_pixels_per_deg
                    if y < -h * 2.0 or y > h * 2.0:
                        continue

                    is_major = abs(pitch_deg) % 10 == 0
                    half_w = major_half_w if is_major else minor_half_w

                    painter.setPen(
                        QPen(
                            QColor("#ffffff" if is_major else "#e2e8f0"),
                            2.0 if is_major else 1.2,
                        )
                    )

                    painter.drawLine(int(-half_w), int(y), int(half_w), int(y))

                    # Vertical end ticks
                    cap_h = 4 if is_major else 2.5
                    painter.drawLine(int(-half_w), int(y - cap_h), int(-half_w), int(y + cap_h))
                    painter.drawLine(int(half_w), int(y - cap_h), int(half_w), int(y + cap_h))

                    # Pitch Degree Labels
                    if is_major:
                        text = f"{abs(pitch_deg)}"
                        painter.drawText(
                            int(-half_w - 32),
                            int(y - font_size * 0.6),
                            28,
                            font_size + 6,
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                            text,
                        )
                        painter.drawText(
                            int(half_w + 4),
                            int(y - font_size * 0.6),
                            28,
                            font_size + 6,
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                            text,
                        )
            finally:
                painter.restore()

            # ==========================================================
            # ROLL ANGLE ARC & TICKS (TOP OF VIEWPORT)
            # ==========================================================
            painter.save()
            try:
                painter.translate(cx, cy)
                arc_radius = min(cx, cy) * 0.90

                painter.setPen(QPen(QColor("#f8fafc"), 1.5))
                for angle in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
                    rad = math.radians(angle)
                    sin_a = math.sin(rad)
                    cos_a = math.cos(rad)

                    is_major_roll = abs(angle) in (0, 30, 60)
                    tick_len = 8 if is_major_roll else 5

                    out_x = sin_a * arc_radius
                    out_y = -cos_a * arc_radius
                    in_x = sin_a * (arc_radius - tick_len)
                    in_y = -cos_a * (arc_radius - tick_len)

                    painter.drawLine(int(out_x), int(out_y), int(in_x), int(in_y))

                # Roll Pointer (Zero Mark Triangle)
                painter.setPen(QPen(QColor("#facc15"), 1.5))
                painter.setBrush(QBrush(QColor("#facc15")))
                poly = [
                    QPointF(0.0, -arc_radius + 2.0),
                    QPointF(-5.0, -arc_radius + 10.0),
                    QPointF(5.0, -arc_radius + 10.0),
                ]
                painter.drawPolygon(QPolygonF(poly))
            finally:
                painter.restore()

            # ==========================================================
            # FIXED AIRCRAFT SYMBOL (CROSSHAIR / WINGS IN CENTER)
            # ==========================================================
            painter.save()
            try:
                painter.translate(cx, cy)

                wing_span = min(w * 0.28, 60.0)
                inner_gap = min(w * 0.08, 16.0)

                pen_wings = QPen(QColor("#facc15"), 3.5)
                pen_wings.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen_wings)

                # Left Wing
                painter.drawLine(int(-wing_span), 0, int(-inner_gap), 0)
                # Left Wing L-tip
                painter.drawLine(int(-wing_span), 0, int(-wing_span), 6)

                # Right Wing
                painter.drawLine(int(inner_gap), 0, int(wing_span), 0)
                # Right Wing L-tip
                painter.drawLine(int(wing_span), 0, int(wing_span), 6)

                # Center Fuselage Pip / Dot
                painter.setBrush(QBrush(QColor("#facc15")))
                painter.drawEllipse(QPointF(0, 0), 3.5, 3.5)
            finally:
                painter.restore()

            # Outer subtle border
            painter.setPen(QPen(QColor("#334155"), 1.0))
            painter.drawRect(0, 0, w - 1, h - 1)

        finally:
            painter.end()
