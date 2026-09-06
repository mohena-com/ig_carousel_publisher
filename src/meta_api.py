from __future__ import annotations

import time
from dataclasses import dataclass
import requests


@dataclass
class InstagramAccount:
    page_id: str
    page_name: str
    page_access_token: str
    ig_user_id: str


class MetaAPI:
    def __init__(self, api_version):
        self.base = f"https://graph.facebook.com/{api_version}"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "instagram-carousel-publisher/1.0"
        })

    def _request(self, method, path, *, params=None, data=None):
        r = self.session.request(
            method,
            self.base + path,
            params=params,
            data=data,
            timeout=45,
        )

        try:
            payload = r.json()
        except Exception:
            payload = {"raw": r.text}

        if not r.ok:
            raise RuntimeError(
                f"Meta API error {r.status_code}: {payload}"
            )

        return payload

    def discover_page(self, user_access_token, page_id):
        """
        Retrieve the configured Facebook Page directly.

        We intentionally do not use /me/accounts because the
        current Meta setup is able to access the Page directly
        while /me/accounts returns an empty list.
        """

        fields = (
            "id,name,access_token,"
            "tasks,instagram_business_account"
        )

        return self._request(
            "GET",
            f"/{page_id}",
            params={
                "fields": fields,
                "access_token": user_access_token,
            },
        )

    def choose_account(
        self,
        user_access_token,
        page_name=None,
        page_id=None,
    ):
        if not page_id:
            raise RuntimeError(
                "META_PAGE_ID is required for direct Page discovery."
            )

        page = self.discover_page(
            user_access_token,
            page_id,
        )

        if not page.get("id"):
            raise RuntimeError(
                f"Meta did not return a Page ID: {page}"
            )

        actual_page_name = page.get("name", "")

        if page_name:
            if actual_page_name.strip().lower() != page_name.strip().lower():
                raise RuntimeError(
                    "Configured META_PAGE_NAME does not match the "
                    f"Meta Page. Expected '{page_name}', got "
                    f"'{actual_page_name}'."
                )

        page_access_token = page.get("access_token")
        if not page_access_token:
            raise RuntimeError(
                "Meta did not return a Page access token. "
                "Check the User Access Token and Page permissions."
            )

        ig = page.get("instagram_business_account")

        if not ig or not ig.get("id"):
            raise RuntimeError(
                "The Facebook Page does not have an "
                "instagram_business_account connected to it."
            )

        return InstagramAccount(
            page_id=page["id"],
            page_name=actual_page_name,
            page_access_token=page_access_token,
            ig_user_id=ig["id"],
        )

    def create_image_container(
        self,
        ig_user_id,
        page_access_token,
        image_url,
    ):
        p = self._request(
            "POST",
            f"/{ig_user_id}/media",
            data={
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": page_access_token,
            },
        )

        if not p.get("id"):
            raise RuntimeError(
                f"Meta did not return child container ID: {p}"
            )

        return p["id"]

    def create_carousel_container(
        self,
        ig_user_id,
        page_access_token,
        child_ids,
        caption,
    ):
        if not 2 <= len(child_ids) <= 10:
            raise ValueError(
                "Instagram carousel requires between 2 and 10 child items."
            )

        p = self._request(
            "POST",
            f"/{ig_user_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": page_access_token,
            },
        )

        if not p.get("id"):
            raise RuntimeError(
                f"Meta did not return carousel container ID: {p}"
            )

        return p["id"]

    def container_status(
        self,
        container_id,
        page_access_token,
    ):
        return self._request(
            "GET",
            f"/{container_id}",
            params={
                "fields": "status_code,status",
                "access_token": page_access_token,
            },
        )

    def wait_until_ready(
        self,
        container_id,
        page_access_token,
        timeout_seconds=300,
        poll_seconds=10,
    ):
        deadline = time.time() + timeout_seconds
        last = None

        while time.time() < deadline:
            last = self.container_status(
                container_id,
                page_access_token,
            )

            code = str(
                last.get("status_code", "")
            ).upper()

            if code in {"FINISHED", "PUBLISHED"}:
                return last

            if code == "ERROR":
                raise RuntimeError(
                    f"Instagram container failed: {last}"
                )

            time.sleep(poll_seconds)

        raise TimeoutError(
            "Instagram container did not become ready within "
            f"{timeout_seconds}s. Last status: {last}"
        )

    def publish(
        self,
        ig_user_id,
        page_access_token,
        creation_id,
    ):
        p = self._request(
            "POST",
            f"/{ig_user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": page_access_token,
            },
        )

        if not p.get("id"):
            raise RuntimeError(
                f"Meta did not return published media ID: {p}"
            )

        return p["id"]