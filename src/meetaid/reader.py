from typing import Optional

import logging
import os
# from datetime import datetime

import click
import easyocr
from scenedetect import ContentDetector, SceneManager, open_video
from scenedetect.scene_manager import save_images

# from meetaid.recorder import DT_FORMAT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
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
@click.argument("video_loc")
def main(video_loc: str) -> None:
    """Read a video"""
    read(video_loc)


def read(video_loc: str) -> None:
    """Read a video recording"""
    scene_text = read_video_scenes(video_loc)
    logger.info("Writing result to text file")
    video_text = os.path.splitext(video_loc)[0] + ".txt"
    with open(video_text, "w") as file:
        file.write("Video Text:\n" + scene_text)
    logger.info(f"Text at: {video_text}")


def read_video_scenes(video_path, threshold=27.0):
    """Split a video into scenes, save a single image from each, and read each one."""
    video = open_video(video_path)
    # video_20231202-092450
    # video_dt = datetime.strptime(video.name.split("_")[1], DT_FORMAT)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    # Detect all scenes in video from current position to end.
    scene_manager.detect_scenes(video)
    # `get_scene_list` returns a list of start/end timecode pairs
    # for each scene that was found.
    scene_list = scene_manager.get_scene_list()
    logger.debug(scene_list)
    image_out_dir = os.path.dirname(video_path)
    img_ext = "jpg"
    save_images(
        scene_list,
        video,
        num_images=1,
        frame_margin=1,
        image_extension=img_ext,
        encoder_param=95,
        image_name_template="$VIDEO_NAME-Scene-$SCENE_NUMBER",
        output_dir=image_out_dir,
        show_progress=False,
    )

    # Read the text for each image in the list of scene images
    logger.info("Loading Reader")
    reader = easyocr.Reader(["en"])
    read_text = ""
    logger.info("Reading scenes")
    for i, scene in enumerate(scene_list):
        # video_20231202-092450-Scene-001.jpg
        scene_image = (
            f"{image_out_dir}/{video.name}-Scene-{(i+1):03}.{img_ext}"
        )
        scene_text = reader.readtext(scene_image, detail=0)
        read_text += f"[{scene[0].get_timecode()}-{scene[1].get_timecode()}]:  "
        read_text += f"{scene_text}\n\n"
        # Get datetime from video name
        # Add scene[0].get_timecode() "00:00:00.000" to date time from video
        # scene_start = datetime.strptime(
        #                   scene[0].get_timecode(precision=0), 
        #                   "%H:%M:%S"
        #               )
        # img_time = video_dt + timedelta(hours=scene_start.hour,
        #                       minutes=scene_start.minute,
        #                       seconds=scene_start.second)
        # Save as "img_newdate-newtime.jpg" (e.g., img_20231202-092451.jpg)
        # new_file_name = f"{image_out_dir}/img_"
        #                 f"{img_time.strftime(DT_FORMAT)}.{img_ext}"
        # if os.path.exists(new_file_name):
        #    img_time = img_time + timedelta(seconds=1)
        #    new_file_name = f"{image_out_dir}/img_
        #                    f"{img_time.strftime(DT_FORMAT)}.{img_ext}"
        # scene_images.append(new_file_name)
        # os.rename(scene_image, new_file_name)
    return read_text
