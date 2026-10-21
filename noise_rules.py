"""国会発言データのノイズ判定・本文正規化ルール。"""

from __future__ import annotations

import re


SPEAKER_PREFIX = re.compile(r"^○[^\s　]+[\s　]+")
CHAIR_PREFIX = re.compile(r"^○[^\s　]+(?:委員長|主査|座長)[\s　]+")
STAGE_DIRECTION = re.compile(
    r"[（〔](?:発言する者あり|拍手|笑声|騒然|速記中止|「[^」]*」と呼ぶ者あり)[）〕]"
)
SEPARATOR = re.compile(r"[\s　]*[―◇]{3,}[\s　]*")
FORMALITY_ONLY = re.compile(
    r"^(?:ありがとうございます|ありがとうございました|以上です|終わります|結構です|はい、どうぞ)[。．]?$"
)


def body_without_speaker_prefix(text: str) -> str:
    return SPEAKER_PREFIX.sub("", text, count=1).strip()


def clean_text(text: str) -> str:
    """発言者ラベルと舞台注記を除き、空白を正規化する。"""
    text = body_without_speaker_prefix(text)
    text = STAGE_DIRECTION.sub(" ", text)
    text = SEPARATOR.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def noise_labels(record: dict) -> list[str]:
    """削除候補を理由付きで返す。原データは変更しない。"""
    text = record.get("speech", "")
    body = body_without_speaker_prefix(text)
    labels: list[str] = []

    if record.get("nameOfMeeting") != "予算委員会":
        labels.append("non_exact_meeting")
    if CHAIR_PREFIX.match(text):
        labels.append("procedural_chair")
    if FORMALITY_ONLY.fullmatch(body):
        labels.append("formality_only")
    if len(clean_text(text)) <= 30:
        labels.append("very_short_review")
    if STAGE_DIRECTION.search(text):
        labels.append("contains_stage_direction")
    return labels


def should_exclude(record: dict, exact_meeting_only: bool = True) -> bool:
    """高精度な既定ルール。短文・舞台注記だけでは除外しない。"""
    labels = set(noise_labels(record))
    if exact_meeting_only and "non_exact_meeting" in labels:
        return True
    return bool(labels & {"procedural_chair", "formality_only"})
