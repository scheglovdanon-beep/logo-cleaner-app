# -*- coding: utf-8 -*-
"""Stage 4 — removal (TZ §6, method-3). Remove the SPECIFIC path-objects of a logo from the
content stream via per-object redaction. Never masks, never rasterizes, never edits input."""
import pymupdf

def remove_objects(pdf, obj_indices, out):
    d=pymupdf.open(pdf); pg=d[0]; dr=pg.get_drawings()
    done=0
    for i in obj_indices:
        if 0<=i<len(dr):
            b=dr[i]["rect"]; pg.add_redact_annot(pymupdf.Rect(b.x0-1,b.y0-1,b.x1+1,b.y1+1),fill=False); done+=1
    pg.apply_redactions(graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                        text=pymupdf.PDF_REDACT_TEXT_REMOVE, images=pymupdf.PDF_REDACT_IMAGE_NONE)
    d.save(out, garbage=4, deflate=True)
    return done

def process(pdf, detect_result, out, approve=("auto",)):
    idxs=[]; used=[]
    for c in detect_result["candidates"]:
        if c["decision"] in approve:
            idxs += [int(o.split("_")[1]) for o in c["object_ids"]]
            used.append(c["id"])
    n=remove_objects(pdf, sorted(set(idxs)), out)
    return {"removed_objects": n, "candidates_applied": used}
