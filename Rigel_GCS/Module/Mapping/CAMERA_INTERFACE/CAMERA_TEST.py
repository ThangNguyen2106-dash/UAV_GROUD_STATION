import tkinter as tk

from Rigel_GCS.Module.Mapping.CAMERA_INTERFACE.CAMERA_Widget import CameraWidget


def main():

    root = tk.Tk()

    root.title(
        "RIGEL GCS - Camera Test"
    )

    root.geometry(
        "1100x750"
    )

    root.minsize(
        800,
        600
    )

    camera = CameraWidget(
        root,
        width=1000,
        height=600
    )

    camera.pack(
        fill=tk.BOTH,
        expand=True
    )

    def on_close():

        camera.stop_camera()

        root.destroy()

    root.protocol(
        "WM_DELETE_WINDOW",
        on_close
    )

    root.mainloop()


if __name__ == "__main__":
    main()