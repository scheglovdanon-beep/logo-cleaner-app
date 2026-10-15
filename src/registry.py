# -*- coding: utf-8 -*-
"""Stage 2 — diagnostic module (TZ §4). READ-ONLY object registry + ID-labelled preview.
Each vector path from get_drawings() is one object. Never modifies the input."""
import os, json, pymupdf
from PIL import Image, ImageDraw

def _hex(c):
    if not c: return None
    return "#%02x%02x%02x" % tuple(int(round(v*255)) for v in c[:3])

def build_registry(pdf):
    d=pymupdf.open(pdf); pg=d[0]; W,H=pg.rect.width,pg.rect.height; pa=W*H
    ocgs=[i["name"] for i in d.get_ocgs().values()]
    dr=pg.get_drawings()
    objs=[]
    for i,r in enumerate(dr):
        b=r["rect"]; a=b.width*b.height
        large = a>0.02*pa                 # structure/garment/base -> protect
        objs.append({
            "id": f"obj_{i:04d}",
            "type": r.get("type"),                       # f=fill, s=stroke, fs=both
            "page": 0,
            "bbox": [round(b.x0,1),round(b.y0,1),round(b.x1,1),round(b.y1,1)],
            "w": round(b.width,1), "h": round(b.height,1),
            "area_frac": round(a/pa,5),
            "fill": _hex(r.get("fill")), "stroke": _hex(r.get("color")),
            "draw_order": r.get("seqno", i),
            "path_items": len(r.get("items",[])),
            "size_class": "large" if large else ("medium" if a>0.0008*pa else "small"),
            "removable_alone": (not large),              # large shapes not safely removable alone
            "layer": None,                               # not resolvable per-path (OCG=panels)
            "group": None,                               # Illustrator groups not preserved
        })
    meta={"source": os.path.basename(pdf), "page_pt":[round(W,1),round(H,1)],
          "object_count": len(objs), "ocg_layers": ocgs,
          "limitations": ["текст в кривых — семантического текста нет",
                          "группы Illustrator не сохранены как контейнеры",
                          "слой на путь не определяется (OCG=панели)",
                          "лого = набор отдельных путей, не один объект"]}
    d.close()
    return meta, objs

def diagnostic_preview(pdf, objs, out_png, label_cap=45):
    pg=pymupdf.open(pdf)[0]; W=pg.rect.width; z=min(900/W,1.4)
    pix=pg.get_pixmap(matrix=pymupdf.Matrix(z,z)); im=Image.frombytes("RGB",(pix.w,pix.h),pix.samples)
    dr=ImageDraw.Draw(im)
    # colour-code: large=blue(protected), medium=orange(candidate), small=red(detail)
    col={"large":(40,90,255),"medium":(255,120,0),"small":(230,40,40)}
    for o in objs:
        x0,y0,x1,y1=[v*z for v in o["bbox"]]
        dr.rectangle([x0,y0,x1,y1],outline=col[o["size_class"]],width=1)
    # label IDs for MEDIUM candidates (readable count)
    meds=[o for o in objs if o["size_class"]=="medium"][:label_cap]
    for o in meds:
        x0,y0=o["bbox"][0]*z,o["bbox"][1]*z
        dr.text((x0,y0-9),o["id"].replace("obj_",""),fill=(0,0,0))
    im.save(out_png)
    return len(meds)

if __name__=="__main__":
    import sys
    os.makedirs("logotool/reports",exist_ok=True); os.makedirs("logotool/previews",exist_ok=True)
    for pdf in sys.argv[1:]:
        meta,objs=build_registry(pdf)
        stem=os.path.splitext(os.path.basename(pdf))[0]
        json.dump({"meta":meta,"objects":objs}, open(f"logotool/reports/registry_{stem}.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
        n=diagnostic_preview(pdf,objs,f"logotool/previews/registry_{stem}.png")
        sc={}
        for o in objs: sc[o["size_class"]]=sc.get(o["size_class"],0)+1
        print(f"{stem}: {meta['object_count']} объектов  {sc}  | помечено ID: {n}  (ТОЛЬКО АНАЛИЗ, исходник не тронут)")
