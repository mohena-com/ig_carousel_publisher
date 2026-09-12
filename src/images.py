from pathlib import Path

from PIL import Image


INSTAGRAM_WIDTH = 1080
INSTAGRAM_HEIGHT = 1350


def find_six_slides(input_dir: Path):
    if not input_dir.exists():
        raise FileNotFoundError(
            f"Input directory not found: {input_dir}"
        )

    slides = [
        input_dir / f"slide_{i}.png"
        for i in range(1, 7)
    ]

    missing = [
        str(p)
        for p in slides
        if not p.is_file()
    ]

    if missing:
        raise RuntimeError(
            "Exactly six PNG slides are required. Missing: "
            + ", ".join(missing)
        )

    return slides


def _save_meta_safe_jpeg(source: Path, target: Path):
    """
    Normalize an image into the JPEG representation proven reliable
    with Meta's Instagram media fetcher.

    Pipeline:
      source image
        -> RGB
        -> exact 1080x1350 pixel buffer
        -> baseline JPEG
        -> quality 85
        -> no optimization
        -> no progressive encoding
    """

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with Image.open(source) as im:
        clean = im.convert("RGB")

        # Force the exact Instagram portrait dimensions and create
        # a fresh pixel buffer even when the source is already 1080x1350.
        clean = clean.resize(
            (INSTAGRAM_WIDTH, INSTAGRAM_HEIGHT),
            Image.Resampling.LANCZOS,
        )

        clean.save(
            target,
            format="JPEG",
            quality=85,
            optimize=False,
            progressive=False,
        )

    # verify() and load() must use separate Image.open() calls.
    with Image.open(target) as check:
        check.verify()

    with Image.open(target) as check:
        check.load()

    return target


def convert_to_jpegs(slides, work_dir: Path):
    """Convert all six source slides into Meta-safe JPEGs."""

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    out = []

    for i, source in enumerate(slides, 1):
        target = work_dir / f"slide_{i}.jpg"
        _save_meta_safe_jpeg(source, target)
        out.append(target)

    return out


def reencode_jpeg(source: Path, target: Path):
    """Recovery helper using the same normalization pipeline."""
    return _save_meta_safe_jpeg(source, target)
