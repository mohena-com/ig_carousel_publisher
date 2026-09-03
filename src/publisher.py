from datetime import datetime,timezone
from .config import Config
from .images import find_six_slides,convert_to_jpegs
from .meta_api import MetaAPI
from .cloudinary import CloudinaryUploader
from .ledger import PublicationLedger
class Publisher:
    def __init__(self,config:Config): self.config=config; self.meta=MetaAPI(config.meta_api_version); self.ledger=PublicationLedger(config.data_dir/"publications.json")
    def discover(self):
        self.config.validate_meta(); return self.meta.choose_account(self.config.meta_user_access_token,self.config.meta_page_name)
    def validate(self,input_dir,caption):
        slides=find_six_slides(input_dir); self.config.validate_meta(); self.config.validate_cloudinary(); account=self.discover(); fp=self.ledger.fingerprint(slides,caption); return slides,account,fp,self.ledger.already_published(fp)
    def dry_run(self,input_dir,caption):
        slides,account,fp,dup=self.validate(input_dir,caption); jpegs=convert_to_jpegs(slides,self.config.data_dir/"tmp"/input_dir.name)
        return {"input_dir":str(input_dir),"slides":[str(x) for x in slides],"jpegs":[str(x) for x in jpegs],"page_name":account.page_name,"page_id":account.page_id,"ig_user_id":account.ig_user_id,"fingerprint":fp,"already_published":dup,"caption":caption}
    def publish(self,input_dir,caption):
        slides,account,fp,dup=self.validate(input_dir,caption)
        if dup: raise RuntimeError("This exact six-slide set + caption was already published. Existing publication: "+str(dup))
        jpegs=convert_to_jpegs(slides,self.config.data_dir/"tmp"/input_dir.name)
        up=CloudinaryUploader(self.config.cloudinary_cloud_name,self.config.cloudinary_api_key,self.config.cloudinary_api_secret,self.config.cloudinary_folder)
        urls=[]
        for i,jpeg in enumerate(jpegs,1): print(f"Uploading slide {i}/6..."); urls.append(up.upload_jpeg(jpeg,f"{input_dir.name}/slide_{i}")["secure_url"])
        child=[]
        for i,url in enumerate(urls,1): print(f"Creating Instagram child container {i}/6..."); child.append(self.meta.create_image_container(account.ig_user_id,account.page_access_token,url))
        print("Creating CAROUSEL container..."); carousel=self.meta.create_carousel_container(account.ig_user_id,account.page_access_token,child,caption)
        print("Waiting for carousel readiness..."); status=self.meta.wait_until_ready(carousel,account.page_access_token)
        print("Publishing ONE Instagram post..."); media=self.meta.publish(account.ig_user_id,account.page_access_token,carousel)
        self.ledger.record(fp,{"published_at_utc":datetime.now(timezone.utc).isoformat(),"input_dir":str(input_dir),"page_name":account.page_name,"page_id":account.page_id,"ig_user_id":account.ig_user_id,"carousel_container_id":carousel,"child_container_ids":child,"instagram_media_id":media,"caption":caption})
        return {"instagram_media_id":media,"carousel_container_id":carousel,"child_container_ids":child,"status":status}
