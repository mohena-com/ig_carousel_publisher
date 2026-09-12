from __future__ import annotations
import re
 
import time
from pathlib import Path

import requests


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

        url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{self.cloud_name}/image/upload"
        )

        with path.open("rb") as fh:
            response = requests.post(
                url,
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
            payload = {"raw": response.text}

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

        # The uploaded asset is already a normalized JPEG.
        # Meta accepts the plain Cloudinary delivery URL, but our
        # testing showed Meta rejects the versioned delivery URL.
        # Remove the Cloudinary version segment and do not apply
        # any further image transformation.
        meta_url = re.sub(
            r"/image/upload/v\d+/",
            "/image/upload/",
            secure_url,
            count=1,
        )
        payload["meta_secure_url"] = meta_url

        return payload
