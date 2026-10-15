# -*- coding: utf-8 -*-
"""Stage 3 — logo detector (TZ §5). READ-ONLY.
Localises logo candidate regions (visual/geometric, since structure doesn't isolate logos),
MAPS each region to its constituent PDF path-objects (from the registry), scores confidence,
and decides: auto / review / skip. Threshold configurable."""
import os, json, math, pymupdf

def _load_cfg():
    return json.load(open("logotool/config/detection.json"))

def _glyph_lines(rects, W, H, pa, cfg, y0f, y1f):
    """rects: list of fitz.Rect (left panel). Return text lines (runs of >=N similar glyphs)."""
    cx=sum((b.x0+b.x1)/2 for b in rects)/len(rects)
    fy0=min(b.y0 for b in rects); fy1=max(b.y1 for b in rects); fh=fy1-fy0
    fw=max(b.x1 for b in rects)-min(b.x0 for b in rects)
    g=[b for b in rects if 8<b.width*b.height<0.0022*pa and 3<b.height<0.05*H and 2<b.width<0.055*W
       and fy0+y0f*fh<(b.y0+b.y1)/2<fy0+y1f*fh and abs((b.x0+b.x1)/2-cx)<cfg["central_column_frac"]*fw]
    g.sort(key=lambda b:((b.y0+b.y1)/2,b.x0)); used=[False]*len(g); lines=[]
    for i in range(len(g)):
        if used[i]: continue
        hc=(g[i].y0+g[i].y1)/2; hh=g[i].height
        band=[j for j in range(len(g)) if not used[j] and abs((g[j].y0+g[j].y1)/2-hc)<0.55*hh and abs(g[j].height-hh)<0.6*hh]
        band.sort(key=lambda j:g[j].x0); run=[band[0]]
        for j in band[1:]:
            if g[j].x0-g[run[-1]].x1<1.8*hh: run.append(j)
            else:
                if len(run)>=cfg["min_glyphs_per_line"]: lines.append([g[j2] for j2 in run])
                run=[j]
        if len(run)>=cfg["min_glyphs_per_line"]: lines.append([g[j2] for j2 in run])
        for j in band: used[j]=True
    return lines

def detect(pdf, registry_objs=None):
    cfg=_load_cfg()
    d=pymupdf.open(pdf); pg=d[0]; W,H=pg.rect.width,pg.rect.height; pa=W*H
    dr=pg.get_drawings()
    objs=registry_objs
    if objs is None:
        from registry import build_registry
        _,objs=build_registry(pdf)
    rects=[r["rect"] for r in dr if (r["rect"].x0+r["rect"].x1)/2<W/2]   # LEFT panel
    cands=[]
    # candidate regions from text-lines in the torso zone
    tz=cfg["zones"]["torso"]
    lines=_glyph_lines(rects,W,H,pa,cfg,tz[0],tz[1])
    if lines:
        allg=[b for ln in lines for b in ln]
        x0=min(b.x0 for b in allg)-6; y0=min(b.y0 for b in allg)-6
        x1=max(b.x1 for b in allg)+6; y1=max(b.y1 for b in allg)+6
        region=[x0,y0,x1,y1]
        # map to registry path-objects: center in region, not large
        prot=cfg["protect_large_area_frac"]
        matched=[o for o in objs if x0<=(o["bbox"][0]+o["bbox"][2])/2<=x1
                 and y0<=(o["bbox"][1]+o["bbox"][3])/2<=y1 and o["area_frac"]<prot]
        # confidence from signals
        n_lines=len(lines); n_obj=len(matched)
        garment=max((o for o in objs if x0-30<=(o['bbox'][0]+o['bbox'][2])/2<=x1+30
                     and y0-30<=(o['bbox'][1]+o['bbox'][3])/2<=y1+30), key=lambda o:o['area_frac'], default=None)
        contrast=0.0
        if garment and garment["fill"]:
            gc=tuple(int(garment["fill"][k:k+2],16)/255 for k in (1,3,5))
            cc=sum(1 for o in matched if o["fill"] and math.dist([int(o["fill"][k:k+2],16)/255 for k in (1,3,5)],gc)>0.17)
            contrast=cc/max(n_obj,1)
        # region compactness: a clean logo is COMPACT. Broad region / too many objects
        # => likely grabbing figure detail => low confidence => manual review.
        rh=(y1-y0)/H; rw=(x1-x0)/W
        base=0.15*min(n_lines,3) + 0.45*contrast + 0.15
        penalty=1.0
        if n_obj>180: penalty*=max(0.25, 1-(n_obj-180)/600)
        if rh>0.30:   penalty*=max(0.35, 1-(rh-0.30)*2)
        if rw>0.22:   penalty*=max(0.5, 1-(rw-0.22)*2)
        conf=round(min(1.0, base*penalty),2)
        decision=("auto" if conf>=cfg["auto_threshold"] else
                  "review" if conf>=cfg["review_threshold"] else "skip")
        why=[f"{n_lines} текст-строк", f"{n_obj} объектов",
             f"контраст {contrast:.0%}", f"область {rw:.0%}×{rh:.0%} стр.",
             f"штраф за широту ×{penalty:.2f}"]
        cands.append({"id":"cand_torso","zone":"torso","region":[round(v,1) for v in region],
                      "object_ids":[o["id"] for o in matched], "object_count":n_obj,
                      "confidence":round(conf,2), "decision":decision, "explanation":why})
    d.close()
    return {"source":os.path.basename(pdf),"page_pt":[round(W,1),round(H,1)],
            "config":{"auto":cfg["auto_threshold"],"review":cfg["review_threshold"]},
            "candidates":cands}

def preview(pdf, result, out_png):
    from PIL import Image, ImageDraw
    pg=pymupdf.open(pdf)[0]; W=pg.rect.width; z=min(900/W,1.4)
    pix=pg.get_pixmap(matrix=pymupdf.Matrix(z,z)); im=Image.frombytes("RGB",(pix.w,pix.h),pix.samples); d=ImageDraw.Draw(im)
    col={"auto":(20,170,70),"review":(230,160,0),"skip":(200,40,40)}
    for c in result["candidates"]:
        x0,y0,x1,y1=[v*z for v in c["region"]]
        d.rectangle([x0,y0,x1,y1],outline=col[c["decision"]],width=3)
        d.text((x0,y0-12),f'{c["decision"].upper()} {c["confidence"]} ({c["object_count"]} об.)',fill=col[c["decision"]])
    im.save(out_png)

if __name__=="__main__":
    import sys
    os.makedirs("logotool/reports",exist_ok=True); os.makedirs("logotool/previews",exist_ok=True)
    sys.path.insert(0,"logotool/src")
    for pdf in sys.argv[1:]:
        res=detect(pdf); stem=os.path.splitext(os.path.basename(pdf))[0]
        json.dump(res,open(f"logotool/reports/detect_{stem}.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
        preview(pdf,res,f"logotool/previews/detect_{stem}.png")
        for c in res["candidates"]:
            print(f"{stem}: {c['id']} conf={c['confidence']} -> {c['decision'].upper()} | {c['object_count']} объектов | {c['explanation']}")
