# -*- coding: utf-8 -*-
"""Stage 6 — batch processing (TZ §8). Modes: analyze | preview | process | validate.
Input is never modified; outputs go to separate folders; per-file errors are isolated;
re-runs are safe. Writes a JSON summary report."""
import os, sys, json, hashlib, glob, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit, registry, detector, remover, validator

ROOT="logotool"
DIRS={k:f"{ROOT}/{k}" for k in ["input","output","previews","reports","config","logs"]}
for d in DIRS.values(): os.makedirs(d, exist_ok=True)

def _log(msg):
    open(f"{DIRS['logs']}/batch.log","a").write(msg+"\n"); print(msg)

def run(mode, approve=("auto",)):
    files=sorted(glob.glob(f"{DIRS['input']}/*.pdf"))
    summary={"mode":mode,"files":len(files),"results":[]}
    for src in files:
        stem=os.path.splitext(os.path.basename(src))[0]
        r={"file":os.path.basename(stem)}
        try:
            if mode=="analyze":
                meta,objs=registry.build_registry(src)
                json.dump({"meta":meta,"objects":objs},open(f"{DIRS['reports']}/registry_{stem}.json","w",encoding="utf-8"),ensure_ascii=False)
                registry.diagnostic_preview(src,objs,f"{DIRS['previews']}/registry_{stem}.png")
                r.update(objects=meta["object_count"], status="analyzed")
            elif mode=="preview":
                det=detector.detect(src)
                json.dump(det,open(f"{DIRS['reports']}/detect_{stem}.json","w",encoding="utf-8"),ensure_ascii=False)
                detector.preview(src,det,f"{DIRS['previews']}/detect_{stem}.png")
                r.update(candidates=[{"decision":c["decision"],"conf":c["confidence"],"objs":c["object_count"]} for c in det["candidates"]], status="previewed")
            elif mode=="process":
                h0=hashlib.md5(open(src,'rb').read()).hexdigest()
                det=detector.detect(src)
                decs=[c["decision"] for c in det["candidates"]]
                if not any(d in approve for d in decs):
                    r.update(status="skipped", reason="нет кандидатов с решением "+str(approve)+f" (есть: {decs or 'нет'})")
                else:
                    out=f"{DIRS['output']}/{stem}.pdf"
                    res=remover.process(src,det,out,approve=approve)
                    reg=next((c["region"] for c in det["candidates"] if c["decision"] in approve),None)
                    val=validator.validate(src,out,region=reg,src_hash=h0)
                    json.dump({"detect":det,"remove":res,"validate":val},open(f"{DIRS['reports']}/pipeline_{stem}.json","w",encoding="utf-8"),ensure_ascii=False)
                    r.update(status="processed", removed=res["removed_objects"], verdict=val["verdict"],
                             input_untouched=val["input_untouched"])
            elif mode=="validate":
                out=f"{DIRS['output']}/{stem}.pdf"
                if os.path.exists(out):
                    val=validator.validate(src,out); r.update(status="validated", verdict=val["verdict"])
                else: r.update(status="skipped", reason="нет выходного файла")
        except Exception as e:
            r.update(status="error", error=str(e)); _log(f"ERROR {stem}: {traceback.format_exc()}")
        summary["results"].append(r)
    json.dump(summary,open(f"{DIRS['reports']}/batch_{mode}.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return summary

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "analyze"
    approve=tuple(sys.argv[2].split(",")) if len(sys.argv)>2 else ("auto",)
    s=run(mode,approve)
    print(f"\n=== BATCH {mode} (approve={approve}) — файлов {s['files']} ===")
    for r in s["results"]:
        print(f"  {r['file'][:22]:24} {r.get('status')}  "+("; ".join(f"{k}={v}" for k,v in r.items() if k not in('file','status'))))
