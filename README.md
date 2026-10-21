# 国会発言データ取得

国会会議録検索システムAPIから、期間・会議名・院を指定して発言本文をJSON Lines形式で取得します。

## 実行例

```bash
python3 fetch_speeches.py \
  --years 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026 \
  --meeting 予算委員会 \
  --house 衆議院
```

取得結果は `data/speeches_YYYY.jsonl` に年別保存されます。1行が1発言です。

再実行時は対象年のファイルを作り直します。

## ノイズ確認と除外

固定シードで150件を抽出し、レビュー用CSVを作成します。

```bash
python3 review_noise.py
```

元データを残したまま、完全一致の「予算委員会」に絞り、委員長・主査・座長の議事進行発言などを除外します。

```bash
python3 filter_speeches.py data/speeches_2016.jsonl data/speeches_2026.jsonl
```

短文は意味のある答弁を含むため自動除外せず、`review_flags` を付けます。分科会・公聴会も残す場合は `--include-related-meetings` を指定します。

## 2016年発言のトピック・クラスタリング

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-clustering.txt
.venv/bin/jupyter lab notebooks/cluster_speeches_2016.ipynb
```

Notebookを上から実行すると、クラスタ数を `k=10` に固定して学習し、発言別結果とクラスタ要約を `analysis/clustering_2016/` に出力します。

## 2026年発言のトピック・クラスタリング

2016年版と同じ前処理・設定で、2026年の3,453発言を10クラスタに分類します。

```bash
.venv/bin/jupyter lab notebooks/cluster_speeches_2026.ipynb
```

結果は `analysis/clustering_2026/` に出力されます。

## 2016〜2026年の横断クラスタリング

11暦年（2026年は取得時点まで）のクリーニング済み68,948発言を、共通の特徴空間で10クラスタに分類します。

```bash
.venv/bin/jupyter lab notebooks/cluster_speeches_2016_2026.ipynb
```

結果は `analysis/clustering_2016_2026/` に出力されます。

旧クラスタ0・6を除外して10クラスタへ再学習するNotebookは次のとおりです。

```bash
.venv/bin/jupyter lab notebooks/cluster_speeches_2016_2026_excluding_0_6.ipynb
```

元結果は残し、再学習結果を `analysis/clustering_2016_2026_excluding_0_6/` に保存します。
