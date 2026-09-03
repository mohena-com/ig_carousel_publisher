from pathlib import Path
from PIL import Image
def find_six_slides(input_dir:Path):
    if not input_dir.exists(): raise FileNotFoundError(f"Input directory not found: {input_dir}")
    slides=[input_dir/f"slide_{i}.png" for i in range(1,7)]
    missing=[str(p) for p in slides if not p.is_file()]
    if missing: raise RuntimeError("Exactly six PNG slides are required. Missing: "+", ".join(missing))
    return slides
def convert_to_jpegs(slides,work_dir:Path):
    work_dir.mkdir(parents=True,exist_ok=True); out=[]
    for i,source in enumerate(slides,1):
        target=work_dir/f"slide_{i}.jpg"
        with Image.open(source) as im:
            im=im.convert("RGB"); im.save(target,format="JPEG",quality=95,optimize=True)
        with Image.open(target) as check: check.verify()
        out.append(target)
    return out
