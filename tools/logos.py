# Copia i loghi dei canali di lista.m3u nel ramo «epg» e decide per ciascuno su che fondo mostrarlo.
# Uso: python3 tools/logos.py lista.m3u out/   (scrive out/logos/<nome> e out/logos.json)
import io, json, re, sys, os, urllib.request, concurrent.futures as cf
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(out, "logos"), exist_ok=True)
urls = sorted(set(re.findall(r'tvg-logo="(https?://[^"]+)"', open(src, encoding="utf-8").read())))

def name_of(u):
    n = re.sub(r"^https?://", "", u, flags=re.I)
    n = re.sub(r"[?#].*$", "", n)
    return re.sub(r"[^A-Za-z0-9.]+", "_", n)

def lum(r, g, b):
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

def analyse(im):
    im = im.convert("RGBA"); im.thumbnail((96, 96))
    w, h = im.size; px = list(im.getdata())
    solid = [p for p in px if p[3] >= 128]
    transp = 1 - len(solid) / max(1, len(px))
    border = [im.getpixel((x, y)) for x in range(w) for y in (0, h - 1)] + [im.getpixel((x, y)) for y in range(h) for x in (0, w - 1)]
    bsolid = [p for p in border if p[3] >= 128]
    bg = None
    if len(bsolid) > 0.8 * len(border):
        bg = tuple(sorted(c)[len(c) // 2] for c in zip(*[p[:3] for p in bsolid]))
    L = [lum(*p[:3]) for p in solid]
    light = sum(1 for x in L if x > 0.82) / max(1, len(L))
    fg = [p for p in solid if bg is None or sum(abs(p[i] - bg[i]) for i in range(3)) > 60]
    fgL = [lum(*p[:3]) for p in fg]
    return {"transp": round(transp, 2), "light": round(light, 2), "bg": bg, "bgL": round(lum(*bg), 2) if bg else None,
            "fgL": round(sum(fgL) / len(fgL), 2) if fgL else None, "fg": round(len(fg) / max(1, len(solid)), 2), "size": im.size}

def get(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (TivuPlayer logos)"})
        data = urllib.request.urlopen(req, timeout=20).read()
        if len(data) > 2_000_000: return u, None, "troppo grande"
        im = Image.open(io.BytesIO(data)); im.load()
        return u, (data, im), None
    except Exception as e:
        return u, None, str(e)[:80]

res = {}
with cf.ThreadPoolExecutor(8) as ex:
    for u, got, err in ex.map(get, urls):
        if not got: print("no ", u, err); continue
        data, im = got; n = name_of(u)
        open(os.path.join(out, "logos", n), "wb").write(data)
        a = analyse(im)
        res[u] = {"f": n, **a}
json.dump(res, open(os.path.join(out, "logos.json"), "w"), separators=(",", ":"))
print(len(res), "loghi copiati su", len(urls))
