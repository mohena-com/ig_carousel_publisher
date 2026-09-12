from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
@dataclass(frozen=True)
class Config:
    meta_api_version: str = os.getenv("META_API_VERSION", "26.0")
    meta_user_access_token: str = os.getenv("META_USER_ACCESS_TOKEN", "")
    meta_page_id: str = os.getenv("META_PAGE_ID", "1283817824820147")
    meta_page_name: str = os.getenv("META_PAGE_NAME", "Shaktidootam")
    cloudinary_cloud_name: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key: str = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret: str = os.getenv("CLOUDINARY_API_SECRET", "")
    cloudinary_folder: str = os.getenv("CLOUDINARY_FOLDER", "shaktidootam/instagram_jobs")
    default_hashtags: str = os.getenv("DEFAULT_HASHTAGS", "#governmentjobs #sarkarijob #jobalert #indiajobs")
    data_dir: Path = ROOT / "data"
    @property
    def graph_base(self): return f"https://graph.facebook.com/{self.meta_api_version}"
    
    def validate_cloudinary(self):
        missing=[n for n,v in [("CLOUDINARY_CLOUD_NAME",self.cloudinary_cloud_name),("CLOUDINARY_API_KEY",self.cloudinary_api_key),("CLOUDINARY_API_SECRET",self.cloudinary_api_secret)] if not v]
        if missing: raise RuntimeError("Missing Cloudinary settings in .env: "+", ".join(missing))
        
    
    def validate_meta(self):
        missing = []

        if not self.meta_user_access_token:
            missing.append("META_USER_ACCESS_TOKEN")

        if not self.meta_page_id:
            missing.append("META_PAGE_ID")

        if missing:
            raise RuntimeError("Missing Meta settings in .env: " + ", ".join(missing))