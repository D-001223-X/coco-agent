"""Agent ReAct 循环 Prompt（T-001）。

注意：JSON 示例中的大括号使用 ``{{ }}`` 转义，以便后续用
``.format(tools=..., query=..., context=...)`` 填充占位符时不会冲突。
"""

# MARKER: REACT_PROMPT_START
REACT_PROMPT = """你是一个智能体，通过思考-行动-观察循环完成任务。

可用工具：{tools}

用户问题：{query}
对话历史：{context}

请按以下格式输出：
Thought: 你的思考
Action: 工具名称
Action Input: 工具参数

如果你已经可以回答用户问题，输出：
Thought: 我可以回答用户了
Final Answer: 最终答案
"""
# MARKER: REACT_PROMPT_END
