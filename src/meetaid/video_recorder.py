import logging
import threading

import cv2
import numpy as np
import pyautogui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

SCREEN_SIZE = tuple(pyautogui.size())
# define the codec
CODEC = cv2.VideoWriter_fourcc(*"XVID")
# frames per second
FPS = 60.0
video_filename = "output/video_{}.avi"


class VideoRecorder:
    def __init__(self):
        # Get the webcam if recording separate from screen
        self.started = False

    def start_recording(self, unique_id):
        self.unique_id = unique_id
        logger.debug(video_filename.format(self.unique_id))
        # create the video write object
        self.vw = cv2.VideoWriter(
            video_filename.format(self.unique_id), CODEC, FPS, (SCREEN_SIZE)
        )
        if self.started:
            logger.warn("Threaded video capturing has already been started.")
            return None
        self.started = True
        self.thread = threading.Thread(target=self._update_video, args=())
        self.thread.start()
        return self

    def _update_video(self):
        while self.started:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.vw.write(frame)
            for i in range(0, 5):
                self.vw.write(frame)

    def stop_recording(self):
        self.started = False
        self.vw.release()
        self.thread.join()

    def get_screenshot(self):
        return pyautogui.screenshot()

    def _record_webcam(self):
        self.webcam = cv2.VideoCapture(0)
        _, frame = self.webcam.read()
        # Finding the width, height and shape of our webcam image
        fr_height, fr_width, _ = frame.shape

        # setting the width and height properties
        self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, fr_width)
        self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, fr_height)

        # cv2.imshow('frame', img)
        # Write the frame into the file 'output.avi'
        self.out.write(frame)
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Recording Stopped")
            return
