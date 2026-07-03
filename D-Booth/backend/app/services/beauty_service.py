"""
Offline AI Beauty Processing Service v2.0 — High-Performance Edition
=====================================================================
MediaPipe FaceLandmarker (478-point) + OpenCV  ·  fully offline  ·  free

Dependencies (installed into project venv):
  opencv-python-headless  mediapipe  numpy

Speed targets (i5‑14600KF, CPU‑only):
  720p single face  →  < 45 ms    (LiveView)
  1080p single face →  < 120 ms   (preview)
  4000px single face → < 600 ms   (final print)
"""
from __future__ import annotations

import io
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# dependency guards
# ---------------------------------------------------------------------------
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available – beauty service disabled")

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    # model file location  (downloaded during setup)
    _MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
    _MODEL_PATH = str(_MODEL_DIR / "face_landmarker.task")

    # verify model exists; if path contains CJK characters MediaPipe's C++
    # backend may fail – copy to an ASCII-only location as a workaround.
    if not os.path.exists(_MODEL_PATH):
        _alt = Path("models/face_landmarker.task")
        if _alt.exists():
            _MODEL_PATH = str(_alt)

    if os.path.exists(_MODEL_PATH):
        _safe_dir = Path.home() / ".mediapipe_models"
        _safe_path = _safe_dir / "face_landmarker.task"
        _needs_copy = False
        try:
            _safe_dir.mkdir(parents=True, exist_ok=True)
            # always copy if the bundled path is non-ASCII
            if not _MODEL_PATH.isascii():
                import shutil
                shutil.copy2(_MODEL_PATH, str(_safe_path))
                _MODEL_PATH = str(_safe_path)
                _needs_copy = True
            elif not _safe_path.exists():
                import shutil
                shutil.copy2(_MODEL_PATH, str(_safe_path))
                _MODEL_PATH = str(_safe_path)
                _needs_copy = True
        except Exception:
            pass  # if copy fails, try original path anyway

    if os.path.exists(_MODEL_PATH):
        # base-options for FaceLandmarker (shared across instances)
        _IMG_BASE_OPTIONS = mp_python.BaseOptions(
            model_asset_path=_MODEL_PATH,
        )
    else:
        _IMG_BASE_OPTIONS = None
        logger.warning(
            "MediaPipe model not found – download from: "
            "https://storage.googleapis.com/mediapipe-models/"
            "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        )

    MEDIAPIPE_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    mp = None
    mp_python = None
    mp_vision = None
    _IMG_BASE_OPTIONS = None
    _MODEL_PATH = None
    MEDIAPIPE_AVAILABLE = False
    logger.warning("MediaPipe not available – face features disabled: %s", exc)

# detection thumbnail – smaller = faster but less reliable on tiny faces
_DETECT_MAX_SIDE = 480

# ---------------------------------------------------------------------------
# landmark index sets  (478‑point canonical model)
# ---------------------------------------------------------------------------
_JAWLINE = list(range(0, 17))
_LEFT_EYE = [33, 133, 155, 154, 153, 145, 144, 163, 7, 173, 157, 158, 159, 160, 161, 246]
_RIGHT_EYE = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]
_LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
_MOUTH_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14]
_IRIS_LEFT = [468, 469, 470, 471, 472]
_IRIS_RIGHT = [473, 474, 475, 476, 477]

# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
class BeautyParams(BaseModel):
    """0‑100 sliders matching front‑end UX"""
    smooth: int = Field(default=50, ge=0, le=100)
    whiten: int = Field(default=50, ge=0, le=100)
    thinFace: int = Field(default=50, ge=0, le=100)
    bigEye: int = Field(default=50, ge=0, le=100)
    eyeLight: int = Field(default=50, ge=0, le=100)
    acne: int = Field(default=50, ge=0, le=100)
    nasolabial: int = Field(default=50, ge=0, le=100)
    teethWhiten: int = Field(default=50, ge=0, le=100)
    lipColor: int = Field(default=50, ge=0, le=100)

# ---------------------------------------------------------------------------
# data classes
# ---------------------------------------------------------------------------
@dataclass
class FaceBox:
    x: int; y: int; width: int; height: int
    landmarks: Optional[List[Tuple[int, int]]] = None
    confidence: float = 0.0

@dataclass
class _FaceData:
    """Per‑face data extracted once, reused by all operators."""
    box: FaceBox
    landmarks: List[Tuple[int, int]]
    skin_mask: Optional[np.ndarray] = None  # 0‑255 uint8

# ---------------------------------------------------------------------------
# LUT cache for whitening  (pre‑computed lookup → O(1) per pixel)
# ---------------------------------------------------------------------------
def _build_whiten_lut(strength: float) -> np.ndarray:
    lut = np.arange(256, dtype=np.float32)
    lut = lut + strength * 40.0 * np.sin(lut / 256.0 * np.pi * 0.5)
    return np.clip(lut, 0, 255).astype(np.uint8)

_WHITEN_LUTS: dict[int, np.ndarray] = {}

def _get_whiten_lut(level: int) -> np.ndarray:
    level = max(0, min(100, level))
    if level not in _WHITEN_LUTS:
        _WHITEN_LUTS[level] = _build_whiten_lut(level / 100.0)
    return _WHITEN_LUTS[level]

# ---------------------------------------------------------------------------
# persistent FaceLandmarker (created once at module load; reuse across calls)
# Creating a new FaceLandmarker per request takes ~40 s because TFLite
# model loading is expensive.  A module‑level singleton avoids this.
# ---------------------------------------------------------------------------
_IMG_LANDMARKER: "Optional[mp_vision.FaceLandmarker]" = None
_IMG_LANDMARKER_LOCK = None  # threading.Lock – lazy import to avoid loader issues


def _get_landmarker() -> "mp_vision.FaceLandmarker":
    """Return or create the persistent FaceLandmarker (IMAGE mode, up to 10 faces)."""
    global _IMG_LANDMARKER, _IMG_LANDMARKER_LOCK
    if _IMG_LANDMARKER is not None:
        return _IMG_LANDMARKER

    if _IMG_LANDMARKER_LOCK is None:
        import threading as _thr
        _IMG_LANDMARKER_LOCK = _thr.Lock()

    with _IMG_LANDMARKER_LOCK:
        if _IMG_LANDMARKER is not None:
            return _IMG_LANDMARKER
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=_IMG_BASE_OPTIONS,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=10,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        _IMG_LANDMARKER = mp_vision.FaceLandmarker.create_from_options(opts)
        logger.info("FaceLandmarker created (persistent singleton)")
    return _IMG_LANDMARKER

# ---------------------------------------------------------------------------
# main processor
# ---------------------------------------------------------------------------
class BeautyProcessor:
    """Stateless beauty engine.  FaceLandmarker instances are created
    per‑call (they're lightweight to construct; the heavy TFLite model is
    loaded once from the file cache)."""

    def __init__(self):
        self._mp_ok = (
            MEDIAPIPE_AVAILABLE
            and _IMG_BASE_OPTIONS is not None
            and os.path.exists(str(_MODEL_PATH))
        )

    # -- public API --------------------------------------------------------
    def detect_faces(self, image_bytes: bytes, quality: str = "lite") -> List[FaceBox]:
        """Return faces with 478‑point landmarks.  quality = ``"lite"``| ``"full"``"""
        if not self._mp_ok or not OPENCV_AVAILABLE:
            return []
        try:
            img, sx, sy = self._decode_thumb(image_bytes)
            faces = self._run_face_landmarker(img, quality)
            for fb in faces:
                if fb.landmarks:
                    fb.landmarks = [(int(x * sx), int(y * sy)) for x, y in fb.landmarks]
                fb.x, fb.y = int(fb.x * sx), int(fb.y * sy)
                fb.width, fb.height = int(fb.width * sx), int(fb.height * sy)
            return faces
        except Exception:
            logger.exception("Face detection failed")
            return []

    def process_image(
        self, image_bytes: bytes, params: BeautyParams, *, quality: str = "full"
    ) -> bytes:
        """Full beauty pipeline.  ``quality="lite"`` skips thinFace/nasolabial for speed."""
        t0 = time.perf_counter()
        if not OPENCV_AVAILABLE:
            return image_bytes
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes
            h, w = img.shape[:2]

            # face detection on thumbnail (fast)
            faces: List[_FaceData] = []
            if self._mp_ok and self._any_face_op(params):
                det_img, sx, sy = self._decode_thumb(image_bytes)
                raw = self._run_face_landmarker(det_img, quality)
                for fb in raw:
                    fd = _FaceData(box=fb, landmarks=[])
                    if fb.landmarks:
                        fd.landmarks = [(int(x * sx), int(y * sy)) for x, y in fb.landmarks]
                    fd.box.x, fd.box.y = int(fb.x * sx), int(fb.y * sy)
                    fd.box.width, fd.box.height = int(fb.width * sx), int(fb.height * sy)
                    faces.append(fd)

            result = img

            # shared skin mask
            if faces and (params.smooth or params.whiten or params.acne or params.nasolabial):
                for fd in faces:
                    fd.skin_mask = self._skin_mask(h, w, fd.landmarks)

            # step 1  smooth + acne
            if params.smooth or params.acne:
                result = self._smooth(result, faces, max(params.smooth, params.acne))

            # step 2  whiten
            if params.whiten:
                result = self._whiten(result, faces, params.whiten)

            # step 3  nasolabial
            if params.nasolabial and quality != "lite" and faces:
                result = self._nasolabial(result, faces, params.nasolabial)

            # step 4  face slimming
            if params.thinFace and quality != "lite" and faces:
                for fd in faces:
                    result = self._thin_face(result, fd, params.thinFace)

            # step 5  big eyes
            if params.bigEye and faces:
                for fd in faces:
                    result = self._big_eye(result, fd, params.bigEye)

            # step 6  eye light
            if params.eyeLight and faces:
                result = self._eye_light(result, faces, params.eyeLight)

            # step 7  teeth whiten
            if params.teethWhiten and faces:
                result = self._teeth(result, faces, params.teethWhiten)

            # step 8  lip colour
            if params.lipColor and faces:
                result = self._lip(result, faces, params.lipColor)

            _, encoded = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 92])
            dt = (time.perf_counter() - t0) * 1000
            logger.debug("Beauty: %.0f ms  %dx%d  faces=%d  q=%s", dt, w, h, len(faces), quality)
            return encoded.tobytes()

        except Exception:
            logger.exception("Beauty pipeline crashed – returning original")
            return image_bytes

    # -- internal ----------------------------------------------------------
    @staticmethod
    def _any_face_op(p: BeautyParams) -> bool:
        return any(getattr(p, f, 0) for f in BeautyParams.model_fields)

    @staticmethod
    def _decode_thumb(data: bytes):
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("decode failed")
        h, w = img.shape[:2]
        s = _DETECT_MAX_SIDE / max(h, w) if max(h, w) > _DETECT_MAX_SIDE else 1.0
        if s < 1.0:
            img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        return img, 1.0 / s if s < 1.0 else 1.0, 1.0 / (s if s < 1.0 else 1.0)

    @staticmethod
    def _run_face_landmarker(img_bgr, quality) -> List[FaceBox]:
        """Run MediaPipe FaceLandmarker on a BGR image, return FaceBox list."""
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        h, w = img_bgr.shape[:2]
        faces: List[FaceBox] = []

        landmarker = _get_landmarker()
        result = landmarker.detect(mp_image)
        for face_lm in result.face_landmarks:
            xs = [lt.x * w for lt in face_lm]
            ys = [lt.y * h for lt in face_lm]
            pts = [(int(lt.x * w), int(lt.y * h)) for lt in face_lm]
            faces.append(FaceBox(
                x=int(min(xs)), y=int(min(ys)),
                width=int(max(xs) - min(xs)),
                height=int(max(ys) - min(ys)),
                landmarks=pts, confidence=1.0,
            ))
        return faces

    # -- skin mask ---------------------------------------------------------
    @staticmethod
    def _skin_mask(h, w, landmarks):
        mask = np.zeros((h, w), dtype=np.uint8)
        try:
            pts = np.array([landmarks[i] for i in _JAWLINE], dtype=np.int32)
            cv2.fillConvexPoly(mask, pts, 255)
            mask = cv2.GaussianBlur(mask, (21, 21), 10)
        except Exception:
            return np.ones((h, w), dtype=np.uint8) * 255
        return mask

    # -- smooth ------------------------------------------------------------
    @staticmethod
    def _smooth(img, faces, level):
        sigma = max(1.0, level / 100.0 * 20.0)
        smoothed = cv2.bilateralFilter(img, 7, sigma, sigma)
        if not faces or all(f.skin_mask is None for f in faces):
            a = level / 100.0
            return cv2.addWeighted(smoothed, a, img, 1.0 - a, 0)
        result = img.copy()
        for fd in faces:
            if fd.skin_mask is None:
                continue
            m = (cv2.merge([fd.skin_mask] * 3).astype(np.float32) / 255.0) * (level / 100.0)
            result = (smoothed * m + result * (1.0 - m)).astype(np.uint8)
        return result

    # -- whiten ------------------------------------------------------------
    @staticmethod
    def _whiten(img, faces, level):
        whitened = cv2.LUT(img, _get_whiten_lut(level))
        if not faces or all(f.skin_mask is None for f in faces):
            return cv2.addWeighted(whitened, level / 100.0 * 0.6, img, 1.0 - level / 100.0 * 0.6, 0)
        result = img.copy()
        for fd in faces:
            if fd.skin_mask is None:
                continue
            m = (cv2.merge([fd.skin_mask] * 3).astype(np.float32) / 255.0) * (level / 100.0 * 0.7)
            result = (whitened * m + result * (1.0 - m)).astype(np.uint8)
        return result

    # -- nasolabial --------------------------------------------------------
    @staticmethod
    def _nasolabial(img, faces, level):
        result = img.copy()
        for fd in faces:
            if not fd.landmarks:
                continue
            try:
                nose = fd.landmarks[1]
                for ci in (61, 291):
                    cx = (nose[0] + fd.landmarks[ci][0]) // 2
                    cy = (nose[1] + fd.landmarks[ci][1]) // 2
                    r = max(10, int(np.hypot(nose[0] - fd.landmarks[ci][0], nose[1] - fd.landmarks[ci][1]) * 0.3))
                    x1 = max(0, cx - r); y1 = max(0, cy - r)
                    x2 = min(img.shape[1], cx + r); y2 = min(img.shape[0], cy + r)
                    if x2 - x1 < 4 or y2 - y1 < 4:
                        continue
                    roi = result[y1:y2, x1:x2]
                    s = (level / 100.0) * 10.0 + 1.0
                    roi_s = cv2.bilateralFilter(roi, 5, s, s)
                    result[y1:y2, x1:x2] = cv2.addWeighted(roi_s, level / 100.0 * 0.6, roi, 1.0 - level / 100.0 * 0.6, 0)
            except Exception:
                continue
        return result

    # -- face slimming (remap displacement field) --------------------------
    @staticmethod
    def _thin_face(img, fd, level):
        if not fd.landmarks:
            return img
        try:
            h, w = img.shape[:2]
            strength = (level / 100.0) * 0.045
            jaw = np.array([fd.landmarks[i] for i in _JAWLINE], dtype=np.float32)
            cx, cy = float(fd.box.x + fd.box.width / 2), float(fd.box.y + fd.box.height / 2)
            dx = np.zeros((h, w), dtype=np.float32)
            dy = np.zeros((h, w), dtype=np.float32)
            for px, py in jaw:
                vx, vy = cx - px, cy - py
                d = np.hypot(vx, vy)
                if d < 1.0:
                    continue
                nx, ny = vx / d, vy / d
                radius = max(20, d * 0.6)
                yy, xx = np.ogrid[:h, :w]
                dist = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
                influence = np.clip(1.0 - dist / radius, 0, 1) ** 2
                dx += influence * nx * strength * radius
                dy += influence * ny * strength * radius
            dx = np.clip(dx, -w * 0.08, w * 0.08)
            dy = np.clip(dy, -h * 0.08, h * 0.08)
            map_x = (np.arange(w, dtype=np.float32) + dx.T).T
            map_y = (np.arange(h, dtype=np.float32)[:, None] + dy)
            return cv2.remap(img, map_x.astype(np.float32), map_y.astype(np.float32),
                             cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            return img

    # -- big eyes (remap radial expansion) ---------------------------------
    @staticmethod
    def _big_eye(img, fd, level):
        if not fd.landmarks:
            return img
        try:
            h, w = img.shape[:2]
            strength = (level / 100.0) * 0.07
            map_x = np.broadcast_to(np.arange(w, dtype=np.float32), (h, w)).copy()
            map_y = np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w)).copy()
            for idx in (_LEFT_EYE, _RIGHT_EYE):
                pts = np.array([fd.landmarks[i] for i in idx], dtype=np.float32)
                cx, cy = float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1]))
                r = max(8.0, float(np.max(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy))) * 1.8)
                yy, xx = np.ogrid[:h, :w]
                dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
                influence = np.clip(1.0 - dist / r, 0, 1) ** 3
                map_x += (xx - cx) * strength * influence
                map_y += (yy - cy) * strength * influence
            return cv2.remap(img, map_x.astype(np.float32), map_y.astype(np.float32),
                             cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            return img

    # -- eye light ---------------------------------------------------------
    @staticmethod
    def _eye_light(img, faces, level):
        result = img.copy()
        for fd in faces:
            if not fd.landmarks:
                continue
            try:
                for idx in (_IRIS_LEFT, _IRIS_RIGHT):
                    pts = np.array([fd.landmarks[i] for i in idx], dtype=np.float32)
                    cx, cy = int(np.mean(pts[:, 0])), int(np.mean(pts[:, 1]))
                    r = max(6, int(np.max(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)) * 2.5))
                    x1 = max(0, cx - r); y1 = max(0, cy - r)
                    x2 = min(img.shape[1], cx + r); y2 = min(img.shape[0], cy + r)
                    if x2 - x1 < 2 or y2 - y1 < 2:
                        continue
                    roi = cv2.cvtColor(result[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
                    h_c, s_c, v_c = cv2.split(roi)
                    v_c = cv2.convertScaleAbs(v_c, alpha=1.0 + (level / 100.0 * 0.4), beta=0)
                    s_c = cv2.convertScaleAbs(s_c, alpha=0.85, beta=0)
                    result[y1:y2, x1:x2] = cv2.cvtColor(cv2.merge([h_c, s_c, v_c]), cv2.COLOR_HSV2BGR)
            except Exception:
                continue
        return result

    # -- teeth whiten ------------------------------------------------------
    @staticmethod
    def _teeth(img, faces, level):
        result = img.copy()
        for fd in faces:
            if not fd.landmarks:
                continue
            try:
                pts = np.array([fd.landmarks[i] for i in _MOUTH_INNER], dtype=np.int32)
                hull = cv2.convexHull(pts)
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                cv2.fillConvexPoly(mask, hull, 255)
                mask = cv2.GaussianBlur(mask, (5, 5), 2)
                m = (cv2.merge([mask] * 3).astype(np.float32) / 255.0) * (level / 100.0)
                hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
                h_c, s_c, v_c = cv2.split(hsv)
                s_c = cv2.convertScaleAbs(s_c, alpha=1.0 - (level / 100.0 * 0.5), beta=0)
                v_c = cv2.convertScaleAbs(v_c, alpha=1.0 + (level / 100.0 * 0.25), beta=0)
                w = cv2.cvtColor(cv2.merge([h_c, s_c, v_c]), cv2.COLOR_HSV2BGR)
                result = (w * m + result * (1.0 - m)).astype(np.uint8)
            except Exception:
                continue
        return result

    # -- lip colour --------------------------------------------------------
    @staticmethod
    def _lip(img, faces, level):
        result = img.copy()
        for fd in faces:
            if not fd.landmarks:
                continue
            try:
                pts = np.array([fd.landmarks[i] for i in _LIPS_OUTER], dtype=np.int32)
                hull = cv2.convexHull(pts)
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                cv2.fillConvexPoly(mask, hull, 255)
                mask = cv2.GaussianBlur(mask, (7, 7), 3)
                m = (cv2.merge([mask] * 3).astype(np.float32) / 255.0) * (level / 100.0)
                hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
                h_c, s_c, v_c = cv2.split(hsv)
                s_c = cv2.convertScaleAbs(s_c, alpha=1.0 + (level / 100.0 * 0.6), beta=0)
                v_c = cv2.convertScaleAbs(v_c, alpha=1.0 + (level / 100.0 * 0.15), beta=0)
                coloured = cv2.cvtColor(cv2.merge([h_c, s_c, v_c]), cv2.COLOR_HSV2BGR)
                result = (coloured * m + result * (1.0 - m)).astype(np.uint8)
            except Exception:
                continue
        return result


# singleton
beauty_processor = BeautyProcessor()
