from typing import Any, Dict, List, Optional

import datetime
import logging
import os
import subprocess
from pathlib import Path

import click
import whisper
from whisperx import align, load_align_model
from whisperx.diarize import DiarizationPipeline, assign_word_speakers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
WHISPER_MODEL = "medium.en"
WHISPER_DEVICE = "cuda"  # "cpu" or "cuda" if available
LANGUAGE = "en"
HF_TOKEN = "HF_TOKEN"


def get_key_from_env(key: str) -> Optional[str]:
    """
    Get a key from the environment variables.

    Args:
        key: HF_TOKEN (HuggingFace Token)

    Returns:
        The value of the key if it exists, else None.
    """
    if key not in os.environ:
        logger.critical(
            f"{key} does not exist as environment variable.",
        )
        logger.debug(os.environ)
    return os.getenv(key)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("audio_loc")
def main(audio_loc: str) -> None:
    """Transcribe an audio recording"""
    transcribe(audio_loc)


def transcribe(audio_loc: str) -> None:
    """Transcribe an audio recording"""

    file_loc = audio_loc
    file_path = Path(audio_loc)

    if not file_path.exists():
        logger.error(f"{file_loc}: No such file")
        logger.error(f"CWD: {os.getcwd()}")
        return None

    # Convert to WAV
    if file_path.suffix != ".wav":
        convert_to_wav(file_loc)
        file_loc = os.path.splitext(file_loc)[0] + ".wav"

    # Transcribe and Diarize
    transcript = transcribe_file(file_loc)
    aligned_segments = align_segments(transcript, file_loc)
    diarization_result = diarize(file_loc)
    results_segments_w_speakers = assign_speakers(
        diarization_result, aligned_segments
    )
    transcript_text = ""
    for seg in results_segments_w_speakers:
        start = str(datetime.timedelta(seconds=round(seg["start"])))
        end = str(datetime.timedelta(seconds=round(seg["end"])))
        transcript_text += (
            f"[{start}-{end}] " f"{seg['speaker']}: {seg['text']}\n\n"
        )

    # Write result to file
    logger.info("Writing result to transcript file")
    transcribed = os.path.splitext(file_loc)[0] + ".txt"
    with open(transcribed, "w") as file:
        file.write("Transcript:\n" + transcript_text)
    logger.info(f"Transcription at: {transcribed}")


def convert_to_wav(input_file: str) -> None:
    """
    Converts an audio file to WAV format using FFmpeg. The output file will
    be created by replacing the input file extension with ".wav".

    Args:
        input_file: The path of the input audio file to convert.

    Returns:
        None
    """
    output_file = os.path.splitext(input_file)[0] + ".wav"

    command = (
        f'ffmpeg -i "{input_file}" -vn -acodec pcm_s16le -ar 44100'
        f' -ac 1 "{output_file}"'
    )

    try:
        subprocess.run(command, shell=True, check=True)
        logger.info(
            f'Successfully converted "{input_file}" to "{output_file}"'
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            f'Error: {e}, could not convert "{input_file}" to '
            f'"{output_file}"'
        )


def transcribe_file(audio_file: str) -> Dict[str, Any]:
    """
    Transcribe an audio file using a speech-to-text model.

    Args:
        audio_file: Path to the audio file to transcribe.

    Returns:
        A dictionary representing the transcript, including the segments,
        the language code, and the duration of the audio file.
    """
    # transcribe with original whisper
    logger.info("Loading model: " + WHISPER_MODEL)
    model = whisper.load_model(WHISPER_MODEL, WHISPER_DEVICE)
    whisper.DecodingOptions(language=LANGUAGE)
    # Transcribe
    logger.info("Transcribing")
    return model.transcribe(audio_file)


def align_segments(
    transcript: Dict[str, Any],
    audio_file: str,
) -> Dict[str, Any]:
    """
    Align the transcript segments using a pretrained alignment model.
    Args:
        transcript: Dictionary representing the transcript with segments
        audio_file: Path to the audio file containing the audio data.
    Returns:
        A dictionary representing the aligned transcript segments.
    """
    logger.info("Loading alignment model")
    model_a, metadata = load_align_model(
        language_code=LANGUAGE, device=WHISPER_DEVICE
    )
    logger.info("Aligning output")
    result_aligned = align(
        transcript["segments"], model_a, metadata, audio_file, WHISPER_DEVICE
    )
    return result_aligned


def diarize(audio_file: str) -> Dict[str, Any]:
    """
    Perform speaker diarization on an audio file.
    Args:
        audio_file: Path to the audio file to diarize.
    Returns:
        A dictionary representing the diarized audio file,
        including the speaker embeddings and the number of speakers.
    """
    logger.info("Diarizing")
    diarization_pipeline = DiarizationPipeline(
        use_auth_token=get_key_from_env(HF_TOKEN)
    )
    diarization_result = diarization_pipeline(audio_file)
    return diarization_result


def assign_speakers(
    diarization_result: Dict[str, Any], aligned_segments: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Assign speakers to each transcript segment based on the speaker
    diarization result.
    Args:
        diarization_result: Dictionary representing the diarized audio file,
            including the speaker embeddings and the number of speakers.
        aligned_segments: Dictionary representing the aligned transcript
            segments.
    Returns:
        A list of dictionaries representing each segment of the transcript,
        including the start and end times, the spoken text, and the speaker ID.
    """
    logger.info("Assigning speakers to segments")
    aligned_segments = assign_word_speakers(
        diarization_result, aligned_segments
    )
    results_segments_w_speakers: List[Dict[str, Any]] = []
    for segment in aligned_segments["segments"]:
        if "speaker" not in segment:
            logger.error(
                f"No speaker defined for segment at {segment['start']}."
            )
            segment["speaker"] = "SPEAKER_UNKNOWN"
        if (
            len(results_segments_w_speakers) > 0
            and segment["speaker"]
            == results_segments_w_speakers[-1]["speaker"]
        ):
            results_segments_w_speakers[-1]["text"] += segment["text"]
            results_segments_w_speakers[-1]["end"] = segment["end"]
            continue
        results_segments_w_speakers.append(
            {
                "start": segment["start"],
                "end": segment["end"],
                "speaker": segment["speaker"],
                "text": segment["text"],
            }
        )
    return results_segments_w_speakers


if __name__ == "__main__":
    main()
