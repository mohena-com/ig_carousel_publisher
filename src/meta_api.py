from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any
import requests
@dataclass
class InstagramAccount:
    page_id: str
    page_name: str
    page_access_token: str
    ig_user_id: str
class MetaAPI:
    def __init__(self, api_version):
        self.base=f"https://graph.facebook.com/{api_version}"
        self.session=requests.Session(); self.session.headers.update({"User-Agent":"instagram-carousel-publisher/1.0"})
    def _request(self,method,path,*,params=None,data=None):
        r=self.session.request(method,self.base+path,params=params,data=data,timeout=45)
        try: payload=r.json()
        except Exception: payload={"raw":r.text}
        if not r.ok: raise RuntimeError(f"Meta API error {r.status_code}: {payload}")
        return payload
    def discover_pages(self,user_access_token):
        p=self._request("GET","/me/accounts",params={"fields":"id,name,access_token,tasks,instagram_business_account","access_token":user_access_token})
        return p.get("data",[])
    def choose_account(self,user_access_token,page_name=None):
        pages=self.discover_pages(user_access_token)
        if not pages: raise RuntimeError("Meta returned no Pages for this User Access Token. Check Page access and required permissions.")
        candidates=pages
        if page_name:
            exact=[p for p in pages if (p.get("name") or "").strip().lower()==page_name.strip().lower()]
            if exact: candidates=exact
        for p in candidates:
            ig=p.get("instagram_business_account"); token=p.get("access_token")
            if ig and ig.get("id") and token:
                return InstagramAccount(p["id"],p.get("name",""),token,ig["id"])
        names=", ".join(str(p.get("name","")) for p in pages)
        raise RuntimeError("No selected Page has an instagram_business_account. Pages returned: "+names)
    def create_image_container(self,ig_user_id,page_access_token,image_url):
        p=self._request("POST",f"/{ig_user_id}/media",data={"image_url":image_url,"is_carousel_item":"true","access_token":page_access_token})
        if not p.get("id"): raise RuntimeError(f"Meta did not return child container ID: {p}")
        return p["id"]
    def create_carousel_container(self,ig_user_id,page_access_token,child_ids,caption):
        if not 2<=len(child_ids)<=10: raise ValueError("Instagram carousel requires between 2 and 10 child items.")
        p=self._request("POST",f"/{ig_user_id}/media",data={"media_type":"CAROUSEL","children":",".join(child_ids),"caption":caption,"access_token":page_access_token})
        if not p.get("id"): raise RuntimeError(f"Meta did not return carousel container ID: {p}")
        return p["id"]
    def container_status(self,container_id,page_access_token):
        return self._request("GET",f"/{container_id}",params={"fields":"status_code,status","access_token":page_access_token})
    def wait_until_ready(self,container_id,page_access_token,timeout_seconds=300,poll_seconds=10):
        deadline=time.time()+timeout_seconds; last=None
        while time.time()<deadline:
            last=self.container_status(container_id,page_access_token); code=str(last.get("status_code","")).upper()
            if code in {"FINISHED","PUBLISHED"}: return last
            if code=="ERROR": raise RuntimeError(f"Instagram container failed: {last}")
            time.sleep(poll_seconds)
        raise TimeoutError(f"Instagram container did not become ready within {timeout_seconds}s. Last status: {last}")
    def publish(self,ig_user_id,page_access_token,creation_id):
        p=self._request("POST",f"/{ig_user_id}/media_publish",data={"creation_id":creation_id,"access_token":page_access_token})
        if not p.get("id"): raise RuntimeError(f"Meta did not return published media ID: {p}")
        return p["id"]
