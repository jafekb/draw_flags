from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate LAB centroids for red/pink/purple samples",
    )
    parser.add_argument(
        "--colors-dir",
        type=Path,
        default=Path("backend/data/colors"),
        help="Root directory with labeled subdirectories",
    )
    parser.add_argument(
        "--labels",
        type=str,
        default="red,pink,purple",
        help="Comma-separated labels to include",
    )
    parser.add_argument(
        "--sample-max-per-image",
        type=int,
        default=20000,
        help="Max pixels sampled per image",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for pixel sampling",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON path for centroids and stats",
    )
    parser.add_argument(
        "--misclassified-dir",
        type=Path,
        default=None,
        help="Optional directory to copy misclassified images into",
    )
    parser.add_argument(
        "--misclass-threshold",
        type=float,
        default=0.5,
        help="Minimum fraction of pixels assigned to a wrong label",
    )
    parser.add_argument(
        "--space",
        type=str,
        choices=("lab", "hsv"),
        default="lab",
        help="Color space to compute centroids and confusion in",
    )
    parser.add_argument(
        "--neutral-sat-max",
        type=float,
        default=0.08,
        help="Max saturation to treat as neutral (gray/white/black)",
    )
    parser.add_argument(
        "--black-val-max",
        type=float,
        default=0.12,
        help="Max value to classify as black when neutral",
    )
    parser.add_argument(
        "--white-val-min",
        type=float,
        default=0.9,
        help="Min value to classify as white when neutral",
    )
    parser.add_argument(
        "--use-hsv-thresholds",
        action="store_true",
        help="Use HSV hue thresholds instead of centroid distance",
    )
    parser.add_argument(
        "--tune-hsv-thresholds",
        action="store_true",
        help="Tune HSV hue thresholds to maximize accuracy",
    )
    parser.add_argument(
        "--hue-step",
        type=float,
        default=1.0,
        help="Step size (degrees) for hue threshold search",
    )
    parser.add_argument(
        "--hue-window",
        type=float,
        default=20.0,
        help="Max deviation (degrees) from default thresholds",
    )
    parser.add_argument(
        "--use-color-gates",
        action="store_true",
        help="Apply per-color saturation/value gates to HSV thresholds",
    )
    parser.add_argument(
        "--gate-pct-min",
        type=float,
        default=10.0,
        help="Percentile for minimum saturation/value gates",
    )
    parser.add_argument(
        "--gate-pct-max",
        type=float,
        default=90.0,
        help="Percentile for maximum value gates",
    )
    parser.add_argument(
        "--tune-color-gates",
        action="store_true",
        help="Tune per-color value gates to maximize accuracy",
    )
    parser.add_argument(
        "--gate-percentiles",
        type=str,
        default="5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95",
        help="Comma-separated percentiles to try for tuning",
    )
    parser.add_argument(
        "--use-lab-thresholds",
        action="store_true",
        help="Use LAB thresholds for classification instead of centroids",
    )
    parser.add_argument(
        "--neutral-a-max",
        type=float,
        default=2.0,
        help="Max |a*| to treat as neutral in LAB",
    )
    parser.add_argument(
        "--neutral-b-max",
        type=float,
        default=2.0,
        help="Max |b*| to treat as neutral in LAB",
    )
    parser.add_argument(
        "--black-l-max",
        type=float,
        default=15.0,
        help="Max L* to classify as black when neutral",
    )
    parser.add_argument(
        "--white-l-min",
        type=float,
        default=90.0,
        help="Min L* to classify as white when neutral",
    )
    parser.add_argument(
        "--lab-distance",
        type=str,
        choices=("euclidean", "ciede2000"),
        default="ciede2000",
        help="Distance metric for LAB comparisons",
    )
    return parser.parse_args()


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb / 255.0
    mask = rgb <= 0.04045
    linear = np.where(mask, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return linear


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    linear = srgb_to_linear(rgb.astype(np.float32))
    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float32,
    )
    xyz = linear @ matrix.T
    xyz_ref = np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
    xyz = xyz / xyz_ref
    delta = 6 / 29
    delta3 = delta**3
    f = np.where(xyz > delta3, xyz ** (1 / 3), (xyz / (3 * delta**2)) + (4 / 29))
    l_val = (116 * f[:, 1]) - 16
    a_val = 500 * (f[:, 0] - f[:, 1])
    b_val = 200 * (f[:, 1] - f[:, 2])
    return np.stack([l_val, a_val, b_val], axis=1)


def delta_e_ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    l1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    l2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]

    c1 = np.sqrt(a1 * a1 + b1 * b1)
    c2 = np.sqrt(a2 * a2 + b2 * b2)
    c_bar = 0.5 * (c1 + c2)

    c_bar7 = c_bar**7
    g = 0.5 * (1 - np.sqrt(c_bar7 / (c_bar7 + 25**7)))
    a1p = (1 + g) * a1
    a2p = (1 + g) * a2
    c1p = np.sqrt(a1p * a1p + b1 * b1)
    c2p = np.sqrt(a2p * a2p + b2 * b2)

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dlp = l2 - l1
    dcp = c2p - c1p

    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, dhp)
    dhp = np.where(dhp < -180, dhp + 360, dhp)
    dhp = np.where((c1p * c2p) == 0, 0.0, dhp)
    dhp = np.radians(dhp)
    dhp = 2 * np.sqrt(c1p * c2p) * np.sin(dhp / 2)

    l_bar = 0.5 * (l1 + l2)
    c_bar_p = 0.5 * (c1p + c2p)

    h_sum = h1p + h2p
    h_bar = np.where(
        (c1p * c2p) == 0,
        h_sum,
        np.where(
            np.abs(h1p - h2p) > 180,
            h_sum + 360,
            h_sum,
        ),
    )
    h_bar = (h_bar / 2) % 360.0

    t = (
        1
        - 0.17 * np.cos(np.radians(h_bar - 30))
        + 0.24 * np.cos(np.radians(2 * h_bar))
        + 0.32 * np.cos(np.radians(3 * h_bar + 6))
        - 0.20 * np.cos(np.radians(4 * h_bar - 63))
    )

    delta_theta = 30 * np.exp(-(((h_bar - 275) / 25) ** 2))
    r_c = 2 * np.sqrt((c_bar_p**7) / (c_bar_p**7 + 25**7))
    s_l = 1 + (0.015 * (l_bar - 50) ** 2) / np.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_bar_p
    s_h = 1 + 0.015 * c_bar_p * t
    r_t = -np.sin(np.radians(2 * delta_theta)) * r_c

    d_e = np.sqrt(
        (dlp / s_l) ** 2 + (dcp / s_c) ** 2 + (dhp / s_h) ** 2 + r_t * (dcp / s_c) * (dhp / s_h)
    )
    return d_e


def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.float32) / 255.0
    c_max = np.max(rgb, axis=1)
    c_min = np.min(rgb, axis=1)
    delta = c_max - c_min

    hue = np.zeros_like(c_max)
    nonzero = delta > 0
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]

    red_mask = nonzero & (c_max == r)
    green_mask = nonzero & (c_max == g)
    blue_mask = nonzero & (c_max == b)

    hue[red_mask] = (60 * ((g[red_mask] - b[red_mask]) / delta[red_mask])) % 360
    hue[green_mask] = 60 * ((b[green_mask] - r[green_mask]) / delta[green_mask] + 2)
    hue[blue_mask] = 60 * ((r[blue_mask] - g[blue_mask]) / delta[blue_mask] + 4)

    saturation = np.zeros_like(c_max)
    nonzero_value = c_max > 0
    saturation[nonzero_value] = delta[nonzero_value] / c_max[nonzero_value]

    value = c_max
    return np.stack([hue, saturation, value], axis=1)


def hsv_distance(samples: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    hue_diff = np.abs(samples[:, 0] - centroid[0])
    hue_diff = np.minimum(hue_diff, 360.0 - hue_diff) / 180.0
    sat_diff = np.abs(samples[:, 1] - centroid[1])
    val_diff = np.abs(samples[:, 2] - centroid[2])
    return hue_diff**2 + sat_diff**2 + val_diff**2


def classify_hsv_thresholds(
    hsv: np.ndarray,
    labels: list[str],
    neutral_sat_max: float,
    black_val_max: float,
    white_val_min: float,
    hue_thresholds: dict[str, float] | None = None,
    color_gates: dict[str, dict[str, float]] | None = None,
) -> np.ndarray:
    preds = np.empty(hsv.shape[0], dtype=np.int64)
    neutral_mask = hsv[:, 1] <= neutral_sat_max

    black_idx = labels.index("black") if "black" in labels else None
    white_idx = labels.index("white") if "white" in labels else None
    gray_idx = labels.index("gray") if "gray" in labels else None

    if neutral_mask.any() and gray_idx is not None:
        neutral_vals = hsv[neutral_mask, 2]
        neutral_preds = np.full(neutral_vals.shape[0], gray_idx, dtype=np.int64)
        if black_idx is not None:
            neutral_preds[neutral_vals <= black_val_max] = black_idx
        if white_idx is not None:
            neutral_preds[neutral_vals >= white_val_min] = white_idx
        preds[neutral_mask] = neutral_preds

    color_mask = ~neutral_mask
    if color_mask.any():
        hue = hsv[color_mask, 0]
        color_preds = np.full(hue.shape[0], -1, dtype=np.int64)

        thresholds = hue_thresholds or {
            "red_orange": 14.0,
            "orange_yellow": 36.0,
            "yellow_green": 68.0,
            "green_light_blue": 152.0,
            "light_blue_blue": 200.0,
            "blue_purple": 263.0,
            "purple_pink": 285.0,
            "pink_red": 341.0,
        }

        red_orange = thresholds["red_orange"]
        orange_yellow = thresholds["orange_yellow"]
        yellow_green = thresholds["yellow_green"]
        green_light_blue = thresholds["green_light_blue"]
        light_blue_blue = thresholds["light_blue_blue"]
        blue_purple = thresholds["blue_purple"]
        purple_pink = thresholds["purple_pink"]
        pink_red = thresholds["pink_red"]

        ranges = [
            ("red", hue < red_orange),
            ("red", hue > pink_red),
            ("orange", (hue >= red_orange) & (hue < orange_yellow)),
            ("yellow", (hue >= orange_yellow) & (hue < yellow_green)),
            ("green", (hue >= yellow_green) & (hue < green_light_blue)),
            ("light_blue", (hue >= green_light_blue) & (hue < light_blue_blue)),
            ("blue", (hue > light_blue_blue) & (hue < blue_purple)),
            ("purple", (hue >= blue_purple) & (hue < purple_pink)),
            ("pink", (hue > purple_pink) & (hue <= pink_red)),
        ]

        for label, mask in ranges:
            if label in labels:
                color_preds[mask] = labels.index(label)

        if color_gates:
            alternates = {
                "red": ("pink", "purple"),
                "pink": ("red", "purple"),
                "purple": ("pink", "blue"),
                "blue": ("light_blue", "purple"),
                "light_blue": ("blue",),
            }

            for label, alt_labels in alternates.items():
                if label not in labels:
                    continue
                label_idx = labels.index(label)
                label_mask = color_preds == label_idx
                if not label_mask.any():
                    continue
                gate = color_gates.get(label, {})
                min_s = gate.get("min_s")
                max_s = gate.get("max_s")
                min_v = gate.get("min_v")
                max_v = gate.get("max_v")
                gate_mask = np.ones(label_mask.sum(), dtype=bool)
                if min_s is not None:
                    gate_mask &= hsv[color_mask][label_mask, 1] >= min_s
                if max_s is not None:
                    gate_mask &= hsv[color_mask][label_mask, 1] <= max_s
                if min_v is not None:
                    gate_mask &= hsv[color_mask][label_mask, 2] >= min_v
                if max_v is not None:
                    gate_mask &= hsv[color_mask][label_mask, 2] <= max_v

                reassign_mask = label_mask.copy()
                reassign_mask[label_mask] = ~gate_mask
                if not reassign_mask.any():
                    continue

                reassigned = False
                for alt in alt_labels:
                    if alt not in labels:
                        continue
                    alt_gate = color_gates.get(alt, {})
                    alt_idx = labels.index(alt)
                    alt_mask = np.ones(reassign_mask.sum(), dtype=bool)
                    alt_min_s = alt_gate.get("min_s")
                    alt_max_s = alt_gate.get("max_s")
                    alt_min_v = alt_gate.get("min_v")
                    alt_max_v = alt_gate.get("max_v")
                    if alt_min_s is not None:
                        alt_mask &= hsv[color_mask][reassign_mask, 1] >= alt_min_s
                    if alt_max_s is not None:
                        alt_mask &= hsv[color_mask][reassign_mask, 1] <= alt_max_s
                    if alt_min_v is not None:
                        alt_mask &= hsv[color_mask][reassign_mask, 2] >= alt_min_v
                    if alt_max_v is not None:
                        alt_mask &= hsv[color_mask][reassign_mask, 2] <= alt_max_v
                    if alt_mask.any():
                        reassigned = True
                        reassign_indices = np.where(reassign_mask)[0]
                        color_preds[reassign_indices[alt_mask]] = alt_idx
                        break

                if not reassigned:
                    color_preds[reassign_mask] = label_idx

        fallback = labels.index("blue") if "blue" in labels else 0
        color_preds[color_preds == -1] = fallback
        preds[color_mask] = color_preds

    return preds


def load_rgb_pixels(path: Path, sample_max: int, rng: np.random.Generator) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    pixels = np.array(image).reshape(-1, 4)
    opaque = pixels[:, 3] > 0
    rgb = pixels[opaque, :3]
    if rgb.size == 0:
        return rgb
    if sample_max and rgb.shape[0] > sample_max:
        indices = rng.choice(rgb.shape[0], size=sample_max, replace=False)
        rgb = rgb[indices]
    return rgb


def collect_samples(
    colors_dir: Path,
    labels: list[str],
    sample_max_per_image: int,
    rng: np.random.Generator,
) -> tuple[dict[str, np.ndarray], dict[str, list[tuple[Path, np.ndarray]]]]:
    samples: dict[str, list[np.ndarray]] = {label: [] for label in labels}
    per_image: dict[str, list[tuple[Path, np.ndarray]]] = {label: [] for label in labels}
    for label in labels:
        label_dir = colors_dir / label
        if not label_dir.is_dir():
            raise FileNotFoundError(f"Missing label directory: {label_dir}")
        for path in sorted(label_dir.glob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif"}:
                continue
            rgb = load_rgb_pixels(path, sample_max_per_image, rng)
            if rgb.size > 0:
                samples[label].append(rgb)
                per_image[label].append((path, rgb))
    stacked = {
        label: np.vstack(items) if items else np.empty((0, 3)) for label, items in samples.items()
    }
    return stacked, per_image


def compute_centroids(samples: dict[str, np.ndarray]) -> dict[str, dict[str, np.ndarray]]:
    results: dict[str, dict[str, np.ndarray]] = {}
    for label, rgb in samples.items():
        lab = rgb_to_lab(rgb) if rgb.size else np.empty((0, 3))
        if lab.size == 0:
            results[label] = {
                "centroid_rgb": np.array([np.nan, np.nan, np.nan]),
                "centroid_lab": np.array([np.nan, np.nan, np.nan]),
                "std_lab": np.array([np.nan, np.nan, np.nan]),
                "count": np.array([0]),
            }
            continue
        centroid_rgb = np.rint(rgb.mean(axis=0)).astype(int)
        centroid_lab = lab.mean(axis=0)
        centroid_hsv = rgb_to_hsv(centroid_rgb[None, :])[0]
        results[label] = {
            "centroid_rgb": centroid_rgb,
            "centroid_lab": centroid_lab,
            "centroid_hsv": centroid_hsv,
            "std_lab": lab.std(axis=0),
            "count": np.array([lab.shape[0]]),
        }
    return results


def confusion_matrix(
    centroids: dict[str, np.ndarray],
    samples: dict[str, np.ndarray],
    *,
    space: str,
    neutral_sat_max: float,
    black_val_max: float,
    white_val_min: float,
    use_hsv_thresholds: bool,
    hue_thresholds: dict[str, float] | None = None,
    color_gates: dict[str, dict[str, float]] | None = None,
    use_lab_thresholds: bool = False,
    neutral_a_max: float = 2.0,
    neutral_b_max: float = 2.0,
    black_l_max: float = 15.0,
    white_l_min: float = 90.0,
    lab_centroids: dict[str, np.ndarray] | None = None,
    lab_distance: str = "euclidean",
) -> dict[str, dict[str, int]]:
    labels = list(centroids.keys())
    centroid_stack = np.stack([centroids[label] for label in labels], axis=0)
    confusion: dict[str, dict[str, int]] = {}
    for label in labels:
        rgb = samples[label]
        if rgb.size == 0:
            confusion[label] = dict.fromkeys(labels, 0)
            continue
        if space == "lab" and use_lab_thresholds:
            lab = rgb_to_lab(rgb)
            preds = classify_lab_thresholds(
                lab,
                labels,
                neutral_a_max,
                neutral_b_max,
                black_l_max,
                white_l_min,
                lab_centroids or {},
                lab_distance,
            )
        elif space == "lab" and not use_hsv_thresholds:
            lab = rgb_to_lab(rgb)
            distances = lab_distances(lab, centroid_stack, lab_distance)
            preds = np.argmin(distances, axis=1)
        else:
            hsv = rgb_to_hsv(rgb)
            if use_hsv_thresholds:
                preds = classify_hsv_thresholds(
                    hsv,
                    labels,
                    neutral_sat_max,
                    black_val_max,
                    white_val_min,
                    hue_thresholds=hue_thresholds,
                    color_gates=color_gates,
                )
            else:
                neutral_mask = hsv[:, 1] <= neutral_sat_max
                preds = np.empty(hsv.shape[0], dtype=np.int64)

                black_idx = labels.index("black") if "black" in labels else None
                white_idx = labels.index("white") if "white" in labels else None
                gray_idx = labels.index("gray") if "gray" in labels else None

                if neutral_mask.any() and gray_idx is not None:
                    neutral_vals = hsv[neutral_mask, 2]
                    neutral_preds = np.full(neutral_vals.shape[0], gray_idx, dtype=np.int64)
                    if black_idx is not None:
                        neutral_preds[neutral_vals <= black_val_max] = black_idx
                    if white_idx is not None:
                        neutral_preds[neutral_vals >= white_val_min] = white_idx
                    preds[neutral_mask] = neutral_preds

                color_mask = ~neutral_mask
                if color_mask.any():
                    color_hsv = hsv[color_mask]
                    distances = np.stack(
                        [hsv_distance(color_hsv, centroid_stack[i]) for i in range(len(labels))],
                        axis=1,
                    )
                    preds[color_mask] = np.argmin(distances, axis=1)
        counts = np.bincount(preds, minlength=len(labels))
        confusion[label] = {labels[i]: int(counts[i]) for i in range(len(labels))}
    return confusion


def compute_color_gates(
    samples: dict[str, np.ndarray],
    labels: list[str],
    pct_min: float,
    pct_max: float,
) -> dict[str, dict[str, float]]:
    targets = {"light_blue", "pink", "purple", "red", "blue"}
    gates: dict[str, dict[str, float]] = {}
    for label in labels:
        if label not in targets:
            continue
        rgb = samples[label]
        if rgb.size == 0:
            continue
        hsv = rgb_to_hsv(rgb)
        gates[label] = {
            "min_s": float(np.percentile(hsv[:, 1], pct_min)),
            "max_s": float(np.percentile(hsv[:, 1], pct_max)),
            "min_v": float(np.percentile(hsv[:, 2], pct_min)),
            "max_v": float(np.percentile(hsv[:, 2], pct_max)),
        }
    return gates


def precompute_gate_percentiles(
    samples: dict[str, np.ndarray],
    labels: list[str],
    percentiles: list[float],
) -> dict[str, dict[str, dict[float, float]]]:
    stats: dict[str, dict[str, dict[float, float]]] = {}
    for label in labels:
        rgb = samples[label]
        if rgb.size == 0:
            continue
        hsv = rgb_to_hsv(rgb)
        stats[label] = {
            "s": {p: float(np.percentile(hsv[:, 1], p)) for p in percentiles},
            "v": {p: float(np.percentile(hsv[:, 2], p)) for p in percentiles},
        }
    return stats


def tune_color_gates(
    samples: dict[str, np.ndarray],
    labels: list[str],
    hue_thresholds: dict[str, float] | None,
    neutral_sat_max: float,
    black_val_max: float,
    white_val_min: float,
    base_gates: dict[str, dict[str, float]],
    percentiles: list[float],
) -> dict[str, dict[str, float]]:
    targets = {"light_blue", "pink", "purple", "red", "blue"}
    percentile_stats = precompute_gate_percentiles(samples, labels, percentiles)

    def accuracy(gates: dict[str, dict[str, float]]) -> int:
        correct = 0
        total = 0
        for label in labels:
            rgb = samples[label]
            if rgb.size == 0:
                continue
            hsv = rgb_to_hsv(rgb)
            preds = classify_hsv_thresholds(
                hsv,
                labels,
                neutral_sat_max,
                black_val_max,
                white_val_min,
                hue_thresholds=hue_thresholds,
                color_gates=gates,
            )
            counts = np.bincount(preds, minlength=len(labels))
            pred_label = labels[int(np.argmax(counts))]
            if pred_label == label:
                correct += 1
            total += 1
        return correct * 10000 + total

    gates = {label: base_gates.get(label, {}).copy() for label in labels}
    best_score = accuracy(gates)

    for label in labels:
        if label not in targets or label not in percentile_stats:
            continue
        for key in ("min_v", "max_v"):
            current = gates.get(label, {}).get(key)
            if current is None:
                continue
            best_val = current
            for pct in percentiles:
                candidate = percentile_stats[label]["v"][pct]
                min_v = gates[label].get("min_v", 0.0)
                max_v = gates[label].get("max_v", 1.0)
                if key == "min_v":
                    if candidate >= max_v:
                        continue
                    gates[label]["min_v"] = candidate
                else:
                    if candidate <= min_v:
                        continue
                    gates[label]["max_v"] = candidate
                score = accuracy(gates)
                if score > best_score:
                    best_score = score
                    best_val = candidate
            gates[label][key] = best_val

    return gates


def classify_lab_thresholds(
    lab: np.ndarray,
    labels: list[str],
    neutral_a_max: float,
    neutral_b_max: float,
    black_l_max: float,
    white_l_min: float,
    lab_centroids: dict[str, np.ndarray],
    lab_distance: str,
) -> np.ndarray:
    preds = np.empty(lab.shape[0], dtype=np.int64)
    neutral_mask = (np.abs(lab[:, 1]) <= neutral_a_max) & (np.abs(lab[:, 2]) <= neutral_b_max)

    black_idx = labels.index("black") if "black" in labels else None
    white_idx = labels.index("white") if "white" in labels else None
    gray_idx = labels.index("gray") if "gray" in labels else None

    if neutral_mask.any() and gray_idx is not None:
        neutral_vals = lab[neutral_mask, 0]
        neutral_preds = np.full(neutral_vals.shape[0], gray_idx, dtype=np.int64)
        if black_idx is not None:
            neutral_preds[neutral_vals <= black_l_max] = black_idx
        if white_idx is not None:
            neutral_preds[neutral_vals >= white_l_min] = white_idx
        preds[neutral_mask] = neutral_preds

    color_mask = ~neutral_mask
    if color_mask.any():
        color_lab = lab[color_mask]
        names = [name for name in labels if name not in {"black", "white", "gray"}]
        centroid_stack = np.stack([lab_centroids[name] for name in names], axis=0)
        distances = lab_distances(color_lab, centroid_stack, lab_distance)
        indices = np.argmin(distances, axis=1)
        mapped = np.array([labels.index(names[i]) for i in indices], dtype=np.int64)
        preds[color_mask] = mapped

    return preds


def lab_distances(samples: np.ndarray, centroids: np.ndarray, metric: str) -> np.ndarray:
    if metric == "euclidean":
        diffs = samples[:, None, :] - centroids[None, :, :]
        return np.sum(diffs * diffs, axis=2)
    distances = np.zeros((samples.shape[0], centroids.shape[0]), dtype=np.float32)
    for idx in range(centroids.shape[0]):
        centroid = np.repeat(centroids[idx][None, :], samples.shape[0], axis=0)
        distances[:, idx] = delta_e_ciede2000(samples, centroid)
    return distances


def tune_hsv_thresholds(
    samples: dict[str, np.ndarray],
    labels: list[str],
    neutral_sat_max: float,
    black_val_max: float,
    white_val_min: float,
    hue_step: float,
    hue_window: float,
) -> dict[str, float]:
    defaults = {
        "red_orange": 14.0,
        "orange_yellow": 36.0,
        "yellow_green": 68.0,
        "green_light_blue": 152.0,
        "light_blue_blue": 200.0,
        "blue_purple": 263.0,
        "purple_pink": 285.0,
        "pink_red": 341.0,
    }

    def accuracy(thresholds: dict[str, float]) -> int:
        correct = 0
        total = 0
        for label in labels:
            rgb = samples[label]
            if rgb.size == 0:
                continue
            hsv = rgb_to_hsv(rgb)
            preds = classify_hsv_thresholds(
                hsv,
                labels,
                neutral_sat_max,
                black_val_max,
                white_val_min,
                hue_thresholds=thresholds,
            )
            counts = np.bincount(preds, minlength=len(labels))
            pred_label = labels[int(np.argmax(counts))]
            if pred_label == label:
                correct += 1
            total += 1
        return correct * 10000 + total

    thresholds = defaults.copy()
    keys = list(thresholds.keys())

    for _ in range(3):
        improved = False
        for key in keys:
            current = thresholds[key]
            if key == "red_orange":
                lower = max(0.0, current - hue_window)
                upper = min(thresholds["orange_yellow"] - 1.0, current + hue_window)
            elif key == "pink_red":
                lower = max(thresholds["purple_pink"] + 1.0, current - hue_window)
                upper = min(360.0, current + hue_window)
            else:
                order = keys
                idx = order.index(key)
                prev_key = order[idx - 1] if idx > 0 else None
                next_key = order[idx + 1] if idx + 1 < len(order) else None
                lower = current - hue_window
                upper = current + hue_window
                if prev_key:
                    lower = max(lower, thresholds[prev_key] + 1.0)
                if next_key:
                    upper = min(upper, thresholds[next_key] - 1.0)

            candidates = np.arange(lower, upper + 0.001, hue_step)
            best = current
            best_score = accuracy(thresholds)
            for cand in candidates:
                thresholds[key] = float(cand)
                score = accuracy(thresholds)
                if score > best_score:
                    best_score = score
                    best = float(cand)
            thresholds[key] = best
            if best != current:
                improved = True
        if not improved:
            break

    return thresholds


def main() -> None:
    args = parse_args()
    labels = [label.strip() for label in args.labels.split(",") if label.strip()]
    colors_dir = args.colors_dir
    rng = np.random.default_rng(args.seed)

    samples, per_image = collect_samples(colors_dir, labels, args.sample_max_per_image, rng)
    centroids = compute_centroids(samples)

    hsv_stats: dict[str, dict[str, float]] = {}
    for label, rgb in samples.items():
        if rgb.size == 0:
            hsv_stats[label] = {"sat_p05": float("nan"), "val_p05": float("nan")}
            continue
        hsv = rgb_to_hsv(rgb)
        hsv_stats[label] = {
            "sat_p05": float(np.percentile(hsv[:, 1], 5)),
            "val_p05": float(np.percentile(hsv[:, 2], 5)),
        }

    min_sat = min(stats["sat_p05"] for stats in hsv_stats.values())
    min_val = min(stats["val_p05"] for stats in hsv_stats.values())

    if args.space == "lab":
        centroid_space = {label: centroids[label]["centroid_lab"] for label in labels}
    else:
        centroid_space = {label: centroids[label]["centroid_hsv"] for label in labels}

    hue_thresholds = None
    if args.use_hsv_thresholds:
        hue_thresholds = (
            tune_hsv_thresholds(
                samples,
                labels,
                args.neutral_sat_max,
                args.black_val_max,
                args.white_val_min,
                args.hue_step,
                args.hue_window,
            )
            if args.tune_hsv_thresholds
            else None
        )

    color_gates = (
        compute_color_gates(
            samples,
            labels,
            args.gate_pct_min,
            args.gate_pct_max,
        )
        if args.use_hsv_thresholds and args.use_color_gates
        else None
    )
    if color_gates is not None and args.tune_color_gates:
        percentiles = [float(p.strip()) for p in args.gate_percentiles.split(",") if p.strip()]
        color_gates = tune_color_gates(
            samples,
            labels,
            hue_thresholds,
            args.neutral_sat_max,
            args.black_val_max,
            args.white_val_min,
            color_gates,
            percentiles,
        )

    confusion = confusion_matrix(
        centroid_space,
        samples,
        space=args.space,
        neutral_sat_max=args.neutral_sat_max,
        black_val_max=args.black_val_max,
        white_val_min=args.white_val_min,
        use_hsv_thresholds=args.use_hsv_thresholds,
        hue_thresholds=hue_thresholds,
        color_gates=color_gates,
        use_lab_thresholds=args.use_lab_thresholds,
        neutral_a_max=args.neutral_a_max,
        neutral_b_max=args.neutral_b_max,
        black_l_max=args.black_l_max,
        white_l_min=args.white_l_min,
        lab_centroids={label: centroids[label]["centroid_lab"] for label in labels},
        lab_distance=args.lab_distance,
    )

    if args.misclassified_dir is not None:
        args.misclassified_dir.mkdir(parents=True, exist_ok=True)
        centroid_stack = np.stack([centroid_space[label] for label in labels], axis=0)
        for label in labels:
            for path, rgb in per_image.get(label, []):
                if rgb.size == 0:
                    continue
                if args.space == "lab" and args.use_lab_thresholds:
                    lab = rgb_to_lab(rgb)
                    preds = classify_lab_thresholds(
                        lab,
                        labels,
                        args.neutral_a_max,
                        args.neutral_b_max,
                        args.black_l_max,
                        args.white_l_min,
                        {label: centroids[label]["centroid_lab"] for label in labels},
                        args.lab_distance,
                    )
                elif args.space == "lab" and not args.use_hsv_thresholds:
                    lab = rgb_to_lab(rgb)
                    distances = lab_distances(lab, centroid_stack, args.lab_distance)
                    preds = np.argmin(distances, axis=1)
                else:
                    hsv = rgb_to_hsv(rgb)
                    if args.use_hsv_thresholds:
                        preds = classify_hsv_thresholds(
                            hsv,
                            labels,
                            args.neutral_sat_max,
                            args.black_val_max,
                            args.white_val_min,
                            hue_thresholds=hue_thresholds,
                            color_gates=color_gates,
                        )
                    else:
                        neutral_mask = hsv[:, 1] <= args.neutral_sat_max
                        preds = np.empty(hsv.shape[0], dtype=np.int64)

                        black_idx = labels.index("black") if "black" in labels else None
                        white_idx = labels.index("white") if "white" in labels else None
                        gray_idx = labels.index("gray") if "gray" in labels else None

                        if neutral_mask.any() and gray_idx is not None:
                            neutral_vals = hsv[neutral_mask, 2]
                            neutral_preds = np.full(neutral_vals.shape[0], gray_idx, dtype=np.int64)
                            if black_idx is not None:
                                neutral_preds[neutral_vals <= args.black_val_max] = black_idx
                            if white_idx is not None:
                                neutral_preds[neutral_vals >= args.white_val_min] = white_idx
                            preds[neutral_mask] = neutral_preds

                        color_mask = ~neutral_mask
                        if color_mask.any():
                            color_hsv = hsv[color_mask]
                            distances = np.stack(
                                [
                                    hsv_distance(color_hsv, centroid_stack[i])
                                    for i in range(len(labels))
                                ],
                                axis=1,
                            )
                            preds[color_mask] = np.argmin(distances, axis=1)
                counts = np.bincount(preds, minlength=len(labels))
                pred_idx = int(np.argmax(counts))
                pred_label = labels[pred_idx]
                total = counts.sum()
                if total == 0:
                    continue
                misclass_ratio = 1.0 - (counts[labels.index(label)] / float(total))
                if pred_label != label and misclass_ratio >= args.misclass_threshold:
                    safe_name = path.stem.replace(" ", "_")
                    target = (
                        args.misclassified_dir
                        / f"label_{label}_misclassified-as_{pred_label}_{safe_name}{path.suffix}"
                    )
                    shutil.copy(path, target)

    report = {
        "space": args.space,
        "use_hsv_thresholds": args.use_hsv_thresholds,
        "hue_thresholds": hue_thresholds,
        "color_gates": color_gates,
        "use_lab_thresholds": args.use_lab_thresholds,
        "lab_thresholds": {
            "neutral_a_max": args.neutral_a_max,
            "neutral_b_max": args.neutral_b_max,
            "black_l_max": args.black_l_max,
            "white_l_min": args.white_l_min,
        },
        "lab_distance": args.lab_distance,
        "labels": {
            label: {
                "centroid_rgb": centroids[label]["centroid_rgb"].tolist(),
                "centroid_lab": centroids[label]["centroid_lab"].tolist(),
                "centroid_hsv": centroids[label]["centroid_hsv"].tolist(),
                "std_lab": centroids[label]["std_lab"].tolist(),
                "count": int(centroids[label]["count"][0]),
                "sat_p05": hsv_stats[label]["sat_p05"],
                "val_p05": hsv_stats[label]["val_p05"],
            }
            for label in labels
        },
        "suggested_guardrail": {
            "min_saturation": min_sat,
            "min_value": min_val,
        },
        "confusion": confusion,
    }

    report_text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(report_text)
    print(report_text)


if __name__ == "__main__":
    main()
