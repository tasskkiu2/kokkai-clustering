# Claude Code用・外部データ／特徴量探索エージェント

分析工程全体を分業するのではなく、外部データと特徴量候補の発見に集中した2つの読み取り専用subagentです。

## 構成

```text
.claude/
└── agents/
    ├── external-data-scout.md
    └── feature-hypothesis-generator.md
```

- `external-data-scout`：外部データ源を広く探索し、取得可能性と結合方法まで整理する
- `feature-hypothesis-generator`：現在のデータと外部データ候補から、具体的な特徴量仮説を大量に作る

EDA、実装、リークの最終判定、モデリングは親Claudeが担当します。

## 導入

このフォルダ内の `.claude` を、分析プロジェクトのルートへコピーしてください。

```text
分析プロジェクト/
├── .claude/
│   └── agents/
│       ├── external-data-scout.md
│       └── feature-hypothesis-generator.md
├── data/
├── notebooks/
└── ...
```

Claude Codeを起動した時点で `.claude/agents/` ディレクトリが存在していなかった場合は、ファイルを配置した後にClaude Codeを再起動してください。

## 単独で使う例

```text
external-data-scout を使って、この分析に追加できる外部データを広く探してください。
既存変数との重複を避け、取得元、期間、粒度、結合キー、予測時点での利用可能性まで整理してください。
ファイルは変更しないでください。
```

```text
feature-hypothesis-generator を使って、現在のデータから試せる特徴量候補を体系的に生成してください。
特徴量名だけでなく、計算方法、仮説、必要データ、利用可能時点、リスクを付けてください。
実装やモデル学習はしないでください。
```

## 2段階で使う例

```text
まず external-data-scout を使い、このプロジェクトに追加できる外部データ候補を調査してください。
その結果を親Claudeが整理したうえで、feature-hypothesis-generator に渡し、
既存データだけで作れる特徴量と外部データを使う特徴量を分けて提案させてください。
採否、リーク判定、実装、モデリングは親Claudeが行ってください。
```

## 使用量を抑える例

```text
external-data-scout を使ってください。
今回はA候補を中心に15件までとし、公式または一次情報を優先してください。
```

```text
feature-hypothesis-generator を使ってください。
今回は低コスト特徴量20件と、実験的特徴量10件に絞ってください。
```

## 設計上の注意

- 2つのエージェントはファイルを編集しません
- 両方ともSonnetを使用します
- 特徴量エージェントは、外部データ探索を一からやり直さないよう指示しています
- リークの疑いはフラグとして返しますが、最終判定は親Claudeに残しています
- 候補数を増やすこと自体を目的にせず、取得可能性と実装可能性も報告させます
