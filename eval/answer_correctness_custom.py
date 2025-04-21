# -*- coding: utf-8 -*-
# Created on 2024/8/26

import json
import logging
from typing import List, Union, Tuple, Any, Optional

from tqdm import tqdm

from utilities import qwen_generation, deepseek_v3_generation, extract_tp_fp
from answer_correctness_prompt import (
    CORRECTNESS_INSTRUCTIONS,
    ZH_MULTI_CORRECTNESS_INSTRUCTIONS,
    ZH_SINGLE_CORRECTNESS_INSTRUCTIONS,
    REGENERATION_PROMPT
)


PROMPT = {
    "CORRECTNESS_INSTRUCTIONS": CORRECTNESS_INSTRUCTIONS,
    "ZH_SINGLE_CORRECTNESS_INSTRUCTIONS": ZH_SINGLE_CORRECTNESS_INSTRUCTIONS,
    "ZH_MULTI_CORRECTNESS_INSTRUCTIONS": ZH_MULTI_CORRECTNESS_INSTRUCTIONS
}
model_generation = qwen_generation


def format_to_list_str(list_data) -> str:
    return str(list_data)


def attempt_extraction(
    generation_model,
    original_prompt,
    generation_text,
    max_attempt=1
) -> tuple[list[Any], list[Any]]:
    if max_attempt <= 0:
        return [], []
    try:
        return extract_tp_fp(generation_text)
    except:
        regeneration_prompt = original_prompt + REGENERATION_PROMPT
        logging.warning(f"generation invalid json format, retry with: {regeneration_prompt}")
        try:
            regeneration_text = generation_model(regeneration_prompt)
        except:
            logging.warning(f"LLM response failed {regeneration_prompt}")
            return [], []

        return attempt_extraction(
            generation_model=generation_model,
            original_prompt=regeneration_prompt,
            generation_text=regeneration_text,
            max_attempt=max_attempt - 1
        )


def answer_correctness_multi_GT_eval(
    answer: list[str],
    ground_truth: List[str],
    prompt_template: str
) -> tuple[bool, list[Any], list[Any]]:
    list_answer_str = format_to_list_str(answer)
    list_ground_truth_str = format_to_list_str(ground_truth)

    prompt = PROMPT[prompt_template].format(
        answer=list_answer_str,
        ground_truth=list_ground_truth_str
    )

    print("prompt: ", prompt)
    try:
        model_response = model_generation(task=prompt)
        model_response = model_response.replace("```json", "").replace("```", "").strip()
        print("model_response: ", model_response)
    except:
        logging.warning("model_response failed initially")
        model_response = "你输出的json格式有误，输出已省略"

    tp, fp = attempt_extraction(
        generation_model=model_generation,
        original_prompt=prompt,
        generation_text=model_response,
        max_attempt=1
    )

    if len(tp) != 0 and len(fp) != 0:
        return True, tp, fp
    else:
        return False, [], []


def answer_correctness_single_GT_eval(
        answer: list[str],
        ground_truth: List[str],
        prompt_template: str
) -> tuple[bool, list[Any], list[Any]]:
    total_tp, total_fp = [], []

    list_answer_str = format_to_list_str(answer)

    for each_ground_truth in tqdm(ground_truth, desc="eval each ground truth: "):
        each_ground_truth_str = format_to_list_str(each_ground_truth)
        prompt = PROMPT[prompt_template].format(
            answer=list_answer_str,
            ground_truth=each_ground_truth_str
        )

        try:
            model_response = model_generation(task=prompt)
            model_response = model_response.replace("```json", "").replace("```", "").strip()
            print("prompt: ", prompt)
            print("model_response: ", model_response)
        except Exception as e:
            logging.warning(f"model_response failed initially: {e}")
            model_response = "你输出的json格式有误，输出已省略"

        tp, fp = attempt_extraction(
            generation_model=model_generation,
            original_prompt=prompt,
            generation_text=model_response,
        )
        if len(tp) != 0:
            print("tp[0]: ", type(tp[0]), tp[0])
        total_tp += [tp[0]] if len(tp) != 0 else []
        total_fp += fp

    if len(total_tp) != 0 and len(total_fp) != 0:
        return True, total_tp, total_fp
    else:
        return False, [], []


def main():
    print(answer_correctness_single_GT_eval(
        question="公司在报告期从事的主要业务是什么？"
    ))


if __name__ == "__main__":
    main()
