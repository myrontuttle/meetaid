import logging
import os
from datetime import datetime
from tkinter import Button, Label, Tk

from meetaid.audio_recorder import AudioRecorder
from meetaid.video_recorder import VideoRecorder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

DT_FORMAT = "%Y%m%d-%H%M%S"

window = Tk()
window.geometry("450x400")
window.title("Meeting Aid")
Label(
    window, text="Click on Start To Start Recording", font=("bold", 20)
).pack()


class Recorder:
    def __init__(self, time=None):
        if not os.path.exists("output"):
            os.makedirs("output")
        self.ar = AudioRecorder()
        self.vr = VideoRecorder()

    def start_audio_recording(self):
        dt = datetime.now().strftime(DT_FORMAT)
        self.ar.start_recording(dt)
        Label(window, text="Audio recording has started").pack()

    def stop_audio_recording(self):
        Label(window, text="Stopping recording").pack()
        combined_filename = self.ar.stop_recording()
        Label(
            window, text=f"The audio is written to a [{combined_filename}]."
        ).pack()

    def start_video_recording(self):
        dt = datetime.now().strftime(DT_FORMAT)
        self.vr.start_recording(dt)
        Label(window, text="Video recording has started").pack()

    def stop_video_recording(self):
        self.vr.stop_recording()
        Label(window, text="Video recording has stopped").pack()

    def terminate(self):
        self.ar.close_stream()
        self.ar.terminate()


if __name__ == "__main__":
    r = Recorder()

    Button(
        window,
        text="Start Audio Recording",
        bg="green",
        command=r.start_audio_recording,
        font=("bold", 20),
    ).pack()
    Button(
        window,
        text="Stop Audio Recording",
        bg="green",
        command=r.stop_audio_recording,
        font=("bold", 20),
    ).pack()
    Button(
        window,
        text="Start Video Recording",
        bg="green",
        command=r.start_video_recording,
        font=("bold", 20),
    ).pack()
    Button(
        window,
        text="Stop Video Recording",
        bg="green",
        command=r.stop_video_recording,
        font=("bold", 20),
    ).pack()

    window.mainloop()

    r.terminate()
