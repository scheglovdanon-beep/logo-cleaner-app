# -*- coding: utf-8 -*-
"""Stage 5 — validation (TZ §7). Confirm logo gone + figure preserved + page size + vector,
input untouched, no changes outside the target region; flag suspicious results."""
import os, hashlib, numpy as np, pymupdf

def _arr(pdf,dpi=90):
    pg=pymupdf.open(pdf)[0]; pix=pg.get_pixmap(dpi=dpi,alpha=False)
    return np.frombuffer(pix.samples,np.uint8).reshape(pix.h,pix.w,3)

def validate(src, out, region=None, src_hash=None):
    v={}
    v["input_untouched"] = (src_hash is None) or (hashlib.md5(open(src,'rb').read()).hexdigest()==src_hash)
    s=pymupdf.open(src); o=pymupdf.open(out)
    v["opens_renders"]=True
    v["page_size_same"]= [round(x,1) for x in s[0].rect]==[round(x,1) for x in o[0].rect]
    v["raster_not_added"]= sum(len(p.get_images()) for p in o)<=sum(len(p.get_images()) for p in s)
    v["still_vector"]= len(o[0].get_fonts())==0 and sum(len(p.get_images()) for p in o)==0
    B=_arr(src); A=_arr(out)
    if A.shape!=B.shape:
        v["shape_match"]=False; v["suspicious"]=True; return v
    v["shape_match"]=True
    fg=(B.min(2)<245); diff=(np.abs(A.astype(int)-B.astype(int)).max(2)>25)
    v["changed_frac"]= round(float(diff.sum()/max(fg.sum(),1)),4)
    # change inside vs outside the declared logo region
    outside_frac=inside_frac=None
    if region:
        H,W=B.shape[:2]; pgW=s[0].rect.width; pgH=s[0].rect.height
        zx=W/pgW; zy=H/pgH
        x0,y0,x1,y1=int(region[0]*zx),int(region[1]*zy),int(region[2]*zx),int(region[3]*zy)
        inside=np.zeros_like(diff); inside[max(0,y0-4):y1+4, max(0,x0-4):x1+4]=1
        region_px=inside.sum()
        inside_frac=round(float((diff&(inside>0)).sum()/max(region_px,1)),4)   # how much of region cleared
        outside_frac=round(float((diff&(inside==0)).sum()/max(fg.sum(),1)),4)  # collateral change
        v["change_inside_region_frac"]=inside_frac
        v["change_outside_region_frac"]=outside_frac
    # verdict
    logo_removed = (inside_frac is None and v["changed_frac"]>0.01) or (inside_frac is not None and inside_frac>0.06)
    sus = (not v["page_size_same"]) or (not v["still_vector"]) or (v["changed_frac"]>0.15) \
          or (outside_frac is not None and outside_frac>0.01) or (not logo_removed)
    v["logo_removed"]= bool(logo_removed)
    v["suspicious"]= bool(sus)
    v["verdict"]= "OK" if not v["suspicious"] else ("ЛОГО НЕ УДАЛЁН" if not logo_removed else "НА ПРОВЕРКУ")
    return v
