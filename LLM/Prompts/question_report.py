from langchain.chains.question_answering.map_reduce_prompt import system_template
from langchain_core.prompts import ChatPromptTemplate

from LLM.llm_manager import get_llm_stream

report_template= """
# 🧾 代码分析报告

## 📌 一、功能实现概述

- **输出正确性**：{{CorrectnessEvaluation}}
- **基本功能完成情况**：
  -  输入输出处理
  -  边界条件处理
  -  错误情况处理
  -  算法核心逻辑实现

------

## 🧠 二、代码结构分析

- **模块划分**：{{ModularityEvaluation}}
- **命名规范**：{{NamingStyleEvaluation}}
- **注释情况**：{{CommentingEvaluation}}
- **是否使用函数封装**：✅/❌
- **函数职责是否单一**：✅/❌

> 💡 **模型评语**：
>  {{StructureFeedback}}

------

## 🛠 三、算法与逻辑分析

- **所用算法类型**：{{AlgorithmType}}
- **时间复杂度估算**：{{TimeComplexity}}
- **空间复杂度估算**：{{SpaceComplexity}}
- **逻辑完整性**：{{LogicEvaluation}}

> 💡 **模型评语**：
>  {{AlgorithmFeedback}}

------

## 🧪 四、错误与改进建议

| 问题编号 | 问题描述 | 建议修改方式 |
| -------- | -------- | ------------ |
| 1        | {{Bug1}} | {{Fix1}}     |
| 2        | {{Bug2}} | {{Fix2}}     |
| ...      | ...      | ...          |



------

## 📊 五、评分与等级

| 项目           | 得分               | 满分    |
| -------------- | ------------------ | ------- |
| 功能实现       | {{Score1}}         | 30      |
| 代码规范       | {{Score2}}         | 20      |
| 算法与逻辑     | {{Score3}}         | 30      |
| 编码风格与注释 | {{Score4}}         | 10      |
| 错误处理       | {{Score5}}         | 10      |
| **总分**       | **{{TotalScore}}** | **100** |



- **等级评定**：A / B / C / D / F

------

## 📢 六、综合评语

> {{FinalComment}}

"""

system_prompt_question_report = """
你是一个智能教学辅助系统，负责自动分析学生提交的代码，并生成标准化的分析报告。请根据题目描述和学生代码，严格按照以下 Markdown 模板中的格式，填写完整、专业、清晰的报告内容。

要求如下：

1. 分析学生代码是否正确实现题目功能。
2. 判断代码的结构、命名、注释、可读性与封装性。
3. 推断其算法复杂度和逻辑合理性。
4. 给出针对性错误反馈和改进建议。
5. 用自然语言补全模板中各部分的内容，保持客观、中立、鼓励性语言。
6. 模板中的`✅/❌`请选择其一并保留符号。

最终输出的内容应完整填充整个模板，不需要输出任何其他解释性文字。

----

以下是模板内容：

"""

user_prompt_question_report = """
请根据以下题目描述和学生代码，生成一份完整的 Markdown 格式分析报告。

- 题目描述如下：
   {question}
- 学生提交的代码如下：

```c
{code}
```

请根据以上信息生成一份高质量的分析报告。
"""


question_report_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_question_report + report_template),
    ("user", user_prompt_question_report),
])

def question_report_node(state):
    """生成代码分析报告"""
    question = state["question"]
    code = state["code"]
    prompt = question_report_prompt_template.format_prompt(question=question, code=code)
    llm = get_llm_stream()
    response = llm.invoke(prompt)
    return {**state, "report": response.content}