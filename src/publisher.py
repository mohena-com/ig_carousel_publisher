from datetime import datetime, timezone
from pathlib import Path
import time
import uuid
import hashlib

from .config import Config
from .images import (
    find_six_slides,
    convert_to_jpegs,
    reencode_jpeg,
)
from .meta_api import MetaAPI
from .cloudinary import CloudinaryUploader
from .ledger import PublicationLedger


class Publisher:
    def __init__(self, config: Config):
        self.config = config
        self.meta = MetaAPI(config.meta_api_version)
        self.ledger = PublicationLedger(
            config.data_dir / "publications.json"
        )

    def discover(self):
        self.config.validate_meta()

        return self.meta.choose_account(
            self.config.meta_user_access_token,
            self.config.meta_page_name,
            self.config.meta_page_id,
        )

    def validate(self, input_dir, caption):
        slides = find_six_slides(input_dir)

        self.config.validate_meta()
        self.config.validate_cloudinary()

        account = self.discover()

        fingerprint = self.ledger.fingerprint(
            slides,
            caption,
        )

        duplicate = self.ledger.already_published(
            fingerprint
        )

        return (
            slides,
            account,
            fingerprint,
            duplicate,
        )

    def dry_run(self, input_dir, caption):
        (
            slides,
            account,
            fingerprint,
            duplicate,
        ) = self.validate(
            input_dir,
            caption,
        )

        jpegs = convert_to_jpegs(
            slides,
            self.config.data_dir
            / "tmp"
            / input_dir.name,
        )

        return {
            "input_dir": str(input_dir),
            "slides": [str(x) for x in slides],
            "jpegs": [str(x) for x in jpegs],
            "page_name": account.page_name,
            "page_id": account.page_id,
            "ig_user_id": account.ig_user_id,
            "fingerprint": fingerprint,
            "already_published": duplicate,
            "caption": caption,
        }

    def _is_meta_media_fetch_error(self, exc):
        message = str(exc)

        return (
            "9004" in message
            or "2207052" in message
            or "Media download has failed" in message
        )

    def _upload(
        self,
        uploader,
        jpeg,
        input_dir,
        slide_number,
        recovery=False,
    ):
        seed = f"{input_dir.name}|slide_{slide_number}"

        short_hash = hashlib.sha256(
            seed.encode("utf-8")
        ).hexdigest()[:12]

        if recovery:
            public_id = (
                f"ig_{short_hash}_s{slide_number}_recovery_"
                f"{uuid.uuid4().hex[:8]}"
            )
        else:
            public_id = (
                f"ig_{short_hash}_s{slide_number}"
            )

        result = uploader.upload_jpeg(
            jpeg,
            public_id,
        )

        return result["meta_secure_url"] 

    def _create_child_with_retry(
        self,
        account,
        uploader,
        jpeg,
        input_dir,
        slide_number,
    ):
        print(
            f"Creating Instagram child container "
            f"{slide_number}/6..."
        )

        url = self._upload(
            uploader,
            jpeg,
            input_dir,
            slide_number,
        )

        try:
            return self.meta.create_image_container(
                account.ig_user_id,
                account.page_access_token,
                url,
            )

        except RuntimeError as exc:
            if not self._is_meta_media_fetch_error(exc):
                raise

            print(
                f"Meta rejected slide {slide_number}. "
                "Creating a fully normalized recovery JPEG and retrying once..."
            )

            recovery_dir = (
                self.config.data_dir
                / "tmp"
                / "_recovery"
            )

            recovery_path = (
                recovery_dir
                / (
                    f"{input_dir.name}_"
                    f"slide_{slide_number}_"
                    f"{uuid.uuid4().hex[:8]}.jpg"
                )
            )

            try:
                fresh_jpeg = reencode_jpeg(
                    jpeg,
                    recovery_path,
                )

                recovery_url = self._upload(
                    uploader,
                    fresh_jpeg,
                    input_dir,
                    slide_number,
                    recovery=True,
                )

                print(
                    f"Retrying Instagram child "
                    f"container {slide_number}/6..."
                )

                return self.meta.create_image_container(
                    account.ig_user_id,
                    account.page_access_token,
                    recovery_url,
                )

            finally:
                try:
                    recovery_path.unlink(
                        missing_ok=True
                    )
                except Exception:
                    pass

    def publish(self, input_dir, caption):
        (
            slides,
            account,
            fingerprint,
            duplicate,
        ) = self.validate(
            input_dir,
            caption,
        )

        if duplicate:
            raise RuntimeError(
                "This exact six-slide set + caption was "
                "already published. Existing publication: "
                + str(duplicate)
            )

        work_dir = (
            self.config.data_dir
            / "tmp"
            / input_dir.name
        )

        # Normalize every source image before uploading.
        jpegs = convert_to_jpegs(
            slides,
            work_dir,
        )

        uploader = CloudinaryUploader(
            self.config.cloudinary_cloud_name,
            self.config.cloudinary_api_key,
            self.config.cloudinary_api_secret,
            self.config.cloudinary_folder,
        )

        child = []

        try:
            # SAFETY GATE / PREFLIGHT:
            # Each child container is Meta's media-fetch validation.
            # Create ALL six child containers first; only create the
            # carousel after every image has been accepted by Meta.
            for i, jpeg in enumerate(jpegs, 1):
                print(f"Preflight/uploading slide {i}/6...")
                child_id = self._create_child_with_retry(
                    account,
                    uploader,
                    jpeg,
                    input_dir,
                    i,
                )

                child.append(child_id)

            if len(child) != 6:
                raise RuntimeError(
                    "Safety check failed: expected 6 Instagram "
                    f"child containers, got {len(child)}."
                )

            print(
                "All 6 Instagram child containers created "
                "successfully."
            )

            print(
                "Creating CAROUSEL container..."
            )

            carousel = (
                self.meta.create_carousel_container(
                    account.ig_user_id,
                    account.page_access_token,
                    child,
                    caption,
                )
            )

            print(
                "Waiting for carousel readiness..."
            )

            status = self.meta.wait_until_ready(
                carousel,
                account.page_access_token,
            )

            print(
                "Publishing ONE Instagram post..."
            )

            media = self.meta.publish(
                account.ig_user_id,
                account.page_access_token,
                carousel,
            )

            # Record only after Meta confirms publication.
            self.ledger.record(
                fingerprint,
                {
                    "published_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "input_dir": str(input_dir),
                    "page_name": account.page_name,
                    "page_id": account.page_id,
                    "ig_user_id": account.ig_user_id,
                    "carousel_container_id": carousel,
                    "child_container_ids": child,
                    "instagram_media_id": media,
                    "caption": caption,
                },
            )

            return {
                "instagram_media_id": media,
                "carousel_container_id": carousel,
                "child_container_ids": child,
                "status": status,
            }

        except Exception as exc:
            # Do NOT write a successful ledger entry.
            # Preserve enough information for diagnosis.
            failure_dir = (
                self.config.data_dir
                / "failures"
            )

            failure_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            failure_file = (
                failure_dir
                / (
                    f"{input_dir.name}_"
                    f"{int(time.time())}.txt"
                )
            )

            failure_file.write_text(
                "\n".join(
                    [
                        "Instagram carousel publication failed.",
                        f"Time UTC: {datetime.now(timezone.utc).isoformat()}",
                        f"Input directory: {input_dir}",
                        f"Fingerprint: {fingerprint}",
                        f"Instagram user ID: {account.ig_user_id}",
                        f"Child containers created: {child}",
                        f"Error: {exc}",
                    ]
                ),
                encoding="utf-8",
            )

            print()
            print(
                "PUBLICATION FAILED — no successful "
                "publication was recorded."
            )
            print(
                f"Failure details: {failure_file}"
            )

            raise