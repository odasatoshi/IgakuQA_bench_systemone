# IgakuQA bench for Ollama decision models (`/v1/systemone`)

[IgakuQA](https://github.com/jungokasai/IgakuQA)（2018〜2022年の日本の医師国家試験、全2,000問）を使って、Ollamaの **decision モデル**（`d3`、`clef`、`pplx-decider` など）を評価するためのスクリプト一式です。

結果は [result.md](result.md) を参照してください。

## decision モデルについて
decision モデルは `/api/chat` と `/api/generate` に対応しておらず（`does not support chat` のエラーになる）、`ollama run MODEL --ask ... --choice ...` で使う分類型のモデルです。
CLI が内部で呼んでいる API は次のとおりです。

```http
POST /v1/systemone
{"model": "d3:27b",
 "state": "<問題文>",
 "questions": {"q1": {"type": "choice",
                      "instructions": "<質問>",
                      "criteria": {"a": "<選択肢a>", "b": "<選択肢b>", ...}}}}
```

レスポンスには、選択肢ごとの確率が入ります。

```json
{"answers": {"q1": {"type": "choice", "choice": "d",
                    "probabilities": {"a": 0.0003, "d": 0.9995, ...},
                    "confidence": 0.995}}}
```

## 評価方法
- **state**: `医師国家試験の問題です。` + `問題: <problem_text>` + `a: … e: …` を入れます。正解が複数ある問題には、`正解はk個あります。` も付けます。
- **instructions**: `この医師国家試験の問題の正解の選択肢はどれか。`
- **criteria**: `{a: 選択肢a, …}` の形にします（6択・8択の問題にも対応しています）。
- **予測**: 確率の高い順に、正解数 k 個の選択肢を選びます。元論文のプロンプトも「ちょうどk個選んでください」と正解数を伝えているので、条件は同じです。
- **数値を答える計算問題（12問）**: 選択肢がなく choice 型では表せないため、`NA`（不正解）とします。
- **画像**: IgakuQA には画像が含まれていません。画像付きの問題（529問）もテキストだけで解かせています。元論文のGPT-4と同じ条件です。
- **採点**: `IgakuQA/scripts/evaluate_main.py` と同じ基準です（116A71 は全員正解、112B30 は a と d のどちらも正解）。
- few-shot も chain-of-thought も使わず、1問につき1リクエストです。サンプリングはしませんが、GPU の浮動小数点演算の影響で確率が小数第3位あたりで揺れます。確率が拮抗している問題では、まれに予測が変わります（kev で 116-B を再実行したところ、50問中1問が変わりました）。

## 必要なもの
- Python 3（標準ライブラリだけで動きます）
- Ollama 0.40 以降（`/v1/systemone` に対応しているもの）と、評価したい decision モデル
- IgakuQA をこのディレクトリと同じ階層に clone しておくこと

```text
github/
├── IgakuQA/                    # git clone https://github.com/jungokasai/IgakuQA
└── IgakuQA_bench_systemone/    # ここ
```

## 使い方
```bash
# 1モデル（全30ファイル）。結果は predictions/<年>/<試験>_<model>.jsonl に保存されます
python3 run_systemone.py --model d3:27b

# 特定のファイルだけ
python3 run_systemone.py --model clef:latest --files ../IgakuQA/data/2022/116-A.jsonl

# 全モデルを実行してから集計（MODELS 環境変数で対象を変更できます）
./run_all.sh

# 集計（論文のベースライン gpt4/chatgpt/gpt3/student-majority も一緒に表示します）
python3 summarize.py              # テキスト表
python3 summarize.py --markdown   # Markdown 表
```

`run_systemone.py` の主なオプション: `--model`、`--host`（既定 `http://127.0.0.1:11434`）、`--data-dir`、`--out-dir`、`--files`。
既存の出力ファイルがある場合は、`ERROR` 以外の問題をスキップして続きから実行します。

## ファイル構成
| パス | 内容 |
|---|---|
| `run_systemone.py` | 推論スクリプト（`/v1/systemone` を呼び出します） |
| `summarize.py` | 採点・集計スクリプト |
| `run_all.sh` | 全モデルを一括で実行します |
| `predictions/` | 各モデルの予測結果です。`explanation` に選択肢ごとの確率と confidence が入っています |
| `result.md` | ベンチマークの結果 |
