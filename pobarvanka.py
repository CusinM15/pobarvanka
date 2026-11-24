"""                                                                                                                
pobarvanka.py — pretvori fotografije/risbe v ČRNO-BELE POBARVANKE.                                                 
                                                                                                                
Rezultat je STROGO binaren: samo črna (0) in bela (255), brez sivih odtenkov.                                      
Skripta poskusi odstraniti tudi besedilo/napise/watermarke (majhne črke,                                           
ki ležijo v vodoravnih vrstah).                                                                                    
                                                                                                                
Uporaba:                                                                                                           
    python3 pobarvanka.py [VHODNA_MAPA] [IZHODNA_MAPA] [opcije]                                                    
                                                                                                                
Privzeto: VHODNA_MAPA=test_vhod, IZHODNA_MAPA=test_izhod                                                           
                                                                                                                
Primeri:                                                                                                           
    python3 pobarvanka.py                                                                                          
    python3 pobarvanka.py slike pobarvanke --blur 9 --offset 12 --thicken                                          
    python3 pobarvanka.py slike pobarvanke --keep-text          # obdrži napise                                    
    python3 pobarvanka.py slike pobarvanke --text-min-letters 3                                                    
                                                                                                                
Odvisnosti:                                                                                                        
    pip install Pillow numpy scipy                                                                                 
"""                                                                                                                
                                                                                                                
import argparse                                                                                                    
import os                                                                                                          
import sys                                                                                                         
                                                                                                                
import numpy as np                                                                                                 
from PIL import Image, ImageFilter, ImageOps                                                                       
                                                                                                                
try:                                                                                                               
    from scipy import ndimage as ndi                                                                               
except ImportError:  # scipy je potreben le za odstranjevanje besedila                                             
    ndi = None                                                                                                     
                                                                                                                
INPUT_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}                                           
                                                                                                                
def flatten_on_white(img: Image.Image) -> Image.Image:                                                             
    """Splošči prosojnost na belo ozadje (prosojnost -> bela, ne črna)."""                                         
    img = ImageOps.exif_transpose(img)                                                                             
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):                             
        img = img.convert("RGBA")                                                                                  
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))                                                     
        img = Image.alpha_composite(bg, img)                                                                       
    return img.convert("RGB")                                                                                      
                                                                                                                
def build_mask(gray: Image.Image, blur: float, offset: float, dark_threshold: int) -> np.ndarray:                  
    """Vrni bool masko: True = črna (črta), False = bela (ozadje)."""                                              
    g = np.asarray(gray, dtype=np.float32)                                                                         
    bg = np.asarray(gray.filter(ImageFilter.GaussianBlur(radius=blur)), dtype=np.float32)                          
                                                                                                                
    # črta tam, kjer je piksel bistveno temnejši od lokalnega povprečja                                            
    mask = (bg - g) > offset                                                                                       
    # zelo temne ploskve (zenice, lasje, polna črnina) ohrani                                                      
    mask |= g < dark_threshold                                                                                     
    return mask                                                                                                    
                                                                                                                
def _component_stats(mask: np.ndarray):                                                                            
    """Označi povezane komponente in vrni (labels, stats)."""                                                      
    lab, n = ndi.label(mask, structure=np.ones((3, 3), dtype=bool))                                                
    if n == 0:                                                                                                     
        return lab, []                                                                                             
    stats = []                                                                                                     
    for i, sl in enumerate(ndi.find_objects(lab)):                                                                 
        if sl is None:                                                                                             
            continue                                                                                               
        ys, xs = sl                                                                                                
        stats.append({                                                                                             
            "id": i + 1,                                                                                           
            "y0": int(ys.start), "y1": int(ys.stop),                                                               
            "x0": int(xs.start), "x1": int(xs.stop),                                                               
            "h": int(ys.stop - ys.start),                                                                          
            "w": int(xs.stop - xs.start),                                                                          
        })                                                                                                         
    return lab, stats                                                                                              
                                                                                                                
def _find_text_ids(stats, width: int, height: int,                                                                 
                max_h_frac: float, min_members: int) -> set:                                                    
    """Vrni ID-je komponent, ki izgledajo kot besedilo (vrstice malih črk)."""                                     
    max_h = max(5.0, max_h_frac * height)                                                                          
                                                                                                                
    # kandidati: majhne, a ne čisto drobne komponente                                                              
    cands = [s for s in stats                                                                                      
            if 3 <= s["h"] <= max_h and s["w"] <= 0.6 * width]                                                    
    if len(cands) < min_members:                                                                                   
        return set()                                                                                               
                                                                                                                
    med_h = float(np.median([s["h"] for s in cands]))                                                              
    # črke niso daljše od nekaj višin črke                                                                         
    cands = [s for s in cands if s["w"] <= max(4.0 * med_h, 24.0)]                                                 
    if len(cands) < min_members:                                                                                   
        return set()                                                                                               
                                                                                                                
    tol = max(2.0, 0.7 * med_h)        # ista vrstica besedila                                                     
    gap_max = max(4.0, 2.0 * med_h)    # največji razmik med sosednjima črkama                                     
                                                                                                                
    cands.sort(key=lambda s: ((s["y0"] + s["y1"]) / 2.0, s["x0"]))                                                 
                                                                                                                
    groups = []                                                                                                    
    for s in cands:                                                                                                
        cy = (s["y0"] + s["y1"]) / 2.0                                                                             
        placed = False                                                                                             
        for g in groups:                                                                                           
            gy = (g["y0"] + g["y1"]) / 2.0                                                                         
            if abs(cy - gy) > tol:                                                                                 
                continue                                                                                           
            gap = max(g["x0"] - s["x1"], s["x0"] - g["x1"])                                                        
            if gap > gap_max:                                                                                      
                continue                                                                                           
            g["items"].append(s)                                                                                   
            g["y0"] = min(g["y0"], s["y0"]); g["y1"] = max(g["y1"], s["y1"])                                       
            g["x0"] = min(g["x0"], s["x0"]); g["x1"] = max(g["x1"], s["x1"])                                       
            placed = True                                                                                          
            break                                                                                                  
        if not placed:                                                                                             
            groups.append({"y0": s["y0"], "y1": s["y1"],                                                           
                        "x0": s["x0"], "x1": s["x1"], "items": [s]})                                            
                                                                                                                
    ids = set()                                                                                                    
    for g in groups:                                                                                               
        items = g["items"]                                                                                         
        if len(items) < min_members:                                                                               
            continue                                                                                               
        hs = np.array([i["h"] for i in items], dtype=np.float32)                                                   
        # v besedilni vrstici so črke podobno visoke                                                               
        if hs.max() > 3.0 * max(1.0, hs.min()):                                                                    
            continue                                                                                               
        # vrstica mora biti dovolj široka (beseda, ne dve piki)                                                    
        if (g["x1"] - g["x0"]) < max(6.0 * med_h, 25.0):                                                           
            continue                                                                                               
        for i in items:                                                                                            
            ids.add(i["id"])                                                                                       
    return ids                                                                                                     
                                                                                                                
def remove_text(mask: np.ndarray, max_h_frac: float = 0.035,                                                       
                min_members: int = 4, pad: int = 1):                                                               
    """Odstrani besedilu podobne komponente iz maske. Vrni (nova_maska, št._odstranjenih)."""                      
    if ndi is None or not mask.any():                                                                              
        return mask, 0                                                                                             
    lab, stats = _component_stats(mask)                                                                            
    if not stats:                                                                                                  
        return mask, 0                                                                                             
                                                                                                                
    h, w = mask.shape                                                                                              
    ids = _find_text_ids(stats, w, h, max_h_frac, min_members)                                                     
    if not ids:                                                                                                    
        return mask, 0                                                                                             
                                                                                                                
    removal = np.isin(lab, np.fromiter(ids, dtype=np.int64))                                                       
    if pad > 0:                                                                                                    
        # razširi za 1-2 px, da pobrišeš tudi mehke robove črk                                                     
        removal = ndi.binary_dilation(removal, iterations=pad)                                                     
    return mask & ~removal, len(ids)                                                                               
                                                                                                                
def to_coloring_page(                                                                                                 
    img: Image.Image,                                                                                                 
    blur: float = 4.0,                                                                                                
    offset: float = 7.0,                                                                                              
    smooth: int = 3,                                                                                                  
    dark_threshold: int = 0,                                                                                          
    thicken: bool = False,                                                                                            
    max_size: int = 2000,                                                                                             
    strip_text: bool = True,                                                                                          
    text_max_height: float = 0.035,                                                                                   
    text_min_letters: int = 4,                                                                                        
    text_pad: int = 1,                                                                                                
):                                                                                                                   
    """Pretvori PIL sliko v strogo črno-belo pobarvanko. Vrni (slika, št._odstranjenih_besedil)."""                
    img = flatten_on_white(img)                                                                                    
                                                                                                                
    w, h = img.size                                                                                                
    if max(w, h) > max_size:                                                                                       
        scale = max_size / float(max(w, h))                                                                        
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)                          
                                                                                                                
    gray = img.convert("L")                                                                                        
    if smooth and smooth >= 3:                                                                                     
        gray = gray.filter(ImageFilter.MedianFilter(size=smooth))                                                  
                                                                                                                
    mask = build_mask(gray, blur, offset, dark_threshold)                                                          
                                                                                                                
    removed = 0                                                                                                    
    if strip_text:                                                                                                 
        mask, removed = remove_text(mask, text_max_height, text_min_letters, text_pad)                             
                                                                                                                
    page = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8), mode="L")                                      
                                                                                                                
    if thicken:                                                                                                    
        page = page.filter(ImageFilter.MaxFilter(size=3))                                                          
                                                                                                                
    # končna normalizacija: zagotovo samo 0 ali 255 (nikoli sivine)                                                
    arr = np.asarray(page)                                                                                         
    page = Image.fromarray(np.where(arr > 127, 255, 0).astype(np.uint8), mode="L")                                 
                                                                                                                
    return page, removed                                                                                           
                                                                                                                
def find_images(folder: str, recursive: bool):                                                                     
    found = []                                                                                                     
    if recursive:                                                                                                  
        for root, _dirs, files in os.walk(folder):                                                                 
            for name in files:                                                                                     
                if os.path.splitext(name)[1].lower() in INPUT_EXTS:                                                
                    found.append(os.path.join(root, name))                                                         
    else:                                                                                                          
        for name in sorted(os.listdir(folder)):                                                                    
            path = os.path.join(folder, name)                                                                      
            if os.path.isfile(path) and os.path.splitext(name)[1].lower() in INPUT_EXTS:                           
                found.append(path)                                                                                 
    return sorted(found)                                                                                           
                                                                                                                
def main(argv=None):                                                                                               
    p = argparse.ArgumentParser(                                                                                   
        description="Pretvori slike v strogo črno-bele pobarvanke in odstrani besedilo."                           
    )                                                                                                              
    p.add_argument("input_dir", nargs="?", default="test_vhod",                                                    
                help="mapa z vhodnimi slikami; privzeto test_vhod")                                             
    p.add_argument("output_dir", nargs="?", default="test_izhod",                                                  
                help="mapa za shranjevanje pobarvank; privzeto test_izhod")                                     
    p.add_argument("--blur", type=float, default=4.0,                                                              
                help="radij zameglitve ozadja; večji = debelejše/manj črt (privzeto 4)")                       
    p.add_argument("--offset", type=float, default=7.0,                                                          
                help="občutljivost pragu; manjši = več črt/detajlov (privzeto 7)")                            
    p.add_argument("--smooth", type=int, default=3,                                                                
                help="median filter za šum (privzeto 3, 0 = izklop)")                                           
    p.add_argument("--dark-threshold", type=int, default=0,                                                       
                help="prag za ohranitev zelo temnih ploskev; 0 = izklop (privzeto 0, tanke črte)")              
    p.add_argument("--thicken", action="store_true",                                                               
                help="odebeli črte (bolj izrazita pobarvanka)")                                                 
    p.add_argument("--max-size", type=int, default=2000,                                                           
                help="največja dolžina stranice pred obdelavo (privzeto 2000)")                                 
    p.add_argument("--fmt", choices=["png", "jpg"], default="png",                                                 
                help="format izhoda (privzeto png; PNG edini ohrani strogo črno-belo)")                         
    p.add_argument("--recursive", action="store_true", help="preglej tudi podmape")                                
    p.add_argument("--overwrite", action="store_true",                                                             
                help="prepiši obstoječe izhodne datoteke")                                                      
    # --- odstranjevanje besedila ---                                                                              
    p.add_argument("--keep-text", action="store_true",                                                             
                help="NE odstranjuj besedila/napisov")                                                          
    p.add_argument("--text-max-height", type=float, default=0.035,                                                 
                help="največja višina črke kot delež višine slike (privzeto 0.035 = 3,5%%)")                    
    p.add_argument("--text-min-letters", type=int, default=4,                                                      
                help="najmanj znakov v vrstici, da velja za besedilo (privzeto 4)")                             
    p.add_argument("--text-pad", type=int, default=1,                                                              
                help="razširitev brisanja okoli črk v pikslih (privzeto 1)")                                    
    args = p.parse_args(argv)                                                                                      
                                                                                                                
    if not os.path.isdir(args.input_dir):                                                                          
        print(f"NAPAKA: vhodna mapa ne obstaja: {args.input_dir}", file=sys.stderr)                                
        return 1                                                                                                   
                                                                                                                
    if args.keep_text is False and ndi is None:                                                                    
        print("OPOZORILO: scipy ni nameščen -> besedilo ne bo odstranjeno.\n"                                      
            "Namesti: pip install scipy", file=sys.stderr)                                                       
                                                                                                                
    os.makedirs(args.output_dir, exist_ok=True)                                                                    
    images = find_images(args.input_dir, args.recursive)                                                           
    if not images:                                                                                                 
        print(f"V vhodni mapi ni slik ({', '.join(sorted(INPUT_EXTS))}).")                                         
        return 0                                                                                                   
                                                                                                                
    ext = "." + args.fmt                                                                                           
    ok = skip = err = 0                                                                                            
    for path in images:                                                                                            
        name = os.path.splitext(os.path.basename(path))[0] + ext                                                   
        if args.recursive:                                                                                         
            rel = os.path.relpath(os.path.dirname(path), args.input_dir)                                           
            out_dir = args.output_dir if rel == "." else os.path.join(args.output_dir, rel)                        
            os.makedirs(out_dir, exist_ok=True)                                                                    
            out_path = os.path.join(out_dir, name)                                                                 
        else:                                                                                                      
            out_path = os.path.join(args.output_dir, name)                                                         
                                                                                                                
        if os.path.exists(out_path) and not args.overwrite:                                                        
            print(f"preskočeno (obstaja): {out_path}")                                                             
            skip += 1                                                                                              
            continue                                                                                               
                                                                                                                
        try:                                                                                                       
            with Image.open(path) as im:                                                                           
                page, removed = to_coloring_page(                                                                  
                    im,                                                                                            
                    blur=args.blur,                                                                                
                    offset=args.offset,                                                                            
                    smooth=args.smooth,                                                                            
                    dark_threshold=args.dark_threshold,                                                            
                    thicken=args.thicken,                                                                          
                    max_size=args.max_size,                                                                        
                    strip_text=not args.keep_text,                                                                 
                    text_max_height=args.text_max_height,                                                          
                    text_min_letters=args.text_min_letters,                                                        
                    text_pad=args.text_pad,                                                                        
                )                                                                                                  
            if args.fmt == "jpg":                                                                                  
                page.save(out_path, quality=95, subsampling=0)                                                     
                print("OPOZORILO: JPG vedno doda sivino/artefakte; za strogo "                                     
                    "črno-belo uporabi --fmt png", file=sys.stderr)                                              
            else:                                                                                                  
                page.save(out_path, format="PNG", optimize=True)                                                   
                                                                                                                
            uniq = np.unique(np.asarray(page))                                                                     
            strict = len(uniq) <= 2 and set(uniq.tolist()) <= {0, 255}                                             
            print(f"OK  {path} -> {out_path}  (odstranjenih besedilnih elementov: {removed}, "                     
                f"strogo črno-belo: {'da' if strict else 'NE'})")                                                
            ok += 1                                                                                                
        except Exception as e:  # noqa: BLE001                                                                     
            print(f"NAPAKA pri {path}: {e}", file=sys.stderr)                                                      
            err += 1                                                                                               
                                                                                                                
    print(f"\nKončano: {ok} ustvarjenih, {skip} preskočenih, {err} napak.")                                        
    print(f"Izhodna mapa: {os.path.abspath(args.output_dir)}")                                                     
    return 0 if err == 0 else 2                                                                                    
                                                                                                                
if __name__ == "__main__":                                                                                                 
    raise SystemExit(main()) 
