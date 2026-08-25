"""
Camera device abstraction for RIGEL Ground Station.

Responsibilities:
    - Open a physical camera by index.
    - Read frames.
    - Configure resolution.
    - Release camera resources.

This module does NOT handle Tkinter UI.
"""

import cv2


class CameraDevice:
    """
    Low-level camera device.

    Example:

        camera = CameraDevice(
            device_index=0
        )

        if camera.open():
            frame = camera.read()

        camera.release()
    """

    # =========================================================
    # DEFAULT SETTINGS
    # =========================================================

    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        device_index=0,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
    ):

        self.device_index = int(
            device_index
        )

        self.width = int(
            width
        )

        self.height = int(
            height
        )

        self.cap = None

        self.is_open = False

    # =========================================================
    # OPEN
    # =========================================================

    def open(self):
        """
        Open the selected camera.

        The actual camera index is ALWAYS
        taken from self.device_index.
        """

        # Already open
        if (
            self.is_open
            and self.cap is not None
        ):
            return True

        # Make sure previous capture is closed
        self.release()

        print(
            f"[CameraDevice] "
            f"Opening Camera {self.device_index}"
        )

        try:

            self.cap = cv2.VideoCapture(
                self.device_index,
                cv2.CAP_DSHOW
            )

        except Exception as error:

            print(
                f"[CameraDevice] "
                f"Open error: {error}"
            )

            self.cap = None
            self.is_open = False

            return False

        # =====================================================
        # CHECK CAMERA
        # =====================================================

        if self.cap is None:

            self.is_open = False

            return False

        if not self.cap.isOpened():

            print(
                f"[CameraDevice] "
                f"Camera {self.device_index} "
                f"could not be opened."
            )

            self.release()

            return False

        # =====================================================
        # SET RESOLUTION
        # =====================================================

        try:

            self.cap.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                self.width
            )

            self.cap.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                self.height
            )

        except Exception:
            pass

        # =====================================================
        # READY
        # =====================================================

        self.is_open = True

        actual_width = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        actual_height = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        print(
            f"[CameraDevice] "
            f"Camera {self.device_index} "
            f"opened: "
            f"{actual_width}x{actual_height}"
        )

        return True

    # =========================================================
    # READ
    # =========================================================

    def read(self):
        """
        Read one frame.

        Returns:
            OpenCV BGR frame
            None if reading fails
        """

        if (
            not self.is_open
            or self.cap is None
        ):
            return None

        try:

            ret, frame = self.cap.read()

        except Exception as error:

            print(
                f"[CameraDevice] "
                f"Read error: {error}"
            )

            return None

        if not ret:

            return None

        return frame

    # =========================================================
    # RELEASE
    # =========================================================

    def release(self):
        """
        Completely release camera.
        """

        if self.cap is not None:

            try:
                self.cap.release()
            except Exception:
                pass

        self.cap = None

        self.is_open = False

    # =========================================================
    # RESOLUTION
    # =========================================================

    def get_resolution(self):
        """
        Return actual camera resolution.
        """

        if (
            not self.is_open
            or self.cap is None
        ):
            return None

        try:

            width = int(
                self.cap.get(
                    cv2.CAP_PROP_FRAME_WIDTH
                )
            )

            height = int(
                self.cap.get(
                    cv2.CAP_PROP_FRAME_HEIGHT
                )
            )

            return width, height

        except Exception:

            return None

    # =========================================================
    # TEST CAMERA
    # =========================================================

    @staticmethod
    def is_available(index):
        """
        Test whether a camera index is available.

        This method opens the camera only temporarily.
        """

        cap = None

        try:

            cap = cv2.VideoCapture(
                int(index),
                cv2.CAP_DSHOW
            )

            if not cap.isOpened():

                return False

            return True

        except Exception:

            return False

        finally:

            if cap is not None:

                try:
                    cap.release()
                except Exception:
                    pass

    # =========================================================
    # SCAN CAMERAS
    # =========================================================

    @staticmethod
    def scan(
        max_devices=10
    ):
        """
        Scan available camera indexes.

        Returns:

            [0]
            [0, 1]
            [0, 1, 2]

        etc.
        """

        devices = []

        for index in range(
            int(max_devices)
        ):

            if CameraDevice.is_available(
                index
            ):

                devices.append(
                    index
                )

        print(
            f"[CameraDevice] "
            f"Detected cameras: {devices}"
        )

        return devices