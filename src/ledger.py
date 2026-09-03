import hashlib,json
from pathlib import Path
class PublicationLedger:
    def __init__(self,path:Path): self.path=path; self.path.parent.mkdir(parents=True,exist_ok=True)
    def _load(self): return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
    def fingerprint(self,slides,caption):
        h=hashlib.sha256()
        for p in slides: h.update(p.name.encode()); h.update(p.read_bytes())
        h.update(caption.encode()); return h.hexdigest()
    def already_published(self,fingerprint): return self._load().get(fingerprint)
    def record(self,fingerprint,payload):
        d=self._load(); d[fingerprint]=payload; self.path.write_text(json.dumps(d,indent=2),encoding="utf-8")
