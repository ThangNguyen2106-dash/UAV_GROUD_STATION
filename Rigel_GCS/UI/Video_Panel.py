import tkinter as tk
from tkinter import ttk

from .Styles import Colors
from ..Module.Mapping.CAMERA_INTERFACE.CAMERA_Device import CameraDevice


class VideoPanel:

    def __init__(
        self,
        parent,
        on_camera_change=None
    ):

        self.on_camera_change = (
            on_camera_change
            or (lambda _index: None)
        )

        self.mounted_widget = None
        self.expand_window = None
        self._changing_camera = False
        self.auto_capture_var = tk.BooleanVar(value=False)
        self.capture_status = None

        # =====================================================
        # FRAME
        # =====================================================

        self.frame = tk.Frame(
            parent,
            bg=Colors.PANEL,
            height=225,
            bd=1,
            relief="solid"
        )

        self.frame.pack(
            fill="x",
            padx=10,
            pady=(8, 6)
        )

        self.frame.pack_propagate(False)

        # =====================================================
        # HEADER
        # =====================================================

        header = tk.Frame(
            self.frame,
            bg=Colors.PANEL
        )

        header.pack(
            fill="x",
            padx=8,
            pady=(5, 4)
        )

        tk.Label(
            header,
            text="📷 CAMERA",
            font=("Segoe UI", 9, "bold"),
            fg=Colors.AMBER,
            bg=Colors.PANEL
        ).pack(side="left")

        self.status = tk.Label(
            header,
            text="NOT CONNECTED",
            font=("Segoe UI", 8, "bold"),
            fg=Colors.TEXT,
            bg=Colors.PANEL
        )

        self.status.pack(side="right")

        # =====================================================
        # CONTROLS
        # =====================================================

        controls = tk.Frame(
            self.frame,
            bg=Colors.PANEL
        )

        controls.pack(
            fill="x",
            padx=8,
            pady=(0, 4)
        )

        tk.Label(
            controls,
            text="Camera:",
            font=("Segoe UI", 8, "bold"),
            fg=Colors.TEXT,
            bg=Colors.PANEL
        ).pack(side="left")
      

        # =====================================================
        # CAMERA SELECTOR
        # =====================================================

        self.camera_var = tk.StringVar(
            value="Camera 0"
        )

        self.camera_box = ttk.Combobox(
            controls,
            textvariable=self.camera_var,
            values=("Camera 0",),
            state="readonly",
            width=12
        )

        self.camera_box.pack(
            side="left",
            padx=(5, 6)
        )

        self.reload_button = tk.Button(
            controls, text="↻", command=self.reload_camera,
            font=("Segoe UI", 9, "bold"), bd=0, relief="flat", cursor="hand2",
            bg="#26313d", fg="white", activebackground="#344454",
            activeforeground="white", padx=7, pady=3
        )
        self.reload_button.pack(side="left", padx=(0, 4))

        self.camera_box.bind(
            "<<ComboboxSelected>>",
            self._camera_selected
        )

        # =====================================================
        # LARGE VIEW
        # =====================================================

        self.expand_button = tk.Button(
            controls,
            text="⛶ Xem cam lớn",
            command=self.open_large_view,
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            bg="#26313d",
            fg="white",
            activebackground="#344454",
            activeforeground="white",
            padx=8,
            pady=3
        )

        self.capture_button = tk.Button(
            controls,
            text="📸 Chụp",
            command=self.capture_photo,
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            bg="#8a5a00",
            fg="white",
            activebackground="#aa7000",
            activeforeground="white",
            padx=8,
            pady=3
        )
        self.capture_button.pack(side="right", padx=(4, 0))

        self.auto_capture_check = tk.Checkbutton(
            controls,
            text="Auto WP",
            variable=self.auto_capture_var,
            font=("Segoe UI", 8, "bold"),
            fg=Colors.TEXT,
            bg=Colors.PANEL,
            activebackground=Colors.PANEL,
            activeforeground=Colors.TEXT,
            selectcolor=Colors.PANEL,
            cursor="hand2",
            padx=2
        )
        self.auto_capture_check.pack(side="right", padx=(4, 0))

        self.expand_button.pack(
            side="right"
        )

        # =====================================================
        # VIDEO HOST
        # =====================================================

        self.host = tk.Frame(
            self.frame,
            bg="#080b0e",
            bd=1,
            relief="solid"
        )

        self.host.pack(
            fill="both",
            expand=True,
            padx=6,
            pady=(0, 6)
        )

        self.placeholder = tk.Label(
            self.host,
            text=(
                "VIDEO MODULE\n"
                "Chưa kết nối camera"
            ),
            justify="center",
            font=("Segoe UI", 10, "bold"),
            fg=Colors.TEXT,
            bg="#080b0e"
        )

        self.placeholder.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        # =====================================================
        # SCAN CAMERA
        # =====================================================
        #
        # Đây là phần quan trọng.
        #
        # VideoPanel sẽ tìm tất cả camera trước khi
        # CameraWidget được mount.
        #
        # =====================================================

        self.refresh_camera_list()

    # =========================================================
    # SCAN CAMERA
    # =========================================================

    def refresh_camera_list(self):

        print(
            "[VideoPanel] "
            "Scanning cameras..."
        )

        try:

            devices = CameraDevice.scan(
                max_devices=10
            )

        except Exception as error:

            print(
                f"[VideoPanel] "
                f"Camera scan error: {error}"
            )

            devices = []

        # =====================================================
        # FALLBACK
        # =====================================================

        if not devices:

            print(
                "[VideoPanel] "
                "No camera detected. "
                "Keeping Camera 0."
            )

            devices = [0]

        print(
            f"[VideoPanel] "
            f"Available cameras: {devices}"
        )

        # =====================================================
        # CREATE DISPLAY VALUES
        # =====================================================

        values = [
            f"Camera {index}"
            for index in devices
        ]

        self.camera_box["values"] = values

        # =====================================================
        # DEFAULT CAMERA
        # =====================================================

        if values:

            current = self.camera_var.get()

            if current in values:

                self.camera_var.set(
                    current
                )

            else:

                self.camera_var.set(
                    values[0]
                )

    # =========================================================
    # CAMERA SELECTED
    # =========================================================

    def _camera_selected(
        self,
        _event=None
    ):

        if self._changing_camera:
            return

        selected = self.camera_box.get()

        if not selected:
            return

        try:

            index = int(
                selected.replace(
                    "Camera ",
                    ""
                )
            )

        except (
            ValueError,
            AttributeError
        ):

            return

        print(
            f"[VideoPanel] "
            f"User selected Camera {index}"
        )

        if self.mounted_widget is None:

            print(
                "[VideoPanel] "
                "CameraWidget not mounted."
            )

            return

        self._changing_camera = True

        try:

            self.set_status(
                f"OPENING CAM {index}"
            )

            success = (
                self.mounted_widget.start_camera(
                    index
                )
            )

            if success:

                self.set_status(
                    f"CAMERA {index} CONNECTED"
                )

            else:

                self.set_status(
                    f"CAMERA {index} FAILED"
                )

        except Exception as error:

            print(
                f"[VideoPanel] "
                f"Camera switch error: {error}"
            )

            self.set_status(
                "CAMERA ERROR"
            )

        finally:

            self._changing_camera = False
        try:
            self.on_camera_change(
                index
            )

        except Exception:

            pass

    # =========================================================
    # RELOAD SELECTED CAMERA
    # =========================================================

    def reload_camera(self):
        if self.mounted_widget is None:
            self.set_status("CAMERA NOT READY")
            return False
        index = self.get_selected_camera_index()
        try:
            self.set_status(f"RELOADING CAM {index}")
            ok = self.mounted_widget.start_camera(index)
            self.set_status(f"CAMERA {index} CONNECTED" if ok else f"CAMERA {index} FAILED")
            return ok
        except Exception as error:
            print(f"[VideoPanel] Reload error: {error}")
            self.set_status("CAMERA ERROR")
            return False

    # =========================================================
    # GET SELECTED CAMERA
    # =========================================================

    def get_selected_camera_index(self):

        selected = self.camera_box.get()

        if not selected:
            return 0

        try:

            return int(
                selected.replace(
                    "Camera ",
                    ""
                )
            )

        except (
            ValueError,
            AttributeError
        ):

            return 0

    # =========================================================
    # SET CAMERA OPTIONS
    # =========================================================

    def set_camera_options(
        self,
        options
    ):

        if not options:

            options = [0]

        normalized = []

        for item in options:

            try:

                index = int(
                    str(item).replace(
                        "Camera ",
                        ""
                    )
                )

                normalized.append(
                    f"Camera {index}"
                )

            except (
                ValueError,
                TypeError
            ):

                continue

        normalized = list(
            dict.fromkeys(
                normalized
            )
        )

        if not normalized:

            normalized = [
                "Camera 0"
            ]

        self.camera_box["values"] = (
            normalized
        )

        current = self.camera_var.get()

        if current in normalized:

            self.camera_var.set(
                current
            )

        else:

            self.camera_var.set(
                normalized[0]
            )

    # =========================================================
    # MOUNT
    # =========================================================

    def mount(
        self,
        widget
    ):

        # -----------------------------------------------------
        # Stop old widget
        # -----------------------------------------------------

        if (
            self.mounted_widget is not None
            and self.mounted_widget is not widget
        ):

            try:
                self.mounted_widget.stop_camera()
            except Exception:
                pass

            try:
                self.mounted_widget.destroy()
            except Exception:
                pass

        self.mounted_widget = widget

        # -----------------------------------------------------
        # Remove placeholder
        # -----------------------------------------------------

        try:

            if self.placeholder.winfo_exists():

                self.placeholder.destroy()

        except tk.TclError:

            pass

        # -----------------------------------------------------
        # Mount widget
        # -----------------------------------------------------

        try:

            widget.pack_forget()

        except Exception:

            pass

        widget.pack(
            fill="both",
            expand=True
        )

        # =====================================================
        # START SELECTED CAMERA
        # =====================================================

        index = (
            self.get_selected_camera_index()
        )

        print(
            f"[VideoPanel] "
            f"Starting selected Camera {index}"
        )

        try:

            success = widget.start_camera(
                index
            )

            if success:

                self.set_status(
                    f"CAMERA {index} CONNECTED"
                )

            else:

                self.set_status(
                    f"CAMERA {index} FAILED"
                )

        except Exception as error:

            print(
                f"[VideoPanel] "
                f"Camera start error: {error}"
            )

            self.set_status(
                "CAMERA ERROR"
            )

    # =========================================================
    # STATUS
    # =========================================================

    def set_status(
        self,
        text
    ):

        try:

            self.status.config(
                text=text
            )

        except tk.TclError:

            pass

    # =========================================================
    # PHOTO CAPTURE
    # =========================================================

    def capture_photo(self, filename=None, output_dir=None):
        """Manually capture the currently selected camera frame."""
        if self.mounted_widget is None:
            self.set_status("CAMERA NOT READY")
            return None

        try:
            path = self.mounted_widget.capture_photo(
                output_dir=output_dir,
                filename=filename,
            )
        except Exception as error:
            print(f"[VideoPanel] Capture error: {error}")
            path = None

        if path:
            self.set_status("PHOTO SAVED")
            self.capture_status = path
            try:
                self.frame.after(1800, lambda: self.set_status(
                    f"CAMERA {self.get_selected_camera_index()} CONNECTED"
                ))
            except tk.TclError:
                pass
        else:
            self.set_status("CAPTURE FAILED")

        return path

    def is_auto_capture_enabled(self):
        return bool(self.auto_capture_var.get())

    # =========================================================
    # LARGE VIEW
    # =========================================================

    def open_large_view(self):

        if self.mounted_widget is None:

            self.set_status(
                "CAMERA NOT READY"
            )

            return

        if self.expand_window is not None:

            try:

                if self.expand_window.winfo_exists():

                    self.expand_window.lift()
                    self.expand_window.focus_force()

                    return

            except tk.TclError:

                pass

        # =====================================================
        # WINDOW
        # =====================================================

        self.expand_window = tk.Toplevel(
            self.frame
        )

        self.expand_window.title(
            "RIGEL - CAMERA VIEW"
        )

        self.expand_window.geometry(
            "900x560"
        )

        self.expand_window.minsize(
            640,
            400
        )

        self.expand_window.configure(
            bg=Colors.BG
        )

        # =====================================================
        # TOP
        # =====================================================

        top = tk.Frame(
            self.expand_window,
            bg=Colors.PANEL
        )

        top.pack(
            fill="x",
            padx=8,
            pady=8
        )

        tk.Label(
            top,
            text=(
                f"📷 {self.camera_var.get()}"
            ),
            font=("Segoe UI", 10, "bold"),
            fg=Colors.AMBER,
            bg=Colors.PANEL
        ).pack(
            side="left",
            padx=8,
            pady=5
        )

        tk.Button(
            top,
            text="Đóng",
            command=self._close_large_view,
            font=("Segoe UI", 8, "bold"),
            bd=0,
            cursor="hand2",
            bg="#26313d",
            fg="white",
            activebackground="#344454",
            activeforeground="white",
            padx=10,
            pady=4
        ).pack(
            side="right",
            padx=6,
            pady=3
        )

        # =====================================================
        # LARGE HOST
        # =====================================================

        large_host = tk.Frame(
            self.expand_window,
            bg="#080b0e",
            bd=1,
            relief="solid"
        )

        large_host.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )

        # =====================================================
        # LARGE CAMERA WIDGET
        # =====================================================

        try:

            camera_class = (
                self.mounted_widget.__class__
            )

            camera = camera_class(
                large_host,
                width=880,
                height=500
            )

            camera.pack(
                fill="both",
                expand=True
            )

            camera_index = (
                self.get_selected_camera_index()
            )

            success = camera.start_camera(
                camera_index
            )

            if not success:

                tk.Label(
                    large_host,
                    text="Không thể mở camera lớn.",
                    font=("Segoe UI", 12, "bold"),
                    fg=Colors.TEXT,
                    bg="#080b0e"
                ).place(
                    relx=0.5,
                    rely=0.5,
                    anchor="center"
                )

            self.expand_window._camera_widget = (
                camera
            )

        except Exception as error:

            print(
                f"[VideoPanel] "
                f"Large camera error: {error}"
            )

            tk.Label(
                large_host,
                text="Không thể mở camera lớn.",
                font=("Segoe UI", 12, "bold"),
                fg=Colors.TEXT,
                bg="#080b0e"
            ).place(
                relx=0.5,
                rely=0.5,
                anchor="center"
            )

        self.expand_window.protocol(
            "WM_DELETE_WINDOW",
            self._close_large_view
        )

    # =========================================================
    # CLOSE LARGE VIEW
    # =========================================================

    def _close_large_view(self):

        if self.expand_window is None:
            return

        try:

            camera = getattr(
                self.expand_window,
                "_camera_widget",
                None
            )

            if camera is not None:

                try:
                    camera.stop_camera()
                except Exception:
                    pass

                try:
                    camera.destroy()
                except Exception:
                    pass

            self.expand_window.destroy()

        except tk.TclError:

            pass

        finally:

            self.expand_window = None

    # =========================================================
    # DESTROY
    # =========================================================

    def destroy(self):

        try:

            self._close_large_view()

        except Exception:

            pass

        if self.mounted_widget is not None:

            try:
                self.mounted_widget.stop_camera()
            except Exception:
                pass

        self.mounted_widget = None

        try:

            self.frame.destroy()

        except tk.TclError:

            pass