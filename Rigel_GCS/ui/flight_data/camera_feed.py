from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CameraFeedWidget(QFrame):
    """Dedicated FPV / Payload Camera Video Feed Slot."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("CameraFeedWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._is_streaming = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header toolbar
        header = QHBoxLayout()
        header.setSpacing(6)

        title = QLabel("📹 FPV / CAMERA STREAM")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        header.addWidget(title)

        header.addStretch(1)

        self.stream_status = QLabel("● NO SIGNAL")
        self.stream_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.stream_status.setStyleSheet("color: #94a3b8;")
        header.addWidget(self.stream_status)

        layout.addLayout(header)

        # Video Frame Container (16:9 ratio slot)
        self.video_container = QFrame()
        self.video_container.setStyleSheet("""
            QFrame {
                background: #020617;
                border: 1px solid #1e293b;
                border-radius: 4px;
            }
        """)
        self.video_container.setMinimumHeight(160)
        self.video_container.setMaximumHeight(320)

        v_layout = QVBoxLayout(self.video_container)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.setSpacing(4)

        icon = QLabel("📷")
        icon.setFont(QFont("Segoe UI", 24))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(icon)

        self.msg_label = QLabel("CAMERA FEED STANDBY\n(Ready for RTSP / UDP / USB Stream)")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_label.setFont(QFont("Segoe UI", 9))
        self.msg_label.setStyleSheet("color: #64748b;")
        v_layout.addWidget(self.msg_label)

        layout.addWidget(self.video_container)

        # Bottom Quick Controls
        footer = QHBoxLayout()
        footer.setSpacing(4)

        self.btn_toggle_cam = QPushButton("Connect Stream")
        self.btn_toggle_cam.setFixedHeight(22)
        self.btn_toggle_cam.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 3px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        footer.addWidget(self.btn_toggle_cam)

        self.btn_snapshot = QPushButton("📸 Snapshot")
        self.btn_snapshot.setFixedHeight(22)
        self.btn_snapshot.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 3px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        footer.addWidget(self.btn_snapshot)

        footer.addStretch(1)

        self.res_label = QLabel("720p 30fps")
        self.res_label.setStyleSheet("color: #64748b; font-size: 8px;")
        footer.addWidget(self.res_label)

        layout.addLayout(footer)
