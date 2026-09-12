from pathlib import Path

from PIL import Image


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


def convert_to_jpegs(slides, work_dir: Path):
    """
    Convert all source slides into conservative, Meta-compatible JPEGs.

    The JPEG is deliberately normalized:
      - RGB
      - quality 90
      - non-progressive
      - no optimization
      - no source metadata
    """

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    out = []

    for i, source in enumerate(slides, 1):
        target = work_dir / f"slide_{i}.jpg"

        with Image.open(source) as im:
            # Force a clean RGB pixel buffer. This also strips
            # problematic PNG metadata/color-mode information.
            clean = im.convert("RGB")

            clean.save(
                target,
                format="JPEG",
                quality=90,
                optimize=False,
                progressive=False,
                subsampling=0,
            )

        # Verify that the generated JPEG can be decoded completely.
        with Image.open(target) as check:
            check.verify()

        # Re-open once more to make sure the file is actually readable.
        with Image.open(target) as check:
            check.load()

        out.append(target)

    return out


def reencode_jpeg(source: Path, target: Path):
    """
    Freshly decode and re-encode a JPEG.

    Used as a recovery path when Meta rejects an otherwise
    publicly accessible image.
    """

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with Image.open(source) as im:
        clean = im.convert("RGB")

        clean.save(
            target,
            format="JPEG",
            quality=90,
            optimize=False,
            progressive=False,
            subsampling=0,
        )

    with Image.open(target) as check:
        check.verify()

    with Image.open(target) as check:
        check.load()

    return target
 