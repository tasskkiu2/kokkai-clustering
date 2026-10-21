"""2016年衆議院予算委員会発言の再現可能なトピッククラスタリング。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import Normalizer
from sudachipy import dictionary, tokenizer


RANDOM_STATE = 42
EXPECTED_ROWS = 5928
FIXED_K = 10
K_CANDIDATES = range(5, 21)
SILHOUETTE_SAMPLE_SIZE = 2000
TOKENIZER = dictionary.Dictionary().create()
SPLIT_MODE = tokenizer.Tokenizer.SplitMode.C
KEEP_POS = {"名詞", "動詞", "形容詞"}
NOUN_SUBCATEGORIES = {"普通名詞", "固有名詞"}
STOPWORDS = {
    "ある", "いる", "する", "なる", "れる", "られる", "いただく", "くださる",
    "思う", "考える", "答える", "申し上げる", "いう", "こと", "もの", "よう",
    "ところ", "ため", "これ", "それ", "そこ", "こちら", "現在", "今回", "今",
    "私", "方", "委員", "大臣", "総理", "政府", "質問", "答弁", "お尋ね",
    "指摘", "問題", "話", "御覧", "お願い", "確認", "説明", "以上",
    # Sudachiの正規形（表層がひらがなでも漢字へ正規化される語を含む）
    "有る", "居る", "為る", "成る", "言う", "思う", "考える", "答える",
    "申し上げる", "頂く", "下さる", "御座る", "出来る", "分かる", "見る",
    "聞く", "行く", "来る", "出す", "付く", "終わる", "良い", "無い",
    "おる", "つく", "おく", "遣る", "仰る", "通り", "発言", "時間",
    "先生", "皆さん", "国会", "本当", "非常", "必要", "関係", "対応",
}
NUMERIC = re.compile(r"^[\d０-９一二三四五六七八九十百千万億兆・,.]+$")


def tokenize_ja(text: str) -> list[str]:
    """Sudachiで本文由来の内容語だけを正規化して返す。"""
    source = str(text).strip()
    terms: list[str] = []
    for morpheme in TOKENIZER.tokenize(source, SPLIT_MODE):
        pos = morpheme.part_of_speech()[0]
        term = morpheme.normalized_form().strip().lower()
        if (
            pos in KEEP_POS
            and len(term) > 1
            and term not in STOPWORDS
            and not NUMERIC.fullmatch(term)
        ):
            terms.append(term)
    return terms


def tokenize_ja_nouns(text: str) -> list[str]:
    """Sudachiで本文由来の普通名詞・固有名詞だけを正規化して返す。"""
    source = str(text).strip()
    terms: list[str] = []
    for morpheme in TOKENIZER.tokenize(source, SPLIT_MODE):
        pos = morpheme.part_of_speech()
        term = morpheme.normalized_form().strip().lower()
        if (
            pos[0] == "名詞"
            and pos[1] in NOUN_SUBCATEGORIES
            and len(term) > 1
            and term not in STOPWORDS
            and not NUMERIC.fullmatch(term)
        ):
            terms.append(term)
    return terms


def load_input(path: Path, expected_rows: int = EXPECTED_ROWS) -> pd.DataFrame:
    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    frame = pd.DataFrame(rows)
    required = {
        "speechID", "date", "nameOfMeeting", "speaker", "speakerPosition",
        "speech", "speech_cleaned", "review_flags", "speechURL",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"必要な列がありません: {sorted(missing)}")
    assert len(frame) == expected_rows, f"入力件数が想定外です: {len(frame)}"
    assert frame["speechID"].is_unique, "speechIDが重複しています"
    assert frame["nameOfMeeting"].eq("予算委員会").all(), "会議名に対象外が含まれます"
    assert frame["speech_cleaned"].notna().all(), "speech_cleanedに欠損があります"
    assert frame["speech_cleaned"].str.strip().ne("").all(), "speech_cleanedに空文字があります"
    frame["date"] = pd.to_datetime(frame["date"])
    frame["year"] = frame["date"].dt.year.astype("int16")
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    return frame


def vectorize(frame: pd.DataFrame):
    vectorizer = TfidfVectorizer(
        tokenizer=tokenize_ja,
        token_pattern=None,
        lowercase=False,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.85,
        max_features=20_000,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform(frame["speech_cleaned"])
    keep_mask = np.asarray(matrix.getnnz(axis=1) > 0)
    forbidden = {"発言短文", "低情報発言"} & set(vectorizer.get_feature_names_out())
    if forbidden:
        raise AssertionError(f"人工トークンがTF-IDF語彙に混入しています: {sorted(forbidden)}")
    return vectorizer, matrix[keep_mask], keep_mask


def vectorize_nouns(frame: pd.DataFrame):
    """普通名詞・固有名詞だけでTF-IDFを作り、ゼロベクトル行を識別する。"""
    vectorizer = TfidfVectorizer(
        tokenizer=tokenize_ja_nouns,
        token_pattern=None,
        lowercase=False,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.85,
        max_features=20_000,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform(frame["speech_cleaned"])
    keep_mask = np.asarray(matrix.getnnz(axis=1) > 0)
    forbidden = {"発言短文", "低情報発言"} & set(vectorizer.get_feature_names_out())
    if forbidden:
        raise AssertionError(f"人工トークンがTF-IDF語彙に混入しています: {sorted(forbidden)}")
    return vectorizer, matrix[keep_mask], keep_mask


def reduce_dimensions(matrix):
    svd = TruncatedSVD(n_components=100, random_state=RANDOM_STATE)
    reduced = svd.fit_transform(matrix)
    normalized = Normalizer(copy=False).fit_transform(reduced)
    return svd, normalized


def compare_k(
    reduced: np.ndarray,
    candidates=K_CANDIDATES,
) -> tuple[pd.DataFrame, dict[int, KMeans]]:
    rng = np.random.default_rng(RANDOM_STATE)
    sample_idx = np.sort(
        rng.choice(len(reduced), size=min(SILHOUETTE_SAMPLE_SIZE, len(reduced)), replace=False)
    )
    models: dict[int, KMeans] = {}
    results: list[dict] = []
    for k in candidates:
        model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
        labels = model.fit_predict(reduced)
        sizes = np.bincount(labels, minlength=k)
        if np.any(sizes == 0):
            raise AssertionError(f"k={k} に空クラスタがあります")
        score = silhouette_score(reduced[sample_idx], labels[sample_idx], metric="euclidean")
        results.append({
            "k": k,
            "silhouette": score,
            "inertia": model.inertia_,
            "smallest_cluster": int(sizes.min()),
            "largest_cluster": int(sizes.max()),
        })
        models[k] = model
    scores = pd.DataFrame(results).sort_values("k").reset_index(drop=True)
    return scores, models


def choose_k(scores: pd.DataFrame) -> int:
    """silhouette最大、数値上同点なら小さいkを選ぶ。"""
    best = scores.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0]
    return int(best["k"])


def cluster_details(
    frame: pd.DataFrame,
    matrix,
    reduced: np.ndarray,
    vectorizer: TfidfVectorizer,
    model: KMeans,
):
    labels = model.labels_
    distances = np.linalg.norm(reduced - model.cluster_centers_[labels], axis=1)
    frame = frame.copy()
    frame["cluster"] = labels
    # 並列BLAS由来の機械イプシロン級の差をCSVへ持ち込まない。
    frame["centroid_distance"] = np.round(distances, 12)
    frame["representativeness"] = np.round(1.0 / (1.0 + distances), 12)

    terms = vectorizer.get_feature_names_out()
    summaries: list[dict] = []
    provisional: dict[int, str] = {}
    for cluster_id in range(model.n_clusters):
        member_idx = np.flatnonzero(labels == cluster_id)
        mean_tfidf = np.asarray(matrix[member_idx].mean(axis=0)).ravel()
        top_idx = mean_tfidf.argsort()[::-1][:12]
        top_terms = [terms[i] for i in top_idx if mean_tfidf[i] > 0]
        label = "・".join(top_terms[:3])
        provisional[cluster_id] = label
        representative_idx = member_idx[np.argsort(distances[member_idx])[:5]]
        summaries.append({
            "cluster": cluster_id,
            "provisional_label": label,
            "count": len(member_idx),
            "ratio": round(len(member_idx) / len(frame), 12),
            "top_terms": " | ".join(top_terms),
            "representative_speech_ids": " | ".join(frame.iloc[representative_idx]["speechID"]),
        })
    frame["provisional_label"] = frame["cluster"].map(provisional)
    return frame, pd.DataFrame(summaries).sort_values("cluster").reset_index(drop=True)


def apply_manual_labels(
    assignments: pd.DataFrame,
    summary: pd.DataFrame,
    manual_labels: dict[int, str],
):
    assignments = assignments.copy()
    summary = summary.copy()
    final_map = dict(zip(summary["cluster"], summary["provisional_label"]))
    final_map.update(manual_labels)
    assignments["cluster_label"] = assignments["cluster"].map(final_map)
    summary["cluster_label"] = summary["cluster"].map(final_map)
    return assignments, summary


def export_results(assignments: pd.DataFrame, summary: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = [
        "speechID", "date", "year", "speaker", "speakerPosition", "speech", "speech_cleaned",
        "review_flags", "speechURL", "cluster", "cluster_label", "centroid_distance",
        "representativeness",
    ]
    exported = assignments[columns].copy()
    exported["date"] = exported["date"].dt.strftime("%Y-%m-%d")
    exported["review_flags"] = exported["review_flags"].map(
        lambda value: ";".join(value) if isinstance(value, list) else str(value)
    )
    exported.to_csv(output_dir / "speech_clusters.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "cluster_summary.csv", index=False, encoding="utf-8-sig")
