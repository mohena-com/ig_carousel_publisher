from __future__ import annotations

import hashlib
import re
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image


class CloudinaryUploader:
    def __init__(
        self,
        cloud_name,
        api_key,
        api_secret,
        folder,
    ):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.folder = folder

    def _signature(self, timestamp, public_id):
        params = (
            f"folder={self.folder}"
            f"&public_id={public_id}"
            f"&timestamp={timestamp}"
        )

        return hashlib.sha1(
            (params + self.api_secret).encode()
        ).hexdigest()

    def _wait_until_ready(
        self,
        url,
        timeout=15,
        interval=1,
    ):
        """
        Wait until the Cloudinary delivery URL is reachable
        and returns a valid JPEG that Pillow can decode.
        """
        deadline = time.time() + timeout
        last_error = None

        while time.time() < deadline:
            try:
                response = requests.get(
                    url,
                    timeout=10,
                )

                content_type = (
                    response.headers.get(
                        "content-type",
                        "",
                    )
                    .split(";")[0]
                    .strip()
                    .lower()
                )

                if response.status_code == 200:
                    if content_type == "image/jpeg":
                        with Image.open(
                            BytesIO(response.content)
                        ) as image:
                            image.verify()

                        return

                    last_error = (
                        f"HTTP 200 but unexpected "
                        f"Content-Type: {content_type}"
                    )
                else:
                    last_error = (
                        f"HTTP {response.status_code}"
                    )

            except Exception as exc:
                last_error = str(exc)

            time.sleep(interval)

        raise RuntimeError(
            "Cloudinary asset was not ready for Meta "
            f"after {timeout} seconds: {url}. "
            f"Last error: {last_error}"
        )

    def upload_jpeg(
        self,
        path: Path,
        public_id,
    ):
        timestamp = str(int(time.time()))

        signature = self._signature(
            timestamp,
            public_id,
        )

        upload_url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{self.cloud_name}/image/upload"
        )

        with path.open("rb") as fh:
            response = requests.post(
                upload_url,
                files={
                    "file": (
                        path.name,
                        fh,
                        "image/jpeg",
                    )
                },
                data={
                    "api_key": self.api_key,
                    "timestamp": timestamp,
                    "folder": self.folder,
                    "public_id": public_id,
                    "signature": signature,
                },
                timeout=90,
            )

        try:
            payload = response.json()
        except Exception:
            payload = {
                "raw": response.text
            }

        if not response.ok:
            raise RuntimeError(
                "Cloudinary upload failed: "
                f"{response.status_code} {payload}"
            )

        secure_url = payload.get("secure_url")

        if not secure_url:
            raise RuntimeError(
                "Cloudinary did not return secure_url: "
                f"{payload}"
            )

        # Meta requires Cloudinary to deliver the asset
        # through an explicit JPEG transformation.
        #
        # IMPORTANT:
        # Keep the Cloudinary version segment.
        #
        # Example:
        # /image/upload/v123456789/...
        #
        # becomes:
        # /image/upload/q_auto,f_jpg/v123456789/...
        meta_url = re.sub(
            r"/image/upload/",
            "/image/upload/q_auto,f_jpg/",
            secure_url,
            count=1,
        )

        # Make sure Cloudinary's delivery edge is actually
        # returning a valid JPEG before asking Meta to fetch it.
        self._wait_until_ready(meta_url)

        payload["meta_secure_url"] = meta_url

        return payload