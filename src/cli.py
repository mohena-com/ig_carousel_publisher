import argparse
import json
from pathlib import Path
from .config import Config
from .publisher import Publisher

def build_parser():
    p = argparse.ArgumentParser(description="Publish six generated job slides as one Instagram carousel.")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="Discover the connected Page and Instagram account.")
    d.add_argument("--json", action="store_true")
    q = sub.add_parser("publish", help="Validate, dry-run, or publish a six-slide carousel.")
    q.add_argument("--input-dir", required=True, type=Path)
    q.add_argument("--caption", default="")
    m = q.add_mutually_exclusive_group()
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--publish", action="store_true")
    return p

def main():
    a = build_parser().parse_args()
    c = Config()
    pub = Publisher(c)
    if a.command == "doctor":
        acc = pub.discover()
        result = {
            "page_name": acc.page_name,
            "page_id": acc.page_id,
            "instagram_user_id": acc.ig_user_id,
            "page_access_token": "***hidden***",
            "meta_api_version": c.meta_api_version,
        }
        c.data_dir.mkdir(parents=True, exist_ok=True)
        (c.data_dir / "account.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return
    caption = a.caption.strip()
    if c.default_hashtags and c.default_hashtags not in caption:
        caption = (caption + "\n\n" + c.default_hashtags).strip()
    if not a.publish:
        a.dry_run = True
    if a.dry_run:
        print(json.dumps(pub.dry_run(a.input_dir.resolve(), caption), indent=2))
        print("\nDRY RUN ONLY — nothing was published.")
        return
    print(json.dumps(pub.publish(a.input_dir.resolve(), caption), indent=2))
    print("\nSUCCESS — one Instagram carousel post was published.")

if __name__ == "__main__":
    main()
