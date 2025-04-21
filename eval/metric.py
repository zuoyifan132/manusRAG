# -*- coding: utf-8 -*-
# Created on 2024/8/26

from typing import List, Union, Optional, Tuple
import ast


def TP_FP_num(response: dict) -> Optional[tuple[int, int]]:
    classification = response.get("classification", None)
    if not classification:
        return None
    TP_num = classification.get("TP", None)
    FP_num = classification.get("FP", None)

    print(TP_num)
    print(FP_num)

    if TP_num is None or FP_num is None:
        return None

    return len(TP_num), len(FP_num)


def single_hit(tp):
    if isinstance(tp, str):
        tp = ast.literal_eval(tp)
    TP_num = len(tp)
    print("TP_num: ", TP_num)
    return TP_num != 0


def single_question_recall_rate(tp, ground_truth: List[str]):
    if isinstance(tp, str):
        tp = ast.literal_eval(tp)
    TP_num = len(tp)
    return float(TP_num / len(ground_truth))
