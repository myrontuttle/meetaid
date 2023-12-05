from pathlib import Path

from meetaid import reader


def test_read():
    media_file = "./output/video_20231202-092450.avi"
    reader.read(media_file)
    scene_image = "./output/video_20231202-092450.txt"
    assert Path(scene_image).is_file()


if __name__ == "__main__":
    test_read()
