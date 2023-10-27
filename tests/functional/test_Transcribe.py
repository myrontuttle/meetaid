from pathlib import Path

from meetaid import transcriber


def test_transcribe():
    media_file = "./output/20231025-090127.wav"
    transcriber.transcribe(media_file)
    transcribed = "./output/20231025-090127.txt"
    assert Path(transcribed).is_file()


if __name__ == "__main__":
    test_transcribe()
