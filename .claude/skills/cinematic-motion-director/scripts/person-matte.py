#!/usr/bin/env python3
"""
Person cutout + face track for "behind the head" effects in Remotion.

  python person-matte.py talk.mp4 --out public/me          # -> me/person.webm + me/face.json
  python person-matte.py talk.mp4 --out public/me --start 3 --end 9 --models C:/tools/models

Writes
  person.webm  the speaker alone on transparent pixels (VP9 + alpha, same size / fps / timing as
               the source window). In Remotion: base video -> layers BEHIND the person ->
               <OffthreadVideo transparent src="person.webm"/> -> layers IN FRONT.
  face.json    {fps, width, height, start, frames: [[cx, cy, w], ...]} in pixels per frame, smoothed
               forward + backward (no lag): anchor cards, brackets, punch-ins and "never cover the
               face" checks on it.

Models (downloaded once into --models): MediaPipe Selfie Segmenter (Apache-2.0) and OpenCV
YuNet face detector (MIT). Needs: pip install mediapipe opencv-python numpy; ffmpeg on PATH.
Works best on a vertical talking head with one person, steady light.
"""
import argparse, json, math, os, subprocess, urllib.request
import numpy as np
import cv2

SEG_URL = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"


def model(models, name, url):
    p = os.path.join(models, name)
    if not os.path.exists(p):
        os.makedirs(models, exist_ok=True)
        print(f"downloading {name} ...")
        urllib.request.urlretrieve(url, p)
    return p


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip().split(",")
    n, d = out[2].split("/")
    return int(out[0]), int(out[1]), float(n) / float(d)


def smooth(vals, fps, tau=0.15):
    """forward + backward one-pole filter: steady and without lag"""
    a = 1 - math.exp(-1 / (fps * tau)); v = np.array(vals, float)
    for rng in (range(1, len(v)), range(len(v) - 2, -1, -1)):
        for i in rng:
            j = i - 1 if rng.step == 1 else i + 1
            v[i] = v[j] + a * (v[i] - v[j])
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float)
    ap.add_argument("--models", default=os.path.join(os.path.expanduser("~"), "tools", "models"))
    ap.add_argument("--feather", type=int, default=5, help="edge blur in px (odd)")
    a = ap.parse_args()
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    W, H, fps = probe(a.video)
    os.makedirs(a.out, exist_ok=True)
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=model(a.models, "selfie_segmenter.tflite", SEG_URL)),
        running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True))
    fw_, fh_ = 320, int(320 * H / W)
    det = cv2.FaceDetectorYN.create(model(a.models, "yunet.onnx", YUNET_URL), "", (fw_, fh_), 0.6, 0.3, 20)

    cut = ["-ss", str(a.start)] + (["-t", str(a.end - a.start)] if a.end else [])
    src = subprocess.Popen(["ffmpeg", "-v", "error"] + cut + ["-i", a.video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", f"{fps}", "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
                            "-crf", "34", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1",
                            "-auto-alt-ref", "0", os.path.join(a.out, "person.webm")], stdin=subprocess.PIPE)
    faces, prev, i, found = [], None, 0, 0
    k = a.feather | 1
    while True:
        buf = src.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        r = seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(i * 1000 / fps))
        m = r.confidence_masks[0].numpy_view().astype(np.float32)
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
        m = np.clip((m - 0.35) / 0.3, 0, 1)                    # soft threshold
        m = m if prev is None else 0.6 * m + 0.4 * prev        # calm flicker on the edges
        prev = m
        m = cv2.GaussianBlur(m, (k, k), 0)
        enc.stdin.write(np.dstack([rgb, (m * 255).astype(np.uint8)]).tobytes())
        _, f = det.detect(cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (fw_, fh_)))
        if f is not None and len(f):
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])[:4] * (W / fw_)
            faces.append([x + w / 2, y + h / 2, w]); found += 1
        else:
            faces.append(faces[-1] if faces else [W / 2, H * 0.35, W * 0.3])
        i += 1
    enc.stdin.close(); enc.wait(); src.wait()
    f = np.array(faces)
    cols = [smooth(f[:, j], fps) for j in range(3)]
    json.dump({"fps": fps, "width": W, "height": H, "start": a.start,
               "frames": [[round(float(c[n]), 1) for c in cols] for n in range(len(f))]},
              open(os.path.join(a.out, "face.json"), "w"))
    print(f"ok {a.out}/person.webm + face.json: {i} frames, face found in "
          f"{found} frames, median face width {np.median(f[:, 2]):.0f}px")


if __name__ == "__main__":
    main()
