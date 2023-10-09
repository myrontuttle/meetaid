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
spkr_filename = "output/spkr_output.wav"
mic_filename = "output/mic_output.wav"
combined_filename = "output/combined.wav"


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

    def start_recording(self, target_device: dict):
        self.close_stream()

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

    help_msg = (
        30 * "-" + "\n\n\nStatus:\nRunning=%s | Device=%s | "
        "output=%s\n\nCommands:\nlist\nrecord {"
        "device_index\\default}\npause\ncontinue\nstop {"
        "*.wav\\default}\n"
    )

    target_device = None

    try:
        while True:
            print(
                help_msg
                % (
                    ar.stream_status,
                    target_device["index"]
                    if target_device is not None
                    else "None",
                    spkr_filename,
                )
            )
            com = input("Enter command: ").split()

            if com[0] == "list":
                p.print_detailed_system_info()

            elif com[0] == "record":
                if len(com) > 1 and com[1].isdigit():
                    target_device = p.get_device_info_by_index(int(com[1]))
                else:
                    try:
                        target_device = ar.get_default_wasapi_device(p)
                    except ARException as E:
                        print(
                            f"Something went wrong... {type(E)} = "
                            f"{str(E)[:30]}...\n"
                        )
                        continue
                ar.start_recording(target_device)

            elif com[0] == "pause":
                ar.stop_stream()
            elif com[0] == "continue":
                ar.start_stream()
            elif com[0] == "stop":
                ar.close_stream()

                if (
                    len(com) > 1
                    and com[1].endswith(".wav")
                    and os.path.exists(
                        os.path.dirname(os.path.realpath(com[1]))
                    )
                ):
                    spkr_filename = com[1]

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

                sound1 = AudioSegment.from_file(mic_filename)
                sound2 = AudioSegment.from_file(spkr_filename)

                combined = sound1.overlay(sound2)

                combined.export(combined_filename, format="wav")

                print(
                    f"The audio is written to a [{combined_filename}]. "
                    f"Exit..."
                )
                break

            else:
                print(f"[{com[0]}] is unknown command")

    except KeyboardInterrupt:
        print("\n\nExit without saving...")
    finally:
        ar.close_stream()
        p.terminate()
