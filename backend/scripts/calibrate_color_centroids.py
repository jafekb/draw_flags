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
        results[label] = {
            "centroid_rgb": centroid_rgb,
            "centroid_lab": lab.mean(axis=0),
            "std_lab": lab.std(axis=0),
            "count": np.array([lab.shape[0]]),
        }
    return results


def confusion_matrix(
    centroids: dict[str, np.ndarray],
    samples: dict[str, np.ndarray],
) -> dict[str, dict[str, int]]:
    labels = list(centroids.keys())
    centroid_stack = np.stack([centroids[label] for label in labels], axis=0)
    confusion: dict[str, dict[str, int]] = {}
    for label in labels:
        rgb = samples[label]
        if rgb.size == 0:
            confusion[label] = dict.fromkeys(labels, 0)
            continue
        lab = rgb_to_lab(rgb)
        diffs = lab[:, None, :] - centroid_stack[None, :, :]
        distances = np.sum(diffs * diffs, axis=2)
        preds = np.argmin(distances, axis=1)
        counts = np.bincount(preds, minlength=len(labels))
        confusion[label] = {labels[i]: int(counts[i]) for i in range(len(labels))}
    return confusion


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

    confusion = confusion_matrix(
        {label: centroids[label]["centroid_lab"] for label in labels},
        samples,
    )

    if args.misclassified_dir is not None:
        args.misclassified_dir.mkdir(parents=True, exist_ok=True)
        centroid_stack = np.stack([centroids[label]["centroid_lab"] for label in labels], axis=0)
        for label in labels:
            for path, rgb in per_image.get(label, []):
                if rgb.size == 0:
                    continue
                lab = rgb_to_lab(rgb)
                diffs = lab[:, None, :] - centroid_stack[None, :, :]
                distances = np.sum(diffs * diffs, axis=2)
                preds = np.argmin(distances, axis=1)
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
        "labels": {
            label: {
                "centroid_rgb": centroids[label]["centroid_rgb"].tolist(),
                "centroid_lab": centroids[label]["centroid_lab"].tolist(),
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
