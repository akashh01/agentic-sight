import logging
import os
from typing import Iterator

import cv2

from agentic_sight.schema import Frame

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, sample_rate_fps: float, out_dir: str) -> Iterator[Frame]:
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, round(native_fps / sample_rate_fps))
    logger.info(
        "sampling %s at %.2f fps (native=%.2f fps, every %d frames) -> %s",
        video_path, sample_rate_fps, native_fps, frame_interval, out_dir,
    )

    frame_idx = 0
    sampled_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % frame_interval == 0:
            timestamp_sec = frame_idx / native_fps
            image_path = os.path.join(out_dir, f"frame_{sampled_idx:05d}.jpg")
            cv2.imwrite(image_path, frame)
            logger.debug("sampled frame %d at t=%.2fs -> %s", sampled_idx, timestamp_sec, image_path)
            yield Frame(index=sampled_idx, timestamp_sec=timestamp_sec, image_path=image_path)
            sampled_idx += 1
        frame_idx += 1

    cap.release()
    logger.info("done: %d frames sampled from %s", sampled_idx, video_path)


def extract_frame_at(video_path: str, timestamp_sec: float, out_dir: str, tag: str) -> Frame:
    """Grab a single frame at (approximately) the given timestamp.

    Used for the confirmation check: when the main sampling loop gets a hit,
    we look at the frames just before/after it rather than trusting one
    frame in isolation. `tag` makes the output filename unique per caller.
    """
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    target_frame_number = max(0, round(timestamp_sec * native_fps))
    if total_frames and target_frame_number >= total_frames:
        cap.release()
        raise ValueError(f"timestamp {timestamp_sec:.2f}s is past the end of {video_path}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_number)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise ValueError(f"could not read a frame at t={timestamp_sec:.2f}s from {video_path}")

    actual_timestamp = target_frame_number / native_fps
    image_path = os.path.join(out_dir, f"confirm_{tag}.jpg")
    cv2.imwrite(image_path, frame)
    logger.debug("grabbed confirmation frame at t=%.2fs -> %s", actual_timestamp, image_path)
    return Frame(index=target_frame_number, timestamp_sec=actual_timestamp, image_path=image_path)


if __name__ == "__main__":
    import argparse

    from agentic_sight.logging_config import setup_logging

    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone test: sample frames from a video")
    parser.add_argument("--video", required=True)
    parser.add_argument("--sample-rate-fps", type=float, default=1.0)
    parser.add_argument("--out-dir", default="frames_out")
    args = parser.parse_args()

    count = 0
    for frame in extract_frames(args.video, args.sample_rate_fps, args.out_dir):
        print(f"frame {frame.index}  t={frame.timestamp_sec:.2f}s  {frame.image_path}")
        count += 1
    print(f"\n{count} frames sampled to {args.out_dir}/")
