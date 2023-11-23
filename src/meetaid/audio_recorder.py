import logging
import os
import wave
from queue import Queue

import pyaudiowpatch as pyaudio
from pydub import AudioSegment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

data_format = pyaudio.paInt24  # 24 bits per sample


class ARException(Exception):
    """Base class for AudioRecorder`s exceptions"""


class WASAPINotFound(ARException):
    ...


class InvalidDevice(ARException):
    ...


class AudioRecorder:
    CHUNK_SIZE = 512

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.spkr_queue = Queue()
        self.mic_queue = Queue()
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

    def start_recording(self, unique_id):
        self.close_stream()

        self.unique_id = unique_id
        self.spkr_filename = f"output/spkr_{unique_id}.wav"
        self.mic_filename = f"output/mic_{unique_id}.wav"
        self.combined_filename = f"output/audio_{unique_id}.wav"
        target_device = None
        try:
            target_device = ar.get_default_wasapi_device(self.p)
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

    def stop_recording(self) -> str:
        self.close_stream()

        target_device = None
        try:
            target_device = ar.get_default_wasapi_device(self.p)
        except ARException as E:
            print(
                f"Something went wrong... {type(E)} = " f"{str(E)[:30]}...\n"
            )

        if not self.spkr_queue.empty():
            spkr_file = wave.open(self.spkr_filename, "wb")
            spkr_file.setnchannels(target_device["maxInputChannels"])
            spkr_file.setsampwidth(pyaudio.get_sample_size(data_format))
            spkr_file.setframerate(int(target_device["defaultSampleRate"]))

            while not self.spkr_queue.empty():
                spkr_file.writeframes(self.spkr_queue.get())
            spkr_file.close()

        if not self.mic_queue.empty():
            mic_file = wave.open(self.mic_filename, "wb")
            mic_file.setnchannels(target_device["maxInputChannels"])
            mic_file.setsampwidth(pyaudio.get_sample_size(data_format))
            mic_file.setframerate(int(target_device["defaultSampleRate"]))

            while not self.mic_queue.empty():
                mic_file.writeframes(self.mic_queue.get())
            mic_file.close()

        if not os.path.exists(self.spkr_filename):
            os.rename(self.mic_filename, self.combined_filename)
        elif not os.path.exists(self.mic_filename):
            os.rename(self.spkr_filename, self.combined_filename)
        else:
            sound1 = AudioSegment.from_file(self.mic_filename)
            sound2 = AudioSegment.from_file(self.spkr_filename)
            combined = sound1.overlay(sound2)
            combined.export(self.combined_filename, format="wav")
            os.remove(self.mic_filename)
            os.remove(self.spkr_filename)
        return self.combined_filename

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

    def terminate(self):
        self.p.terminate()

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
    ar = AudioRecorder()

    ar.terminate()
