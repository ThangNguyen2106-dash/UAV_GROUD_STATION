from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from serial.tools import list_ports
except Exception:  # pragma: no cover
    list_ports = None


class NoWheelSpinBox(QSpinBox):
    """Do not change numeric values while scrolling with the mouse wheel."""
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class ConnectionSelector(QGroupBox):
    """Top-bar link selector.

    This widget only collects connection settings and emits a request.
    It does not open Serial/UDP itself.
    """

    connect_requested = Signal(dict)
    disconnect_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("SOURCE", parent)
        self._build_ui()
        self.refresh_serial_ports()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        row = QHBoxLayout()
        row.addWidget(QLabel("Type"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["AUTO", "SERIAL", "UDP"])
        self.source_combo.currentTextChanged.connect(self._source_changed)
        row.addWidget(self.source_combo, 1)
        root.addLayout(row)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_auto_page())
        self.stack.addWidget(self._build_serial_page())
        self.stack.addWidget(self._build_udp_page())
        root.addWidget(self.stack)

        buttons = QHBoxLayout()
        self.connect_button = QPushButton("CONNECT")
        self.connect_button.clicked.connect(self._emit_connect)
        self.disconnect_button = QPushButton("DISCONNECT")
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.disconnect_button)
        root.addLayout(buttons)

    def _build_auto_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.auto_info = QLabel("Automatic discovery / default UDP endpoint")
        self.auto_info.setWordWrap(True)
        layout.addRow(self.auto_info)
        return page

    def _build_serial_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)

        self.serial_combo = QComboBox()
        self.serial_combo.setMinimumWidth(150)
        layout.addRow("COM", self.serial_combo)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["57600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")
        layout.addRow("Baud", self.baud_combo)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_serial_ports)
        layout.addRow("", refresh)
        return page

    def _build_udp_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)

        self.udp_rx_host = QLineEdit("0.0.0.0")
        self.udp_rx_port = NoWheelSpinBox()
        self.udp_rx_port.setRange(1, 65535)
        self.udp_rx_port.setValue(14550)
        layout.addRow("RX Host", self.udp_rx_host)
        layout.addRow("RX Port", self.udp_rx_port)

        self.udp_tx_host = QLineEdit("127.0.0.1")
        self.udp_tx_port = NoWheelSpinBox()
        self.udp_tx_port.setRange(1, 65535)
        self.udp_tx_port.setValue(14560)
        layout.addRow("TX Host", self.udp_tx_host)
        layout.addRow("TX Port", self.udp_tx_port)
        return page

    def _source_changed(self, source: str) -> None:
        self.stack.setCurrentIndex({"AUTO": 0, "SERIAL": 1, "UDP": 2}.get(source, 0))
        if source == "SERIAL":
            self.refresh_serial_ports()

    def refresh_serial_ports(self) -> None:
        if not hasattr(self, "serial_combo"):
            return
        current = self.serial_combo.currentData()
        self.serial_combo.clear()
        if list_ports is None:
            self.serial_combo.addItem("Serial unavailable", None)
            return
        try:
            ports = sorted(list_ports.comports(), key=lambda p: p.device)
        except Exception as exc:
            self.serial_combo.addItem(f"Scan error: {exc}", None)
            return
        for port in ports:
            label = port.device
            if port.description:
                label += f" — {port.description}"
            self.serial_combo.addItem(label, port.device)
        if current:
            idx = self.serial_combo.findData(current)
            if idx >= 0:
                self.serial_combo.setCurrentIndex(idx)
        if self.serial_combo.count() == 0:
            self.serial_combo.addItem("No COM port", None)

    def _emit_connect(self) -> None:
        source = self.source_combo.currentText()
        if source == "SERIAL":
            self.connect_requested.emit({
                "source": "SERIAL",
                "port": self.serial_combo.currentData(),
                "baudrate": int(self.baud_combo.currentText()),
            })
        elif source == "UDP":
            self.connect_requested.emit({
                "source": "UDP",
                "rx_host": self.udp_rx_host.text().strip() or "0.0.0.0",
                "rx_port": self.udp_rx_port.value(),
                "tx_host": self.udp_tx_host.text().strip() or "127.0.0.1",
                "tx_port": self.udp_tx_port.value(),
            })
        else:
            self.connect_requested.emit({"source": "AUTO"})
    