# -*- coding: utf-8 -*-
"""Stage 1 — structural audit of PDF layouts (TZ §3). READ-ONLY, never modifies input.
For each PDF answers: pages/size, OCG layers, vector/text counts, Form XObjects &
marked-content groups, images, and whether logos are isolatable objects."""
import sys, os, json, re, pymupdf, pikepdf

def audit_one(path):
    r={"file":os.path.basename(path)}
    d=pymupdf.open(path); pg=d[0]
    r["pages"]=len(d)
    r["page_pt"]=[round(pg.rect.width,1),round(pg.rect.height,1)]
    r["ocg_layers"]=[i["name"] for i in d.get_ocgs().values()]
    r["vector_drawings"]=len(pg.get_drawings())
    r["live_text_fonts"]=len(pg.get_fonts())          # 0 => text already outlined to curves
    r["raster_images"]=sum(len(p.get_images()) for p in d)
    # marked-content groups in page content (Illustrator groups/layers often -> /OCx BDC)
    cont=pg.read_contents().decode("latin-1","replace")
    r["marked_content_blocks"]=len(re.findall(r'/\w+\s+BDC|/\w+\s+BMC', cont))
    # Form XObjects via pikepdf (nested sub-objects)
    px=pikepdf.open(path)
    forms=0; imgs=0
    try:
        for name,obj in px.pages[0].get("/Resources",{}).get("/XObject",{}).items():
            st=str(obj.get("/Subtype",""))
            if "Form" in st: forms+=1
            elif "Image" in st: imgs+=1
    except Exception: pass
    r["form_xobjects"]=forms
    r["content_stream_bytes"]=len(cont)
    # --- can logos be isolated? heuristic analysis ---
    notes=[]
    if r["ocg_layers"] and any(re.search(r'logo|лого|text|напис', n, re.I) for n in r["ocg_layers"]):
        notes.append("есть OCG-слой с именем похожим на лого -> можно пробовать удаление слоя")
    elif r["ocg_layers"]:
        notes.append("OCG-слои есть, но это панели/нумерация (не лого) -> удаление слоя не выделит лого")
    else:
        notes.append("OCG-слоёв нет (файл сплющен)")
    if forms>0: notes.append(f"{forms} Form XObject — проверить, не отдельный ли это лого")
    if r["marked_content_blocks"]<=3:
        notes.append("мало marked-content блоков -> группы Illustrator НЕ сохранены как отдельные контейнеры")
    r["isolatable_logo"]="НЕТ (лого = отдельные пути в общем потоке, не слой/группа/XObject)"
    r["notes"]=notes
    d.close(); px.close()
    return r

if __name__=="__main__":
    files=sys.argv[1:]
    rep={"environment":"see audit log","files":[audit_one(f) for f in files]}
    os.makedirs("logotool/reports",exist_ok=True)
    with open("logotool/reports/audit_report.json","w",encoding="utf-8") as f:
        json.dump(rep,f,ensure_ascii=False,indent=1)
    for r in rep["files"]:
        print(f"\n### {r['file']}  ({r['page_pt'][0]}x{r['page_pt'][1]} pt, {r['pages']} стр.)")
        print(f"  OCG-слои ({len(r['ocg_layers'])}): {r['ocg_layers']}")
        print(f"  вектор-путей: {r['vector_drawings']} | живой текст(шрифты): {r['live_text_fonts']} | растр: {r['raster_images']}")
        print(f"  Form XObject: {r['form_xobjects']} | marked-content блоков: {r['marked_content_blocks']} | поток: {r['content_stream_bytes']} б")
        print(f"  ЛОГО как отдельный объект: {r['isolatable_logo']}")
        for n in r["notes"]: print(f"     - {n}")
