"""Agent 决策层 Prompt（T-001）。

注意：JSON 示例中的大括号使用 ``{{ }}`` 转义，以便后续用
``.format(query=..., context=...)`` 填充占位符时不会冲突。
"""

# MARKER: DECISION_PROMPT_START
DECISION_PROMPT = """你是一个智能体决策者。根据用户的问题和上下文，决定应该采取哪种行动路径。

可选路径：
1. simple_answer - 问题简单，可以直接回答
2. deep_reasoning - 问题复杂，需要检索和推理
3. clarify - 问题模糊，需要追问用户

用户问题：{query}
上下文：{context}

请输出JSON格式的决策结果：
{{
  "decision": "simple_answer | deep_reasoning | clarify",
  "reason": "决策理由",
  "confidence": 0.0-1.0
}}
"""
# MARKER: DECISION_PROMPT_END
