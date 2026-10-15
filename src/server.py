# -*- coding: utf-8 -*-
"""Logo-cleaning dashboard backend (Flask).
Workflow: load figure -> user draws boxes on logos -> /api/clean removes the vector
objects inside (method-3, large shapes protected) -> review before/after -> /api/approve
moves the cleaned PDF to clean/. Inputs are never modified (cleaned copy goes to output/)."""
import os, io, shutil, pymupdf
from flask import Flask, request, jsonify, send_file, Response

HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(HERE)                      # logotool/
IN=os.path.join(ROOT,"input"); OUT=os.path.join(ROOT,"output"); CLEAN=os.path.join(ROOT,"clean")
for d in (IN,OUT,CLEAN): os.makedirs(d,exist_ok=True)
DPI=110
app=Flask(__name__)

def _figs():
    out=[]
    for f in sorted(os.listdir(IN)):
        if f.lower().endswith(".pdf"):
            st=("approved" if os.path.exists(os.path.join(CLEAN,f))
                else "cleaned" if os.path.exists(os.path.join(OUT,f)) else "pending")
            out.append({"id":f,"status":st})
    return out

def _png(path):
    pg=pymupdf.open(path)[0]; return pg.get_pixmap(dpi=DPI).tobytes("png")

@app.route("/")
def index(): return send_file(os.path.join(HERE,"dashboard.html"))

@app.route("/api/figures")
def figures(): return jsonify(_figs())

@app.route("/api/pageinfo")
def pageinfo():
    pg=pymupdf.open(os.path.join(IN,request.args["id"]))[0]
    return jsonify({"w_pt":pg.rect.width,"h_pt":pg.rect.height,"dpi":DPI})

@app.route("/api/image")
def image():
    fid=request.args["id"]; which=request.args.get("which","input")
    path=os.path.join(OUT if which=="output" else IN, fid)
    if not os.path.exists(path): path=os.path.join(IN,fid)
    return Response(_png(path), mimetype="image/png")

@app.route("/api/clean", methods=["POST"])
def clean():
    d=request.get_json(); fid=d["id"]; boxes=d["boxes"]       # boxes in PDF points
    src=os.path.join(IN,fid)
    doc=pymupdf.open(src); pg=doc[0]; pa=pg.rect.width*pg.rect.height; dr=pg.get_drawings()
    idx=set()
    for z in boxes:
        x0,y0,x1,y1=min(z[0],z[2]),min(z[1],z[3]),max(z[0],z[2]),max(z[1],z[3])
        for i,o in enumerate(dr):
            b=o["rect"]; cx=(b.x0+b.x1)/2; cy=(b.y0+b.y1)/2
            if x0<=cx<=x1 and y0<=cy<=y1 and b.width*b.height<0.08*pa: idx.add(i)
    for i in idx:
        b=dr[i]["rect"]; pg.add_redact_annot(pymupdf.Rect(b.x0-1,b.y0-1,b.x1+1,b.y1+1),fill=False)
    pg.apply_redactions(graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                        text=pymupdf.PDF_REDACT_TEXT_REMOVE, images=pymupdf.PDF_REDACT_IMAGE_NONE)
    doc.save(os.path.join(OUT,fid), garbage=4, deflate=True)
    # quick validation
    o=pymupdf.open(os.path.join(OUT,fid))[0]
    val={"page_size_ok": [round(x,1) for x in pg.rect]==[round(x,1) for x in o.rect],
         "still_vector": len(o.get_fonts())==0 and sum(len(p.get_images()) for p in pymupdf.open(os.path.join(OUT,fid)))==0,
         "input_untouched": os.path.exists(src)}
    return jsonify({"ok":True, "removed":len(idx), "validate":val})

@app.route("/api/approve", methods=["POST"])
def approve():
    fid=request.get_json()["id"]; o=os.path.join(OUT,fid)
    if os.path.exists(o):
        shutil.move(o, os.path.join(CLEAN,fid)); return jsonify({"ok":True})
    return jsonify({"ok":False,"err":"сначала очистите фигуру"})

@app.route("/api/reset", methods=["POST"])
def reset():
    fid=request.get_json()["id"]; o=os.path.join(OUT,fid)
    if os.path.exists(o): os.remove(o)
    return jsonify({"ok":True})

if __name__=="__main__":
    port=int(os.environ.get("PORT","8000"))     # Render/Railway set $PORT
    print(f"Дашборд: http://localhost:{port}   (папки: input/ output/ clean/)")
    app.run(host="0.0.0.0", port=port, debug=False)
