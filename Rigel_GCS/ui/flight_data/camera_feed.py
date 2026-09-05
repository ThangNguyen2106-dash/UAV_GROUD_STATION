from __future__ import annotations

import datetime
import math
import os
import time
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


class VideoStreamWorker(QThread):
    """Dedicated background worker thread for low-latency video decoding."""

    frame_received = Signal(QImage)
    status_changed = Signal(str, str)  # status_text, color_hex
    fps_updated = Signal(float)
    error_occurred = Signal(str)

    def __init__(self, source_type: str, source_uri: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.source_type = source_type
        self.source_uri = source_uri
        self._running = False
        self._last_raw_frame = None

    def get_last_raw_frame(self):
        return self._last_raw_frame

    def run(self) -> None:
        self._running = True
        self.status_changed.emit("CONNECTING...", "#f59e0b")
        print(f"[CAMERA] Starting video stream | Source: {self.source_type} | Target: {self.source_uri}")

        if self.source_type == "TEST":
            self._run_test_stream()
            return

        if cv2 is None:
            self.status_changed.emit("ERROR: OpenCV Missing", "#ef4444")
            self.error_occurred.emit("OpenCV (cv2) is not installed in the environment.")
            return

        # Parse target for OpenCV
        target = self.source_uri
        cap = None

        if self.source_type == "USB":
            try:
                target_idx = int(self.source_uri.split()[0])
            except (ValueError, IndexError):
                target_idx = 0

            # Try DirectShow on Windows for fastest camera opening
            if hasattr(cv2, "CAP_DSHOW") and os.name == "nt":
                cap = cv2.VideoCapture(target_idx, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(target_idx)

            # Fallback to index 1 if index 0 failed
            if not cap.isOpened() and target_idx == 0:
                print("[CAMERA] Camera index 0 failed, trying camera index 1...")
                if hasattr(cv2, "CAP_DSHOW") and os.name == "nt":
                    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(1)
        else:
            cap = cv2.VideoCapture(target)

        if cap is None or not cap.isOpened():
            print(f"[CAMERA] ERROR: Could not open video source: {self.source_uri}")
            self.status_changed.emit("FAILED TO OPEN", "#ef4444")
            self.error_occurred.emit(f"Could not open camera ({self.source_uri}). Check if camera is in use by another application.")
            return

        if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        print("[CAMERA] Video stream connected successfully!")
        self.status_changed.emit("LIVE", "#10b981")

        frame_count = 0
        start_time = time.time()

        while self._running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.04)
                continue

            self._last_raw_frame = frame

            # Convert OpenCV BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()

            self.frame_received.emit(qimg)

            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                self.fps_updated.emit(fps)
                frame_count = 0
                start_time = time.time()

            # Small sleep to limit max CPU load
            time.sleep(0.01)

        cap.release()
        print("[CAMERA] Video stream stopped.")
        self.status_changed.emit("NO SIGNAL", "#94a3b8")

    def _run_test_stream(self) -> None:
        """Synthetic FPV camera test pattern generator."""
        self.status_changed.emit("TEST FEED", "#38bdf8")
        w, h = 640, 360
        t = 0.0

        while self._running:
            t += 0.05
            img = QImage(w, h, QImage.Format.Format_RGB32)
            img.fill(QColor("#020617"))

            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # Simulated Horizon background
            pitch_offset = math.sin(t * 0.8) * 30.0
            roll_angle = math.sin(t * 0.5) * 15.0

            painter.save()
            painter.translate(w / 2.0, h / 2.0 + pitch_offset)
            painter.rotate(roll_angle)

            # Sky / Ground
            painter.fillRect(QRectF(-w, -h * 2, w * 2, h * 2), QColor("#0369a1"))
            painter.fillRect(QRectF(-w, 0, w * 2, h * 2), QColor("#14532d"))

            # Horizon line
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(QPointF(-w, 0), QPointF(w, 0))
            painter.restore()

            # Center FPV Crosshair
            painter.setPen(QPen(QColor("#facc15"), 1.5))
            cx, cy = w / 2.0, h / 2.0
            painter.drawLine(QPointF(cx - 20, cy), QPointF(cx - 6, cy))
            painter.drawLine(QPointF(cx + 6, cy), QPointF(cx + 20, cy))
            painter.drawLine(QPointF(cx, cy - 15), QPointF(cx, cy - 5))
            painter.drawLine(QPointF(cx, cy + 5), QPointF(cx, cy + 15))
            painter.drawEllipse(QPointF(cx, cy), 3, 3)

            # OSD Text
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#38bdf8"), 1.0))
            painter.drawText(15, 25, "RIGEL FPV SIMULATOR [TEST PATTERN]")
            now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-4]
            painter.drawText(15, 45, f"TIME: {now_str}")
            painter.drawText(w - 120, 25, "720p 30FPS")

            painter.end()

            self.frame_received.emit(img)
            self.fps_updated.emit(30.0)
            time.sleep(0.033)

        self.status_changed.emit("NO SIGNAL", "#94a3b8")

    def stop(self) -> None:
        self._running = False
        self.wait(1000)


class StreamConfigDialog(QDialog):
    """Stream Configuration Dialog for selecting camera source."""

    def __init__(self, current_type: str, current_uri: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Camera Stream Configuration")
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QDialog {
                background: #0b1329;
                color: #f1f5f9;
            }
            QLabel {
                color: #e2e8f0;
                font-weight: 600;
            }
            QComboBox, QLineEdit {
                background: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton {
                background: #0284c7;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background: #0369a1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["USB", "TEST", "RTSP", "UDP"])
        self.combo_type.setCurrentText(current_type)
        self.combo_type.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Stream Source:", self.combo_type)

        self.input_uri = QLineEdit(current_uri)
        form.addRow("URI / Device:", self.input_uri)

        layout.addLayout(form)

        # Preset hint
        self.hint_label = QLabel()
        self.hint_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.hint_label)
        self._on_type_changed(self.combo_type.currentText())

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background: #334155; color: #cbd5e1;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Connect")
        btn_save.clicked.connect(self.accept)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _on_type_changed(self, stream_type: str) -> None:
        if stream_type == "USB":
            self.input_uri.setEnabled(True)
            if self.input_uri.text() in ("Synthetic FPV Pattern", ""):
                self.input_uri.setText("0")
            self.hint_label.setText("Enter webcam index: 0 for Laptop Camera, 1 for External Camera.")
        elif stream_type == "TEST":
            self.input_uri.setText("Synthetic FPV Pattern")
            self.input_uri.setEnabled(False)
            self.hint_label.setText("Generates a simulated artificial horizon video stream.")
        elif stream_type == "RTSP":
            self.input_uri.setEnabled(True)
            if not self.input_uri.text().startswith("rtsp"):
                self.input_uri.setText("rtsp://192.168.1.100:8554/live")
            self.hint_label.setText("Enter RTSP stream URL from drone/companion computer.")
        elif stream_type == "UDP":
            self.input_uri.setEnabled(True)
            if not self.input_uri.text().startswith("udp"):
                self.input_uri.setText("udp://@:5600")
            self.hint_label.setText("Enter UDP listening URL (e.g., udp://@:5600).")

    def get_config(self) -> tuple[str, str]:
        return self.combo_type.currentText(), self.input_uri.text().strip()


class CameraViewport(QWidget):
    """Full-bleed video rendering viewport with smooth hardware scaling and optional HUD crosshair."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._pixmap: Optional[QPixmap] = None
        self._placeholder_text = "📷 CAMERA STANDBY\nClick '⚡ Connect' or ⚙️ Config"

    def set_frame(self, qimage: QImage) -> None:
        self._pixmap = QPixmap.fromImage(qimage)
        self.update()

    def clear_frame(self, text: str = "📷 CAMERA STANDBY\nClick '⚡ Connect' or ⚙️ Config") -> None:
        self._pixmap = None
        self._placeholder_text = text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = self.rect()

        if self._pixmap is not None and not self._pixmap.isNull():
            # Draw frame filling the entire viewport edge-to-edge
            painter.drawPixmap(rect, self._pixmap)

            # Subtle center crosshair
            cx = rect.width() / 2.0
            cy = rect.height() / 2.0
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1))
            painter.drawLine(QPointF(cx - 10, cy), QPointF(cx - 3, cy))
            painter.drawLine(QPointF(cx + 3, cy), QPointF(cx + 10, cy))
            painter.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy - 3))
            painter.drawLine(QPointF(cx, cy + 3), QPointF(cx, cy + 8))
        else:
            # Dark standby background
            painter.fillRect(rect, QColor("#020617"))
            painter.setPen(QPen(QColor("#334155"), 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))

            painter.setPen(QPen(QColor("#64748b"), 1))
            painter.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Medium))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._placeholder_text)


class CameraFeedWidget(QFrame):
    """Dedicated FPV / Payload Camera Video Feed Slot with edge-to-edge video display."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("CameraFeedWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.source_type = "USB"
        self.source_uri = "0"
        self._worker: Optional[VideoStreamWorker] = None
        self._last_qimage: Optional[QImage] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Header toolbar with title, status, and compact inline action buttons
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        header.setSpacing(4)

        title = QLabel("📹 FPV FEED")
        title.setFont(QFont("Segoe UI", 8.5, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        header.addWidget(title)

        self.stream_status = QLabel("● NO SIGNAL")
        self.stream_status.setFont(QFont("Segoe UI", 7.5, QFont.Weight.Bold))
        self.stream_status.setStyleSheet("color: #94a3b8;")
        header.addWidget(self.stream_status)

        header.addStretch(1)

        self.btn_toggle_cam = QPushButton("⚡ Connect")
        self.btn_toggle_cam.setFixedHeight(20)
        self.btn_toggle_cam.setStyleSheet("""
            QPushButton {
                background: #0284c7;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 7.5pt;
                font-weight: bold;
                padding: 0 6px;
            }
            QPushButton:hover {
                background: #0369a1;
            }
        """)
        self.btn_toggle_cam.clicked.connect(self._toggle_stream)
        header.addWidget(self.btn_toggle_cam)

        self.btn_config = QPushButton("⚙️")
        self.btn_config.setFixedSize(20, 20)
        self.btn_config.setToolTip("Camera Settings")
        self.btn_config.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 2px;
                font-size: 8pt;
                padding: 0;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        self.btn_config.clicked.connect(self._open_config)
        header.addWidget(self.btn_config)

        self.btn_snapshot = QPushButton("📸")
        self.btn_snapshot.setFixedSize(20, 20)
        self.btn_snapshot.setToolTip("Take Snapshot")
        self.btn_snapshot.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 2px;
                font-size: 8pt;
                padding: 0;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        self.btn_snapshot.clicked.connect(self._take_snapshot)
        header.addWidget(self.btn_snapshot)

        layout.addLayout(header)

        # Full-bleed Video Viewport (Expands to fill available vertical space)
        self.viewport = CameraViewport(self)
        self.viewport.setMinimumHeight(140)
        self.viewport.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.viewport, 1)

    def _toggle_stream(self) -> None:
        if self._worker and self._worker.isRunning():
            self._stop_stream()
        else:
            self._start_stream()

    def _start_stream(self) -> None:
        self._stop_stream()

        self._worker = VideoStreamWorker(self.source_type, self.source_uri)
        self._worker.frame_received.connect(self._on_frame_received)
        self._worker.status_changed.connect(self._on_status_changed)
        self._worker.fps_updated.connect(self._on_fps_updated)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

        self.btn_toggle_cam.setText("⏹ Stop")
        self.btn_toggle_cam.setStyleSheet("""
            QPushButton {
                background: #dc2626;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 7.5pt;
                font-weight: bold;
                padding: 0 6px;
            }
            QPushButton:hover {
                background: #b91c1c;
            }
        """)

    def _stop_stream(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker = None

        self.btn_toggle_cam.setText("⚡ Connect")
        self.btn_toggle_cam.setStyleSheet("""
            QPushButton {
                background: #0284c7;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 7.5pt;
                font-weight: bold;
                padding: 0 6px;
            }
            QPushButton:hover {
                background: #0369a1;
            }
        """)
        self.viewport.clear_frame("📷 CAMERA STANDBY\nClick '⚡ Connect' or ⚙️ Config")
        self.stream_status.setText("● NO SIGNAL")
        self.stream_status.setStyleSheet("color: #94a3b8;")

    def _open_config(self) -> None:
        dlg = StreamConfigDialog(self.source_type, self.source_uri, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.source_type, self.source_uri = dlg.get_config()
            self._start_stream()

    def _on_frame_received(self, qimage: QImage) -> None:
        self._last_qimage = qimage
        self.viewport.set_frame(qimage)

    def _on_status_changed(self, status_text: str, color_hex: str) -> None:
        self.stream_status.setText(f"● {status_text}")
        self.stream_status.setStyleSheet(f"color: {color_hex}; font-weight: bold;")

    def _on_fps_updated(self, fps: float) -> None:
        pass

    def _on_error(self, err_msg: str) -> None:
        QMessageBox.warning(self, "Camera Stream Error", err_msg)
        self._stop_stream()

    def _take_snapshot(self) -> None:
        if self._last_qimage is None:
            QMessageBox.information(self, "Snapshot", "No video frame available to capture.")
            return

        snapshots_dir = os.path.join("captures", "snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        filepath = os.path.join(snapshots_dir, filename)

        success = self._last_qimage.save(filepath, "JPG", 95)
        if success:
            QMessageBox.information(self, "Snapshot Saved", f"Image saved successfully to:\n{filepath}")
        else:
            QMessageBox.warning(self, "Snapshot Error", "Failed to save snapshot image file.")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_stream()
        super().closeEvent(event)


