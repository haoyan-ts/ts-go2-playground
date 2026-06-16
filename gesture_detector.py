import mediapipe as mp

GESTURE_NONE = "NONE"
GESTURE_OPEN_HAND = "OPEN_HAND"      # パー → StandUp
GESTURE_FIST = "FIST"                # グー → StandDown
GESTURE_THUMB_UP = "THUMB_UP"        # サムズアップ → Dance
GESTURE_PEACE = "PEACE"              # ピース → Hello
GESTURE_POINT = "POINT"              # 指差し → RecoveryStand

_FINGER_TIPS = [
    mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP,
    mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP,
    mp.solutions.hands.HandLandmark.RING_FINGER_TIP,
    mp.solutions.hands.HandLandmark.PINKY_TIP,
]
_FINGER_PIPS = [
    mp.solutions.hands.HandLandmark.INDEX_FINGER_PIP,
    mp.solutions.hands.HandLandmark.MIDDLE_FINGER_PIP,
    mp.solutions.hands.HandLandmark.RING_FINGER_PIP,
    mp.solutions.hands.HandLandmark.PINKY_PIP,
]


def _finger_extended(lm, tip, pip) -> bool:
    return lm[tip].y < lm[pip].y


def _thumb_extended(lm) -> bool:
    tip = mp.solutions.hands.HandLandmark.THUMB_TIP
    ip = mp.solutions.hands.HandLandmark.THUMB_IP
    return lm[tip].x < lm[ip].x  # 右手前提（左手は逆になる）


def detect_gesture(hand_landmarks) -> str:
    lm = hand_landmarks.landmark
    extended = [_finger_extended(lm, tip, pip) for tip, pip in zip(_FINGER_TIPS, _FINGER_PIPS)]
    thumb_up = _thumb_extended(lm)

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
