# -*- coding: utf-8 -*-
# Created on 2024/9/11

CORRECTNESS_INSTRUCTIONS = """\
Base on ground truth, an answer statements and you own knowledge, analyze each statement and classify them in one of the following categories:

- TP (true positive): statements that are present in answer that are also directly supported by the one or more statements in ground truth,
- FP (false positive): statements present in the answer but not directly supported by any statement in ground truth,

Each statement can only belong to one of the categories. Provide a reason for each classification.

# Example

## Example 1:
    "question": "What powers the sun and what is its primary function?"
    "answer":  [
        "The sun is powered by nuclear fission, similar to nuclear reactors on Earth.",
        "The primary function of the sun is to provide light to the solar system.",
    ],
    "ground_truth": [
                "The sun is powered by nuclear fusion, where hydrogen atoms fuse to form helium.",
                "This fusion process in the sun's core releases a tremendous amount of energy.",
                "The energy from the sun provides heat and light, which are essential for life on Earth.",
                "The sun's light plays a critical role in Earth's climate system.",
                "Sunlight helps to drive the weather and ocean currents.",
            ]
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": "The primary function of the sun is to provide light to the solar system.",
                    "reason": "This statement is somewhat supported by the ground truth mentioning the sun providing light and its roles, though it focuses more broadly on the sun's energy.",
                }}
            ],
            "FP": [
                {{
                    "statement": "The sun is powered by nuclear fission, similar to nuclear reactors on Earth.",
                    "reason": "This statement is incorrect and contradicts the ground truth which states that the sun is powered by nuclear fusion.",
                }}
            ]
        }}
    }}

## Example 2:
    "question": "What is the boiling point of water?",
    "answer": [
        "The boiling point of water is 100 degrees Celsius at sea level"
    ]
    "ground_truth": [
        "The boiling point of water is 100 degrees Celsius (212 degrees Fahrenheit) at sea level.",
        "The boiling point of water can change with altitude.",
    ]
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": "The boiling point of water is 100 degrees Celsius at sea level",
                    "reason": "This statement is directly supported by the ground truth which specifies the boiling point of water as 100 degrees Celsius at sea level.",
                }}
            ],
            "FP": []
        }}
    }}

# Input Data
    "question": {question}
    "answer": {answer}
    "ground_truth": {ground_truth}

# Response format
Return output as a well-formed JSON-formatted string with the following format:
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": <TP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_TP>
                }},
                {{
                    "statement": <TP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_TP>
                }}
            ],
            "FP": [
                {{
                    "statement": <FP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_FP>
                }},
                {{
                    "statement": <FP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_FP>
                }}
            ]
        }}
    }}

# Response rule
Please response in Chinese, Don't output anything else except for the json
"""

ZH_MULTI_CORRECTNESS_INSTRUCTIONS = """
基于正确答案<ground_truth>中的陈述，分析每个陈述并将其分类到以下类别之一：
- TP（真阳性）：答案<answer>中出现的陈述直接得到事实陈述<ground_truth>中的的一条或者多条**直接**支持，若无则为[]
- FP（假阳性）：答案<answer>中出现的陈述没有得到事实陈述<ground_truth>中任何陈述的**直接**支持，若无则为[]
每个答案陈述只能属于其中一个类别。请为每个分类提供理由。

# 判断规则：
- 答案<answer>中出现的陈述直接得到事实陈述<ground_truth>中的**直接**支持才算TP（真阳性），间接支持或推理后支持为FP（假阳性）

# 输入数据
    "answer": {answer}
    "ground_truth": {ground_truth}
    
# 输出规则
- TP: statement 需要是原始答案中的陈述
- FP: statement 可以使原始答案陈述中的摘要或核心要素， 不宜过长

# 输出格式
请以格式良好的 JSON 字符串形式返回，格式如下：
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": <TP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_TP>
                }},
                {{
                    "statement": <TP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_TP>
                }}
            ],
            "FP": [
                {{
                    "statement": <FP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_FP>
                }},
                {{
                    "statement": <FP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_FP>
                }}
            ]
        }}
    }}
# 响应规则
注意不要编造事实，根据正确答案<ground_truth>作为依据判断；不输出除 JSON 外的任何内容。
"""


ZH_SINGLE_CORRECTNESS_INSTRUCTIONS = """
基于正确答案<ground_truth>中的陈述，分析每个陈述并将其分类到以下类别之一：
- TP（真阳性）：答案<answer>中出现的陈述直接得到事实陈述<ground_truth>中的一条或者多条**直接**支持，若无则为[]
- FP（假阳性）：答案<answer>中出现的陈述没有得到事实陈述<ground_truth>中任何陈述的**直接**支持，若无则为[]
每个陈述只能属于其中一个类别。请为每个分类提供理由。

# 判断规则：
- 答案<answer>中出现的陈述直接得到事实陈述<ground_truth>中的**直接**支持才算TP（真阳性），间接支持或推理后支持为FP（假阳性）

# 输出规则
- TP: statement 需要是原始答案中的陈述
- FP: statement 可以使原始答案陈述中的摘要或核心要素， 不宜过长

# 输入数据
    "answer": {answer}
    "ground_truth": {ground_truth}

# 输出格式
请以格式良好的 JSON 字符串形式返回，格式如下：
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": <TP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_TP>
                }}
            ],
            "FP": [
                {{
                    "statement": <FP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_FP>
                }},
                {{
                    "statement": <FP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_FP>
                }}
            ]
        }}
    }}
# 响应规则
注意不要编造事实，根据正确答案<ground_truth>作为依据判断；不输出除 JSON 外的任何内容。
"""

ZH_GT_CORRECTNESS_INSTRUCTIONS = """
基于事实陈述、答案中的陈述以及你自身的知识，分析每个陈述并将其分类到以下类别之一：
- TP（真阳性）：答案<answer>中出现的陈述直接得到事实陈述<ground_truth>中一个或多个陈述的支持，
- FP（假阳性）：答案<answer>中出现的陈述没有得到事实陈述<ground_truth>中任何陈述的直接支持，
每个陈述只能属于其中一个类别。请为每个分类提供理由。

# 示例
## 示例 1：
    "answer":  [
        "太阳是通过核裂变供能的，类似于地球上的核反应堆。",
         "太阳的主要功能是为太阳系提供光。"
    ],
    "ground_truth": [
        "太阳通过核聚变供能，其中氢原子融合形成氦。",
        "太阳核心的这种聚变过程释放出大量能量。",
        "来自太阳的能量提供热量和光，对地球上的生命至关重要。",
        "太阳光在地球的气候系统中发挥着关键作用。",
        "阳光有助于驱动天气和海洋洋流。"
    ]
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": "太阳的主要功能是为太阳系提供光。",
                    "reason": "这一陈述在一定程度上得到了事实陈述的支持，尽管事实陈述更广泛地提到了太阳的能量。"
                }}
            ],
            "FP": [
                {{
                    "statement": "太阳是通过核裂变供能的，类似于地球上的核反应堆。",
                    "reason": "这一陈述是错误的，且与事实陈述中的核聚变相矛盾。"
                }}
            ]
        }}
    }}
## 示例 2：
    "answer": [
        "水在海平面的沸点是100摄氏度。"
    ]
    "ground_truth": [
        "水在海平面的沸点是100摄氏度（212华氏度）。",
        "水的沸点会随着海拔的变化而变化。"
    ]
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": "水在海平面的沸点是100摄氏度。",
                    "reason": "这一陈述得到了事实陈述的直接支持，事实陈述明确指出水在海平面的沸点是100摄氏度。"
                }}
            ],
            "FP": []
        }}
    }}

# 输入数据
    "answer": {answer}
    "ground_truth": {ground_truth}

# 输出格式
请以格式良好的 JSON 字符串形式返回，格式如下：
    {{
        "classification": {{
            "TP": [
                {{
                    "statement": <TP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_TP>
                }},
                {{
                    "statement": <TP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_TP>
                }}
            ],
            "FP": [
                {{
                    "statement": <FP_answer_statement_1>,
                    "reason": <reason_answer_statement_1_is_FP>
                }},
                {{
                    "statement": <FP_answer_statement_2>,
                    "reason": <reason_answer_statement_2_is_FP>
                }}
            ]
        }}
    }}
# 响应规则
请用中文回答，不输出除 JSON 外的任何内容。
"""


REGENERATION_PROMPT = """输出json格式可能有错误， 请根据json格式要求重新输出，注意不要输出json结果意外的其他内容
输出："""

