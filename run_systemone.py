"""IgakuQA benchmark runner for Ollama "decision" models (e.g. d3:27b) via POST /v1/systemone.

The model scores each labeled choice; we take the top-k labels where k = number of
gold answers (mirrors the original prompt "必ずa,b,c,d,eの中からちょうどk個選んでください").
Numeric-answer questions (no choices) cannot be expressed as a choice and are output as "NA".
"""
import argparse, glob, json, os, string, time, urllib.request

INSTRUCTIONS = "この医師国家試験の問題の正解の選択肢はどれか。"

def build_state(q):
    lines = ["医師国家試験の問題です。", "問題: " + q["problem_text"]]
    for label, choice in zip(string.ascii_lowercase, q["choices"]):
        lines.append(f"{label}: {choice}")
    k = len(q["answer"])
    if k > 1:
        lines.append(f"正解は{k}個あります。")
    return "\n".join(lines)

def ask(host, model, q, timeout=600):
    criteria = {l: c for l, c in zip(string.ascii_lowercase, q["choices"])}
    body = {"model": model, "state": build_state(q),
            "questions": {"q1": {"type": "choice", "instructions": INSTRUCTIONS, "criteria": criteria}}}
    req = urllib.request.Request(host + "/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"]["q1"]

def run_file(in_file, out_file, host, model):
    qs = [json.loads(l) for l in open(in_file)]
    done = {}
    if os.path.exists(out_file):
        done = {d["problem_id"]: d for d in map(json.loads, open(out_file))}
    out = []
    for q in qs:
        pid = q["problem_id"]
        if pid in done and done[pid]["prediction"] != "ERROR":
            out.append(done[pid]); continue
        if not q["choices"]:
            out.append({"problem_id": pid, "prediction": "NA", "explanation": "numeric question; not supported by choice API"})
            continue
        for attempt in range(3):
            try:
                a = ask(host, model, q); break
            except Exception as e:
                print(f"  {pid} failed ({e}); retry"); time.sleep(5); a = None
        if a is None:
            out.append({"problem_id": pid, "prediction": "ERROR", "explanation": ""}); continue
        probs = a["probabilities"]
        k = len(q["answer"])
        top = sorted(probs, key=probs.get, reverse=True)[:k]
        out.append({"problem_id": pid, "prediction": ",".join(sorted(top)),
                    "explanation": json.dumps({"probabilities": probs, "confidence": a.get("confidence")}, ensure_ascii=False)})
    with open(out_file, "w") as f:
        for d in out:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="d3:27b")
    p.add_argument("--host", default="http://127.0.0.1:11434")
    p.add_argument("--data-dir", default="../IgakuQA/data")
    p.add_argument("--out-dir", default="predictions")
    p.add_argument("--files", nargs="*", help="specific input jsonl files (default: all exams)")
    a = p.parse_args()
    tag = a.model.replace(":", "-")
    files = a.files or sorted(glob.glob(os.path.join(a.data_dir, "*", "*-[A-F].jsonl")))
    for fn in files:
        year = os.path.basename(os.path.dirname(fn))
        os.makedirs(os.path.join(a.out_dir, year), exist_ok=True)
        out = os.path.join(a.out_dir, year, os.path.basename(fn).replace(".jsonl", f"_{tag}.jsonl"))
        t = time.time(); run_file(fn, out, a.host, a.model)
        print(f"{fn} -> {out} ({time.time()-t:.0f}s)", flush=True)
