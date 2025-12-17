import argparse
import sys
import re
from pathlib import Path

import numpy as np
import imageio.v3 as iio


def rescale_to_uint8(img: np.ndarray, method: str = "percentile", p_low: float = 2.0, p_high: float = 98.0) -> np.ndarray:
    """
    Convert input image to uint8 with contrast normalization for visibility.
    - method="percentile": robust min/max from percentiles p_low/p_high
    - method="minmax": use exact min/max
    - method="none": if already uint8, return as-is; else clip to 0..255
    """
    if img.dtype == np.uint8:
        return img

    array = img.astype(np.float64, copy=False)
    if method == "percentile":
        lo = float(np.percentile(array, p_low))
        hi = float(np.percentile(array, p_high))
    elif method == "minmax":
        lo = float(np.min(array))
        hi = float(np.max(array))
    else:
        return np.clip(array, 0, 255).astype(np.uint8)

    if hi <= lo:
        return np.zeros_like(array, dtype=np.uint8)

    scaled = (array - lo) / (hi - lo)
    scaled = np.clip(scaled, 0.0, 1.0)
    return (scaled * 255.0 + 0.5).astype(np.uint8)


def find_timepoint_one_dir(plate_dir: Path) -> Path | None:
    """
    Return the "TimePoint_1" directory under a plate directory. If not present, return None.
    """
    if not plate_dir.is_dir():
        return None
    candidate = plate_dir / "TimePoint_1"
    return candidate if candidate.is_dir() else None


def convert_tif_to_png(
    input_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    preserve_16bit: bool = False,
    rescale_method: str = "percentile",
    rescale_p_low: float = 2.0,
    rescale_p_high: float = 98.0,
) -> int:
    """
    Iterate plates in input_dir, find the "TimePoint_1" dir within each plate,
    convert all 16-bit TIFs to PNG, and write to output_dir preserving
    plate/timepoint structure. Returns the number of converted files.
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    num_converted = 0
    tif_suffixes = {".tif", ".tiff", ".TIF", ".TIFF"}

    # Determine plates: if running inside a plate (contains TimePoint_1), treat
    # input_dir as the sole plate. Otherwise, traverse immediate subdirectories
    # (plates), skipping the output dir.
    if (input_dir / "TimePoint_1").is_dir():
        candidate_plates = [input_dir]
    else:
        candidate_plates = [
            p for p in input_dir.iterdir()
            if p.is_dir() and p.resolve() != output_dir.resolve()
        ]

    # Traverse candidate plates
    for plate_dir in sorted(candidate_plates):
        first_timepoint = find_timepoint_one_dir(plate_dir)
        if first_timepoint is None:
            continue

        # Determine destination base: output/Plate/TimePoint_X
        dest_base = output_dir / plate_dir.name / first_timepoint.name
        dest_base.mkdir(parents=True, exist_ok=True)

        # Convert each TIF within the first timepoint directory (recursive),
        # preserving any nested subdirectory structure under dest_base
        for tif_path in sorted(
            p for p in first_timepoint.rglob("*") if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}
        ):
            rel_path = tif_path.relative_to(first_timepoint)
            dst_path = (dest_base / rel_path).with_suffix(".png")

            if dst_path.exists():
                # Skip if already converted
                continue

            if dry_run:
                print(f"[DRY RUN] Would convert: {tif_path} -> {dst_path}")
                num_converted += 1
                continue

            # Read using imageio (with tifffile plugin under the hood) preserving dtype
            try:
                img = iio.imread(tif_path)
            except Exception as exc:
                print(f"Failed to read {tif_path}: {exc}", file=sys.stderr)
                continue

            # Ensure array is 2D or 3D; choose writing dtype
            if not isinstance(img, np.ndarray):
                print(f"Unexpected image type for {tif_path}: {type(img)}", file=sys.stderr)
                continue

            if preserve_16bit and img.dtype == np.uint16:
                write_array = img
            else:
                write_array = rescale_to_uint8(img, method=rescale_method, p_low=rescale_p_low, p_high=rescale_p_high)

            try:
                # imageio will emit a 16-bit PNG if dtype is uint16; otherwise uint8
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                iio.imwrite(dst_path, write_array)
                num_converted += 1
            except Exception as exc:
                print(f"Failed to write {dst_path}: {exc}", file=sys.stderr)
                # Best-effort: continue with others

    return num_converted


def parse_args(argv: list[str]) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir / "input"
    default_output = script_dir / "output"

    parser = argparse.ArgumentParser(
        description=(
            "Convert 16-bit TIF files in input/{plate}/TimePoint_1 to PNG, "
            "writing to output/{plate}/TimePoint_1. Defaults are relative to the script."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input,
        help="Input root directory (default: <script_dir>/input)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output,
        help="Output directory (default: <script_dir>/output)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing files",
    )
    parser.add_argument(
        "--preserve-16bit",
        action="store_true",
        help="If set, write uint16 PNG when source is uint16 (may appear dark)",
    )
    parser.add_argument(
        "--rescale-method",
        choices=["percentile", "minmax", "none"],
        default="percentile",
        help="Contrast normalization method for uint8 output (default: percentile)",
    )
    parser.add_argument(
        "--rescale-p-low",
        type=float,
        default=2.0,
        help="Low percentile for percentile rescaling (default: 2.0)",
    )
    parser.add_argument(
        "--rescale-p-high",
        type=float,
        default=98.0,
        help="High percentile for percentile rescaling (default: 98.0)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        num = convert_tif_to_png(
            args.input_dir,
            args.output_dir,
            dry_run=args.dry_run,
            preserve_16bit=args.preserve_16bit,
            rescale_method=args.rescale_method,
            rescale_p_low=args.rescale_p_low,
            rescale_p_high=args.rescale_p_high,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[DRY RUN] Files that would be converted: {num}")
    else:
        print(f"Converted {num} file(s) to PNG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


