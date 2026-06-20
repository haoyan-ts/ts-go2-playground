import argparse
import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp

from .gesture_detector import (
    detect_gesture,
    GESTURE_NONE,
    GESTURE_OPEN_HAND,
    GESTURE_FIST,
    GESTURE_THUMB_UP,
    GESTURE_PEACE,
    GESTURE_POINT,
)

CONFIRM_FRAMES = 15  # 同じジェスチャーが何フレーム続いたら実行するか
COOLDOWN_SEC = 2.0  # コマンド実行後のクールダウン（秒）
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"
)

GESTURE_ACTIONS = {
    GESTURE_OPEN_HAND: ("StandUp", lambda c: c.stand_up()),
    GESTURE_FIST: ("StandDown", lambda c: c.stand_down()),
    GESTURE_THUMB_UP: ("Dance", lambda c: c.dance()),
    GESTURE_PEACE: ("Hello", lambda c: c.hello()),
    GESTURE_POINT: ("RecoveryStand", lambda c: c.recovery_stand()),
}

GESTURE_LABELS = {
    GESTURE_OPEN_HAND: "OPEN HAND",
    GESTURE_FIST: "FIST",
    GESTURE_THUMB_UP: "THUMB UP",
    GESTURE_PEACE: "PEACE",
    GESTURE_POINT: "POINT",
    GESTURE_NONE: "",
}


def ensure_hand_landmarker_model(model_path: Path) -> Path:
    if model_path.exists():
        return model_path

    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[MediaPipe] Downloading hand landmarker model to {model_path}")
    try:
        urllib.request.urlretrieve(MODEL_URL, model_path)
    except OSError as exc:
        raise RuntimeError(
            f"Failed to download MediaPipe hand landmarker model from {MODEL_URL}"
        ) from exc
    return model_path


def create_hand_landmarker(model_path: Path):
    resolved_model_path = ensure_hand_landmarker_model(model_path)
    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(resolved_model_path)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    return mp.tasks.vision.HandLandmarker.create_from_options(options)


def draw_overlay(frame, gesture: str, last_action: str, cooldown_remaining: float):
    h, w = frame.shape[:2]
    label = GESTURE_LABELS.get(gesture, "")
    if label:
        cv2.putText(
            frame,
            f"Gesture: {label}",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            2,
        )
    if last_action:
        cv2.putText(
            frame,
            f"Action: {last_action}",
            (10, h - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 200, 255),
            2,
        )
    if cooldown_remaining > 0:
        cv2.putText(
            frame,
            f"Cooldown: {cooldown_remaining:.1f}s",
            (10, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (100, 100, 255),
            2,
        )


def run(network_interface: str, camera_index: int, dry_run: bool, model_path: Path):
    controller = None
    if not dry_run:
        from .go2_controller import Go2Controller

        controller = Go2Controller(network_interface)

    cap = cv2.VideoCapture(camera_index)
    hand_landmarker = create_hand_landmarker(model_path)
    draw_landmarks = mp.tasks.vision.drawing_utils
    draw_styles = mp.tasks.vision.drawing_styles
    hand_connections = mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS

    candidate_gesture = GESTURE_NONE
    candidate_count = 0
    last_executed_gesture = GESTURE_NONE
    last_action_label = ""
    last_command_time = 0.0
    last_frame_timestamp_ms = -1

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = time.monotonic_ns() // 1_000_000
            frame_timestamp_ms = max(last_frame_timestamp_ms + 1, timestamp_ms)
            last_frame_timestamp_ms = frame_timestamp_ms
            results = hand_landmarker.detect_for_video(mp_image, frame_timestamp_ms)

            current_gesture = GESTURE_NONE
            if results.hand_landmarks:
                hand_landmarks = results.hand_landmarks[0]
                handedness = None
                if results.handedness and results.handedness[0]:
                    handedness = results.handedness[0][0].category_name

                draw_landmarks.draw_landmarks(
                    frame,
                    hand_landmarks,
                    hand_connections,
                    draw_styles.get_default_hand_landmarks_style(),
                    draw_styles.get_default_hand_connections_style(),
                )
                current_gesture = detect_gesture(hand_landmarks, handedness)

            # 連続フレームカウント
            if current_gesture == candidate_gesture and current_gesture != GESTURE_NONE:
                candidate_count += 1
            else:
                candidate_gesture = current_gesture
                candidate_count = 1

            now = time.time()
            cooldown_remaining = max(0.0, COOLDOWN_SEC - (now - last_command_time))

            # クールダウン中、または直前と同じジェスチャーは実行しない
            if (
                candidate_count >= CONFIRM_FRAMES
                and cooldown_remaining == 0.0
                and candidate_gesture != GESTURE_NONE
                and candidate_gesture != last_executed_gesture
                and candidate_gesture in GESTURE_ACTIONS
            ):
                action_label, action_fn = GESTURE_ACTIONS[candidate_gesture]
                last_action_label = action_label
                last_executed_gesture = candidate_gesture
                last_command_time = now
                print(f"[GO2] {action_label}")
                if controller:
                    action_fn(controller)

            # クールダウンが終わったら前回ジェスチャーをリセット（同じ動作を再度実行可能に）
            if cooldown_remaining == 0.0:
                last_executed_gesture = GESTURE_NONE

            draw_overlay(
                frame,
                (
                    candidate_gesture
                    if candidate_count >= CONFIRM_FRAMES
                    else GESTURE_NONE
                ),
                last_action_label,
                cooldown_remaining,
            )

            cv2.imshow("Go2 Gesture Demo", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        hand_landmarker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unitree Go2 Gesture Control Demo")
    parser.add_argument(
        "--interface", default="eth0", help="ネットワークインターフェース名（例: eth0）"
    )
    parser.add_argument("--camera", type=int, default=0, help="カメラデバイス番号")
    parser.add_argument(
        "--dry-run", action="store_true", help="Go2に接続せずカメラと認識だけテスト"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="MediaPipe Hand Landmarker task model path",
    )
    args = parser.parse_args()

    run(args.interface, args.camera, args.dry_run, args.model)
