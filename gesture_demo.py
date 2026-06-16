import argparse
import time
import cv2
import mediapipe as mp

from gesture_detector import (
    detect_gesture,
    GESTURE_NONE,
    GESTURE_OPEN_HAND,
    GESTURE_FIST,
    GESTURE_THUMB_UP,
    GESTURE_PEACE,
    GESTURE_POINT,
)
from go2_controller import Go2Controller

CONFIRM_FRAMES = 15   # 同じジェスチャーが何フレーム続いたら実行するか
COOLDOWN_SEC = 2.0    # コマンド実行後のクールダウン（秒）

GESTURE_ACTIONS = {
    GESTURE_OPEN_HAND: ("StandUp",        lambda c: c.stand_up()),
    GESTURE_FIST:      ("StandDown",      lambda c: c.stand_down()),
    GESTURE_THUMB_UP:  ("Dance",          lambda c: c.dance()),
    GESTURE_PEACE:     ("Hello",          lambda c: c.hello()),
    GESTURE_POINT:     ("RecoveryStand",  lambda c: c.recovery_stand()),
}

GESTURE_LABELS = {
    GESTURE_OPEN_HAND: "OPEN HAND",
    GESTURE_FIST:      "FIST",
    GESTURE_THUMB_UP:  "THUMB UP",
    GESTURE_PEACE:     "PEACE",
    GESTURE_POINT:     "POINT",
    GESTURE_NONE:      "",
}


def draw_overlay(frame, gesture: str, last_action: str, cooldown_remaining: float):
    h, w = frame.shape[:2]
    label = GESTURE_LABELS.get(gesture, "")
    if label:
        cv2.putText(frame, f"Gesture: {label}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
    if last_action:
        cv2.putText(frame, f"Action: {last_action}", (10, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)
    if cooldown_remaining > 0:
        cv2.putText(frame, f"Cooldown: {cooldown_remaining:.1f}s", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 255), 2)


def run(network_interface: str, camera_index: int, dry_run: bool):
    controller = None if dry_run else Go2Controller(network_interface)

    cap = cv2.VideoCapture(camera_index)
    hands = mp.solutions.hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    draw_landmarks = mp.solutions.drawing_utils

    candidate_gesture = GESTURE_NONE
    candidate_count = 0
    last_executed_gesture = GESTURE_NONE
    last_action_label = ""
    last_command_time = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        current_gesture = GESTURE_NONE
        if results.multi_hand_landmarks:
            hand_lm = results.multi_hand_landmarks[0]
            draw_landmarks.draw_landmarks(
                frame, hand_lm, mp.solutions.hands.HAND_CONNECTIONS
            )
            current_gesture = detect_gesture(hand_lm)

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

        draw_overlay(frame, candidate_gesture if candidate_count >= CONFIRM_FRAMES else GESTURE_NONE,
                     last_action_label, cooldown_remaining)

        cv2.imshow("Go2 Gesture Demo", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unitree Go2 Gesture Control Demo")
    parser.add_argument("--interface", default="eth0", help="ネットワークインターフェース名（例: eth0）")
    parser.add_argument("--camera", type=int, default=0, help="カメラデバイス番号")
    parser.add_argument("--dry-run", action="store_true", help="Go2に接続せずカメラと認識だけテスト")
    args = parser.parse_args()

    run(args.interface, args.camera, args.dry_run)
