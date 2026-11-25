# Copia i loghi dei canali di lista.m3u nel ramo «epg», pronti per l'app:
#  - margini trasparenti tolti (il logo riempie il riquadro), lato massimo 192 px, formato WebP (file piccoli)
#  - per ogni logo si decide il fondo: i loghi chiari su sfondo trasparente (es. il «5» bianco di Canale 5) vanno su fondo scuro
# Uso: python3 tools/logos.py lista.m3u out/   ->  out/logos/<nome>.webp  e  out/logos.json {url: [file, fondo_scuro]}
import io, json, re, sys, os, urllib.request, concurrent.futures as cf
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(out, "logos"), exist_ok=True)
urls = sorted(set(re.findall(r'tvg-logo="(https?://[^"]+)"', open(src, encoding="utf-8").read())))

def name_of(u):
    n = re.sub(r"^https?://", "", u, flags=re.I)
    n = re.sub(r"[?#].*$", "", n)
    return re.sub(r"[^A-Za-z0-9.]+", "_", n)[-120:]

def lum(p):
    return (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]) / 255

def prepare(data):
    im = Image.open(io.BytesIO(data)); im.load(); im = im.convert("RGBA")
    a = im.getchannel("A")
    transparent = a.getextrema()[0] < 128
    if transparent:
        box = a.point(lambda v: 255 if v >= 24 else 0).getbbox()
        if box:
            pad = max(2, int(max(box[2] - box[0], box[3] - box[1]) * 0.04))
            box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
            im = im.crop(box)
    im.thumbnail((192, 192), Image.LANCZOS)
    small = im.copy(); small.thumbnail((64, 64))
    px = list(small.getdata()); solid = [p for p in px if p[3] >= 128]
    transp = 1 - len(solid) / max(1, len(px))
    light = sum(1 for p in solid if lum(p) > 0.82) / max(1, len(solid))
    dark_bg = 1 if (transparent and transp > 0.15 and light > 0.5) else 0
    buf = io.BytesIO(); im.save(buf, "WEBP", quality=86, method=6)
    return buf.getvalue(), dark_bg

def get(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (TivuPlayer logos)"})
        data = urllib.request.urlopen(req, timeout=20).read()
        if len(data) > 3_000_000: return u, None, "troppo grande"
        return u, prepare(data), None
    except Exception as e:
        return u, None, str(e)[:80]

res, tot = {}, 0
with cf.ThreadPoolExecutor(8) as ex:
    for u, got, err in ex.map(get, urls):
        if not got: print("no ", u, err); continue
        webp, dark = got; n = name_of(u) + ".webp"
        open(os.path.join(out, "logos", n), "wb").write(webp); tot += len(webp)
        res[u] = [n, dark]
json.dump(res, open(os.path.join(out, "logos.json"), "w"), separators=(",", ":"))
print(len(res), "loghi su", len(urls), "·", tot // 1024, "KB in tutto ·", sum(v[1] for v in res.values()), "su fondo scuro")
