"""
Camera preview widget for RIGEL Ground Station.

IMPORTANT ARCHITECTURE:

    VideoPanel
        └── Camera selector
                ↓
        CameraWidget.start_camera(index)
                ↓
        CameraDevice
                ↓
        OpenCV camera

CameraWidget CHỈ chịu trách nhiệm:
    - Hiển thị video
    - Start camera theo index được truyền vào
    - Stop camera
    - Read frame
    - Resize giữ đúng aspect ratio
    - Không mirror hình ảnh
    - Quản lý duy nhất một frame-update loop

CameraWidget KHÔNG có:
    - Camera Combobox
    - Camera selector
    - Camera list
    - Camera selection callback

Camera selector duy nhất nằm trong VideoPanel.
"""

import tkinter as tk
from datetime import datetime
from pathlib import Path

import cv2
from PIL import Image, ImageTk

from .CAMERA_Device import CameraDevice


class CameraWidget(tk.Frame):

    # =========================================================
    # CAMERA SETTINGS
    # =========================================================

    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720

    UPDATE_INTERVAL = 30

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        parent,
        width=256,
        height=160,
        **kwargs
    ):

        super().__init__(
            parent,
            bg="#080808",
            highlightthickness=1,
            highlightbackground="#3A3A3A",
            **kwargs
        )

        # =====================================================
        # PREVIEW SIZE
        # =====================================================

        self.preview_width = width
        self.preview_height = height

        # =====================================================
        # CAMERA STATE
        # =====================================================

        self.camera = None

        self.running = False

        self.device_index = 0

        self.photo = None

        # Latest raw BGR frame. Used for manual/automatic capture.
        self.latest_frame = None

        # after() ID
        self.after_id = None

        self.destroyed = False

        # =====================================================
        # VIDEO AREA ONLY
        # =====================================================
        #
        # KHÔNG CÓ COMBOBOX.
        #
        # KHÔNG CÓ CAMERA SELECTOR.
        #
        # KHÔNG CÓ CONTROL BAR.
        #
        # =====================================================

        self.video_frame = tk.Frame(
            self,
            bg="black"
        )

        self.video_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        # =====================================================
        # VIDEO LABEL
        # =====================================================

        self.video_label = tk.Label(
            self.video_frame,
            bg="black",
            fg="white",
            bd=0,
            highlightthickness=0,
            text="NO CAMERA",
            font=(
                "Segoe UI",
                10
            )
        )

        self.video_label.pack(
            fill=tk.BOTH,
            expand=True
        )

        # =====================================================
        # INITIAL STATUS
        # =====================================================

        self.video_label.config(
            text="NO CAMERA"
        )

    # =========================================================
    # START CAMERA
    # =========================================================

    def start_camera(
        self,
        device_index=0
    ):
        """
        Start exactly one camera.

        Camera index được truyền từ VideoPanel.

        Ví dụ:

            camera_widget.start_camera(0)
            camera_widget.start_camera(1)

        Không có camera selector trong widget này.
        """

        if self.destroyed:

            return False

        # =====================================================
        # VALIDATE INDEX
        # =====================================================

        try:

            device_index = int(
                device_index
            )

        except (
            TypeError,
            ValueError
        ):

            device_index = 0

        print(
            f"[CameraWidget] "
            f"Starting Camera {device_index}"
        )

        # =====================================================
        # STOP CURRENT CAMERA
        # =====================================================

        self.stop_camera()

        # =====================================================
        # SAVE INDEX
        # =====================================================

        self.device_index = (
            device_index
        )

        # =====================================================
        # SHOW OPENING STATUS
        # =====================================================

        try:

            self.video_label.config(
                image="",
                text=(
                    f"OPENING CAMERA "
                    f"{device_index}..."
                ),
                fg="white",
                bg="black"
            )

            self.update_idletasks()

        except tk.TclError:

            return False

        self.photo = None
        self.latest_frame = None

        # =====================================================
        # CREATE CAMERA DEVICE
        # =====================================================

        self.camera = CameraDevice(
            device_index=device_index,
            width=self.CAMERA_WIDTH,
            height=self.CAMERA_HEIGHT
        )

        # =====================================================
        # OPEN CAMERA
        # =====================================================

        if not self.camera.open():

            print(
                f"[CameraWidget] "
                f"Failed to open Camera "
                f"{device_index}"
            )

            self.camera = None

            self.running = False

            try:

                self.video_label.config(
                    image="",
                    text=(
                        "NO CAMERA\n"
                        f"Camera {device_index}"
                    ),
                    fg="white",
                    bg="black"
                )

            except tk.TclError:

                pass

            return False

        # =====================================================
        # CAMERA READY
        # =====================================================

        print(
            f"[CameraWidget] "
            f"Camera {device_index} READY"
        )

        self.running = True

        try:

            self.video_label.config(
                image="",
                text=""
            )

        except tk.TclError:

            pass

        # =====================================================
        # START FRAME LOOP
        # =====================================================

        self._schedule_frame(
            delay=0
        )

        return True

    # =========================================================
    # CAPTURE PHOTO
    # =========================================================

    def capture_photo(self, output_dir=None, filename=None):
        """Save the latest camera frame as a JPEG photo.

        Returns the saved path, or None when no valid frame exists.
        """
        if self.destroyed or not self.running or self.camera is None:
            return None

        frame = self.latest_frame
        if frame is None:
            # Try one immediate read if the display loop has not produced a frame yet.
            try:
                frame = self.camera.read()
            except Exception:
                frame = None

        if frame is None:
            return None

        try:
            if output_dir is None:
                # Keep captures beside the project source, independent of cwd.
                output_dir = Path(__file__).resolve().parents[4] / "captures"
            else:
                output_dir = Path(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)

            if not filename:
                filename = datetime.now().strftime("IMG_%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"
            elif not str(filename).lower().endswith(".jpg"):
                filename = f"{filename}.jpg"

            path = output_dir / str(filename)

            ok = cv2.imwrite(str(path), frame)
            if not ok:
                return None

            print(f"[CameraWidget] Photo captured: {path}")
            return str(path)

        except Exception as error:
            print(f"[CameraWidget] Capture error: {error}")
            return None

    # =========================================================
    # RELOAD CAMERA
    # =========================================================

    def reload_camera(self):
        """
        Reload current camera.

        VideoPanel không cần gọi hàm này
        để chọn camera mới.
        """

        if self.destroyed:

            return False

        index = self.device_index

        print(
            f"[CameraWidget] "
            f"Reload Camera {index}"
        )

        return self.start_camera(
            index
        )

    # =========================================================
    # SCHEDULE FRAME
    # =========================================================

    def _schedule_frame(
        self,
        delay=None
    ):
        """
        Schedule exactly ONE frame update.

        Không cho phép tạo nhiều after()
        callback cùng lúc.
        """

        if self.destroyed:
            return

        if not self.running:
            return

        if self.after_id is not None:
            return

        if delay is None:

            delay = (
                self.UPDATE_INTERVAL
            )

        try:

            self.after_id = self.after(
                delay,
                self._update_frame
            )

        except tk.TclError:

            self.after_id = None

    # =========================================================
    # UPDATE FRAME
    # =========================================================

    def _update_frame(self):
        """
        Read and display one camera frame.
        """

        # Callback đang chạy
        self.after_id = None

        # =====================================================
        # VALIDATE
        # =====================================================

        if self.destroyed:
            return

        if not self.running:
            return

        if self.camera is None:
            return

        # =====================================================
        # READ FRAME
        # =====================================================

        frame = self.camera.read()

        if frame is None:

            self._show_no_signal()

            return

        # Keep the original BGR frame for photo capture.
        self.latest_frame = frame.copy()

        # =====================================================
        # BGR -> RGB
        # =====================================================

        try:

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

        except Exception as error:

            print(
                f"[CameraWidget] "
                f"Color conversion error: "
                f"{error}"
            )

            self._show_no_signal()

            return

        # =====================================================
        # GET DISPLAY SIZE
        # =====================================================

        width = (
            self.video_label.winfo_width()
        )

        height = (
            self.video_label.winfo_height()
        )

        # =====================================================
        # RESIZE KEEP RATIO
        # =====================================================

        if (
            width > 10
            and height > 10
        ):

            frame = self.resize_keep_ratio(
                frame,
                width,
                height
            )

        # =====================================================
        # PIL IMAGE
        # =====================================================

        try:

            image = Image.fromarray(
                frame
            )

            self.photo = ImageTk.PhotoImage(
                image=image
            )

        except Exception as error:

            print(
                f"[CameraWidget] "
                f"Image conversion error: "
                f"{error}"
            )

            self._show_no_signal()

            return

        # =====================================================
        # DISPLAY
        # =====================================================

        if not self.running:
            return

        try:

            self.video_label.config(
                image=self.photo,
                text=""
            )

        except tk.TclError:

            return

        # =====================================================
        # NEXT FRAME
        # =====================================================

        self._schedule_frame()

    # =========================================================
    # NO SIGNAL
    # =========================================================

    def _show_no_signal(self):
        """
        Camera lost signal.
        """

        self.running = False

        self._cancel_after()

        self.photo = None

        try:

            self.video_label.config(
                image="",
                text=(
                    "NO SIGNAL\n"
                    f"Camera {self.device_index}"
                ),
                fg="white",
                bg="black"
            )

        except tk.TclError:

            pass

    # =========================================================
    # CANCEL AFTER
    # =========================================================

    def _cancel_after(self):

        if self.after_id is None:

            return

        try:

            self.after_cancel(
                self.after_id
            )

        except (
            tk.TclError,
            ValueError
        ):

            pass

        self.after_id = None

    # =========================================================
    # RESIZE KEEP RATIO
    # =========================================================

    @staticmethod
    def resize_keep_ratio(
        frame,
        target_width,
        target_height
    ):
        """
        Resize camera frame while maintaining
        original aspect ratio.

        Image is NOT mirrored.
        """

        frame_height, frame_width = (
            frame.shape[:2]
        )

        if (
            frame_width <= 0
            or frame_height <= 0
        ):

            return frame

        if (
            target_width <= 0
            or target_height <= 0
        ):

            return frame

        # =====================================================
        # CALCULATE SCALE
        # =====================================================

        scale = min(
            target_width / frame_width,
            target_height / frame_height
        )

        # =====================================================
        # NEW SIZE
        # =====================================================

        new_width = max(
            1,
            int(
                frame_width * scale
            )
        )

        new_height = max(
            1,
            int(
                frame_height * scale
            )
        )

        # =====================================================
        # RESIZE
        # =====================================================

        return cv2.resize(
            frame,
            (
                new_width,
                new_height
            ),
            interpolation=cv2.INTER_AREA
        )

    # =========================================================
    # STOP CAMERA
    # =========================================================

    def stop_camera(self):
        """
        Completely stop camera.

        Correct order:

            1. running = False
            2. cancel after()
            3. release CameraDevice
            4. clear image
        """

        print(
            "[CameraWidget] "
            f"Stopping Camera {self.device_index}"
        )

        # =====================================================
        # STOP LOOP
        # =====================================================

        self.running = False

        # =====================================================
        # CANCEL CALLBACK
        # =====================================================

        self._cancel_after()

        # =====================================================
        # RELEASE CAMERA
        # =====================================================

        if self.camera is not None:

            try:

                self.camera.release()

            except Exception:

                pass

            self.camera = None

        # =====================================================
        # CLEAR IMAGE
        # =====================================================

        self.photo = None

        try:

            self.video_label.config(
                image="",
                text="NO CAMERA"
            )

        except tk.TclError:

            pass

    # =========================================================
    # DESTROY
    # =========================================================

    def destroy(self):
        """
        Safely destroy CameraWidget.
        """

        if self.destroyed:

            return

        self.destroyed = True

        # =====================================================
        # STOP CAMERA
        # =====================================================

        self.stop_camera()

        # =====================================================
        # DESTROY TK FRAME
        # =====================================================

        try:

            super().destroy()

        except tk.TclError:

            pass