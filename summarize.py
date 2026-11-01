"""Score systemone predictions against IgakuQA gold (same rule as IgakuQA/scripts/evaluate_main.py).

usage: python3 summarize.py [--data-dir ../IgakuQA/data] [--pred-dir predictions]
                            [--baseline-dir ../IgakuQA/baseline_results] [--models d3-27b,...] [--markdown]
Baselines from the IgakuQA paper (gpt4, chatgpt, gpt3, student-majority) are looked up in --baseline-dir.
"""
import argparse, glob, json, os

YEARS = ["2018", "2019", "2020", "2021", "2022"]
PAPER = ["gpt4", "chatgpt", "gpt3", "student-majority"]

def correct(pred, gold):
    p = sorted(pred.split(",")); g = sorted(gold["answer"]); pid = gold["problem_id"]
    if pid == "116A71": return True                                   # all answers accepted
    if pid == "112B30" and p in (["a"], ["d"]): return True           # two answers accepted
    return p == g

def score(data_dir, pred_dir, model, year):
    st = dict(c=0, n=0, s=0, t=0, ct=0, nt=0, ci=0, ni=0)
    for gf in sorted(glob.glob(os.path.join(data_dir, year, "*-[A-F].jsonl"))):
        pf = os.path.join(pred_dir, year, os.path.basename(gf).replace(".jsonl", f"_{model}.jsonl"))
        if not os.path.exists(pf): return None
        for l1, l2 in zip(open(gf), open(pf)):
            g, p = json.loads(l1), json.loads(l2)
            assert g["problem_id"] == p["problem_id"]
            ok = correct(p["prediction"], g); pts = int(g["points"])
            st["c"] += ok; st["n"] += 1; st["s"] += ok * pts; st["t"] += pts
            k = "t" if g["text_only"] else "i"; st["c" + k] += ok; st["n" + k] += 1
    return st

def pct(a, b): return f"{100*a/b:.1f}" if b else "-"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../IgakuQA/data")
    ap.add_argument("--pred-dir", default="predictions")
    ap.add_argument("--baseline-dir", default="../IgakuQA/baseline_results")
    ap.add_argument("--models", default=None, help="comma separated; default = all found in pred-dir")
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args()
    if a.models:
        models = a.models.split(",")
    else:
        models = sorted({os.path.basename(f).split("_", 1)[1][:-6] for f in glob.glob(os.path.join(a.pred_dir, "*", "*_*.jsonl"))})
    res = {}
    for m in models + PAPER:
        d = a.pred_dir if m in models else a.baseline_dir
        per = {y: score(a.data_dir, d, m, y) for y in YEARS}
        if all(per.values()): res[m] = per
    tot = {m: {k: sum(per[y][k] for y in YEARS) for k in per["2018"]} for m, per in res.items()}
    order = sorted(res, key=lambda m: -tot[m]["c"] / tot[m]["n"])
    if a.markdown:
        print("| model | overall | " + " | ".join(YEARS) + " | text-only | w/ image | score (5y) |")
        print("|---|---|" + "---|" * len(YEARS) + "---|---|---|")
        for m in order:
            t = tot[m]; name = f"*{m}* (paper)" if m in PAPER else f"**{m}**"
            print(f"| {name} | {pct(t['c'],t['n'])} | " + " | ".join(pct(res[m][y]['c'], res[m][y]['n']) for y in YEARS)
                  + f" | {pct(t['ct'],t['nt'])} | {pct(t['ci'],t['ni'])} | {t['s']}/{t['t']} |")
        print("\n**Score per year (points / total)**\n")
        print("| model | " + " | ".join(YEARS) + " |"); print("|---|" + "---|" * len(YEARS))
        for m in order:
            print(f"| {m} | " + " | ".join(f"{res[m][y]['s']}/{res[m][y]['t']}" for y in YEARS) + " |")
    else:
        print(f"{'model':22} {'overall':>7} " + " ".join(f"{y:>6}" for y in YEARS) + f" {'text':>6} {'image':>6}")
        for m in order:
            t = tot[m]
            print(f"{m:22} {pct(t['c'],t['n']):>7} " + " ".join(f"{pct(res[m][y]['c'],res[m][y]['n']):>6}" for y in YEARS)
                  + f" {pct(t['ct'],t['nt']):>6} {pct(t['ci'],t['ni']):>6}")

if __name__ == "__main__":
    main()
