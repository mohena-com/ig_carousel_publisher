from __future__ import annotations
import hashlib,time
from pathlib import Path
import requests
class CloudinaryUploader:
    def __init__(self,cloud_name,api_key,api_secret,folder): self.cloud_name=cloud_name; self.api_key=api_key; self.api_secret=api_secret; self.folder=folder
    def _signature(self,timestamp,public_id):
        params=f"folder={self.folder}&public_id={public_id}&timestamp={timestamp}"
        return hashlib.sha1((params+self.api_secret).encode()).hexdigest()
    def upload_jpeg(self,path:Path,public_id):
        ts=str(int(time.time())); sig=self._signature(ts,public_id)
        url=f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/upload"
        with path.open("rb") as fh:
            r=requests.post(url,files={"file":(path.name,fh,"image/jpeg")},data={"api_key":self.api_key,"timestamp":ts,"folder":self.folder,"public_id":public_id,"signature":sig},timeout=90)
        try: p=r.json()
        except Exception: p={"raw":r.text}
        if not r.ok: raise RuntimeError(f"Cloudinary upload failed: {r.status_code} {p}")
        if not p.get("secure_url"): raise RuntimeError(f"Cloudinary did not return secure_url: {p}")
        return p
