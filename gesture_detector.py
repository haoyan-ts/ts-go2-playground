GESTURE_NONE = "NONE"
GESTURE_OPEN_HAND = "OPEN_HAND"  # パー → StandUp
GESTURE_FIST = "FIST"  # グー → StandDown
GESTURE_THUMB_UP = "THUMB_UP"  # サムズアップ → Dance
GESTURE_PEACE = "PEACE"  # ピース → Hello
GESTURE_POINT = "POINT"  # 指差し → RecoveryStand

_FINGER_TIPS = [
    8,
    12,
    16,
    20,
]
_FINGER_PIPS = [
    6,
    10,
    14,
    18,
]
_THUMB_TIP = 4
_THUMB_IP = 3


def _finger_extended(lm, tip, pip) -> bool:
    return lm[tip].y < lm[pip].y


def _thumb_extended(lm, handedness: str | None) -> bool:
    if handedness == "Left":
        return lm[_THUMB_TIP].x > lm[_THUMB_IP].x
    return lm[_THUMB_TIP].x < lm[_THUMB_IP].x


def detect_gesture(hand_landmarks, handedness: str | None = None) -> str:
    lm = hand_landmarks
    extended = [
        _finger_extended(lm, tip, pip) for tip, pip in zip(_FINGER_TIPS, _FINGER_PIPS)
    ]
    thumb_up = _thumb_extended(lm, handedness)

    index, middle, ring, pinky = extended

    if all(extended) and not thumb_up:
        return GESTURE_OPEN_HAND  # パー

    if not any(extended) and not thumb_up:
        return GESTURE_FIST  # グー

    if not any(extended) and thumb_up:
        return GESTURE_THUMB_UP  # サムズアップ

    if index and middle and not ring and not pinky:
        return GESTURE_PEACE  # ピース

    if index and not middle and not ring and not pinky:
        return GESTURE_POINT  # 指差し

    return GESTURE_NONE
