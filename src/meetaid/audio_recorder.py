import logging
import os
import wave
from datetime import datetime
from queue import Queue
from tkinter import Button, Label, Tk

import pyaudiowpatch as pyaudio
from pydub import AudioSegment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

data_format = pyaudio.paInt24  # 24 bits per sample
spkr_filename = "output/spkr_output.wav"
mic_filename = "output/mic_output.wav"

window = Tk()
window.geometry("450x400")
window.title("Meeting Aid")
Label(
    window, text="Click on Start To Start Recording", font=("bold", 20)
).pack()


class ARException(Exception):
    """Base class for AudioRecorder`s exceptions"""


class WASAPINotFound(ARException):
    ...


class InvalidDevice(ARException):
    ...


class AudioRecorder:
    CHUNK_SIZE = 512

    def __init__(
        self, p_audio: pyaudio.PyAudio, spkr_queue: Queue, mic_queue: Queue
    ):
        self.p = p_audio
        self.spkr_queue = spkr_queue
        self.mic_queue = mic_queue
        self.spkr_stream = None
        self.mic_stream = None

    @staticmethod
    def get_default_wasapi_device(p_audio: pyaudio.PyAudio):
        try:  # Get default WASAPI info
            wasapi_info = p_audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            raise WASAPINotFound(
                "Looks like WASAPI is not available on the system"
            )

        # Get default WASAPI speakers
        sys_default_speakers = p_audio.get_device_info_by_index(
            wasapi_info["defaultOutputDevice"]
        )

        if not sys_default_speakers["isLoopbackDevice"]:
            for loopback in p_audio.get_loopback_device_info_generator():
                if sys_default_speakers["name"] in loopback["name"]:
                    return loopback
                    break
            else:
                raise InvalidDevice(
                    "Default loopback output device not found.\n\nRun "
                    "`python -m pyaudiowpatch` to check available devices"
                )

    def spkr_callback(self, in_data, frame_count, time_info, status):
        """Write frames and return PA flag"""
        self.spkr_queue.put(in_data)
        return (in_data, pyaudio.paContinue)

    def mic_callback(self, in_data, frame_count, time_info, status):
        """Write frames and return PA flag"""
        self.mic_queue.put(in_data)
        return (in_data, pyaudio.paContinue)

    def start_recording(self):
        self.close_stream()

        target_device = None
        try:
            target_device = ar.get_default_wasapi_device(p)
        except ARException as E:
            print(
                f"Something went wrong... {type(E)} = " f"{str(E)[:30]}...\n"
            )

        self.spkr_stream = self.p.open(
            format=data_format,
            channels=target_device["maxInputChannels"],
            rate=int(target_device["defaultSampleRate"]),
            frames_per_buffer=self.CHUNK_SIZE,
            input=True,
            input_device_index=target_device["index"],
            stream_callback=self.spkr_callback,
        )
        self.mic_stream = self.p.open(
            format=data_format,
            channels=target_device["maxInputChannels"],
            rate=int(target_device["defaultSampleRate"]),
            frames_per_buffer=self.CHUNK_SIZE,
            input=True,
            stream_callback=self.mic_callback,
        )
        Label(window, text="Recording has started").pack()

    def stop_recording(self):
        self.close_stream()
        Label(window, text="Recording has stopped").pack()

        if not os.path.exists("output"):
            os.makedirs("output")

        target_device = None
        try:
            target_device = ar.get_default_wasapi_device(p)
        except ARException as E:
            print(
                f"Something went wrong... {type(E)} = " f"{str(E)[:30]}...\n"
            )

        spkr_file = wave.open(spkr_filename, "wb")
        spkr_file.setnchannels(target_device["maxInputChannels"])
        spkr_file.setsampwidth(pyaudio.get_sample_size(data_format))
        spkr_file.setframerate(int(target_device["defaultSampleRate"]))

        while not spkr_queue.empty():
            spkr_file.writeframes(spkr_queue.get())
        spkr_file.close()

        mic_file = wave.open(mic_filename, "wb")
        mic_file.setnchannels(target_device["maxInputChannels"])
        mic_file.setsampwidth(pyaudio.get_sample_size(data_format))
        mic_file.setframerate(int(target_device["defaultSampleRate"]))

        while not mic_queue.empty():
            mic_file.writeframes(mic_queue.get())
        mic_file.close()

        combined_filename = (
            "output/" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".wav"
        )
        if spkr_queue.empty():
            os.rename(mic_filename, combined_filename)
        elif mic_queue.empty():
            os.rename(spkr_filename, combined_filename)
        else:
            sound1 = AudioSegment.from_file(mic_filename)
            sound2 = AudioSegment.from_file(spkr_filename)

            combined = sound1.overlay(sound2)

            combined.export(combined_filename, format="wav")

        Label(
            window, text=f"The audio is written to a [{combined_filename}]."
        ).pack()

    def stop_stream(self):
        self.spkr_stream.stop_stream()
        self.mic_stream.stop_stream()

    def start_stream(self):
        self.spkr_stream.start_stream()
        self.mic_stream.start_stream()

    def close_stream(self):
        if self.spkr_stream is not None:
            self.spkr_stream.stop_stream()
            self.spkr_stream.close()
            self.spkr_stream = None
        if self.mic_stream is not None:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
            self.mic_stream = None

    @property
    def stream_status(self):
        return (
            "closed"
            if self.spkr_stream is None
            else "stopped"
            if self.spkr_stream.is_stopped()
            else "running"
        )


if __name__ == "__main__":
    p = pyaudio.PyAudio()
    spkr_queue = Queue()
    mic_queue = Queue()
    ar = AudioRecorder(p, spkr_queue, mic_queue)

    Button(
        window,
        text="Start",
        bg="green",
        command=ar.start_recording,
        font=("bold", 20),
    ).pack()
    Button(
        window,
        text="Stop",
        bg="green",
        command=ar.stop_recording,
        font=("bold", 20),
    ).pack()

    window.mainloop()

    ar.close_stream()
    p.terminate()
