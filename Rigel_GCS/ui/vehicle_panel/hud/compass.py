from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class Compass(QWidget):
    """Compact heading compass used by the HUD."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._heading = 0.0

        self.setMinimumHeight(72)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_heading(self, heading: Optional[float]) -> None:
        if heading is None:
            return

        try:
            val = float(heading) % 360.0
            if abs(val - self._heading) > 1e-4:
                self._heading = val
                self.update()
        except (TypeError, ValueError):
            return

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)

        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True,
            )

            # Background
            painter.fillRect(
                self.rect(),
                QBrush(QColor("#11161c")),
            )

            w = self.width()
            h = self.height()

            if w <= 0 or h <= 0:
                return

            center_x = w / 2.0
            center_y = h * 0.68

            scale = max(
                0.9,
                min(1.6, w / 430.0),
            )

            pixels_per_degree = 2.0 * scale

            # =====================================================
            # COMPASS SCALE
            # =====================================================

            painter.save()

            try:
                painter.setClipRect(
                    0,
                    0,
                    w,
                    max(0, h - 18),
                )

                painter.setFont(
                    QFont("Arial", 8)
                )

                for relative in range(-90, 91, 10):
                    heading = (
                        self._heading + relative
                    ) % 360.0

                    x = (
                        center_x
                        + relative * pixels_per_degree
                    )

                    major = relative % 30 == 0

                    tick = 13 if major else 7

                    # IMPORTANT:
                    # QPen("#color", width) is not reliable
                    # with the PySide6 version being used.
                    painter.setPen(
                        QPen(
                            QColor("#b8c0c8"),
                            1.0,
                        )
                    )

                    painter.drawLine(
                        int(x),
                        int(center_y - tick),
                        int(x),
                        int(center_y),
                    )

                    if major:
                        label = self._cardinal_or_degree(
                            heading
                        )

                        painter.drawText(
                            int(x - 12),
                            int(center_y - tick - 4),
                            24,
                            12,
                            Qt.AlignmentFlag.AlignCenter,
                            label,
                        )

            finally:
                painter.restore()

            # =====================================================
            # CENTER HEADING POINTER
            # =====================================================

            painter.setPen(
                QPen(
                    QColor("#f3c64d"),
                    2.0,
                )
            )

            painter.drawLine(
                int(center_x),
                8,
                int(center_x),
                int(center_y),
            )

            # =====================================================
            # DIGITAL HEADING
            # =====================================================

            painter.setPen(
                QPen(
                    QColor("#e9eef2"),
                    1.0,
                )
            )

            painter.setFont(
                QFont(
                    "Arial",
                    10,
                    QFont.Weight.Bold,
                )
            )

            painter.drawText(
                0,
                h - 17,
                w,
                17,
                Qt.AlignmentFlag.AlignCenter,
                f"HDG {self._heading:06.1f}°",
            )

        finally:
            # Always release the QPainter even if painting fails.
            painter.end()

    @staticmethod
    def _cardinal_or_degree(degrees: float) -> str:
        rounded = int(round(degrees)) % 360

        names = {
            0: "N",
            90: "E",
            180: "S",
            270: "W",
        }

        return names.get(
            rounded,
            str(rounded),
        )