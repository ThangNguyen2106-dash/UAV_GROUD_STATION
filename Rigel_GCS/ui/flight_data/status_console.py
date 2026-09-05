from __future__ import annotations

import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class StatusConsoleWidget(QFrame):
    """Realtime MAVLink STATUSTEXT message log console."""

    # MAVLink Severity levels:
    # 0=EMERGENCY, 1=ALERT, 2=CRITICAL, 3=ERROR, 4=WARNING, 5=NOTICE, 6=INFO, 7=DEBUG
    SEVERITY_COLORS = {
        0: "#ef4444",  # Red
        1: "#ef4444",  # Red
        2: "#ef4444",  # Red
        3: "#f87171",  # Light Red
        4: "#f59e0b",  # Amber / Yellow
        5: "#38bdf8",  # Sky Blue
        6: "#94a3b8",  # Slate Gray (Normal Info)
        7: "#64748b",  # Dim Gray (Debug)
    }

    SEVERITY_TAGS = {
        0: "[EMERGENCY]",
        1: "[ALERT]",
        2: "[CRITICAL]",
        3: "[ERROR]",
        4: "[WARNING]",
        5: "[NOTICE]",
        6: "[INFO]",
        7: "[DEBUG]",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusConsoleWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header toolbar
        header = QHBoxLayout()
        header.setSpacing(6)

        title = QLabel("📟 AUTOPILOT CONSOLE (STATUSTEXT)")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        header.addWidget(title)

        header.addStretch(1)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedHeight(22)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 3px;
                padding: 0 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_logs)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        # Text Console
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #090d16;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.log_text.setMinimumHeight(80)
        self.log_text.setMaximumHeight(140)
        layout.addWidget(self.log_text)

    def add_message(self, text: str, severity: int = 6) -> None:
        """Append a timestamped message from MAVLink STATUSTEXT."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        color = self.SEVERITY_COLORS.get(severity, "#94a3b8")
        tag = self.SEVERITY_TAGS.get(severity, "[INFO]")

        clean_text = text.strip()
        html_msg = f'<span style="color:#64748b;">[{now}]</span> <b style="color:{color};">{tag}</b> <span style="color:#e2e8f0;">{clean_text}</span>'
        
        self.log_text.append(html_msg)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self) -> None:
        self.log_text.clear()
