from langchain_core.prompts import ChatPromptTemplate

from LLM.llm_manager import get_long_text_llm_stream

report_template = """
# 🧾 阶段学习总结报告

## 🧠 一、知识掌握与能力分析

| 知识点                  | 掌握情况   | 点评与指导 |
| ----------------------- | ---------- | ---------- |
| 变量与数据类型          | {{Level1}} | {{Note1}}  |
| 条件与循环结构          | {{Level2}} | {{Note2}}  |
| 函数封装与调用          | {{Level3}} | {{Note3}}  |
| 字符串/数组处理         | {{Level4}} | {{Note4}}  |
| 指针/结构体（如已涉及） | {{Level5}} | {{Note5}}  |



- 掌握等级示例：✅熟练 / ⚠️部分掌握 / ❌尚不熟练
- 这里的知识点不是固定的，而是根据学生的提交分析学生最近的作业中涉及到了哪些知识点

------

## 📈 二、编程技能发展轨迹

- **代码规范变化趋势**：
  - 命名规范演进分析：xxx
  - 注释覆盖率演进分析：xxx
  - xxx：xxx
- **结构与封装能力变化**：
  - 函数封装程度分析：xxx
  - xxx：xxx
- **调试与测试能力演进**：
  - xxx：xxx



> 说明：代码规范部分请描述学生在命名规范、代码排版、注释习惯等方面的变化。例如是否从杂乱无章过渡到统一风格，是否逐步掌握有意义的变量命名，是否注释更具说明性等。结构与封装部分请描述学生在模块化编程、函数划分、单一职责原则等方面的进步。调试与测试能力部分请描述学生在错误定位、主动测试、单元测试思维等方面的表现。
> 每一个部分的细分小点你需要根据学生的学习情况进行分析和编写，学生训练了哪些知识，你就输出哪些小点，保持与模板的格式一致即可。

------

## ❗ 三、常见错误与问题模式分析

| 错误类型             | 出现次数 | 错误率  | 建议改善措施    |
| -------------------- | -------- | ------- | --------------- |
| 语法错误（如漏分号） | {{E1}}   | {{ER1}} | {{Suggestion1}} |
| 条件判断错误         | {{E2}}   | {{ER2}} | {{Suggestion2}} |
| 循环逻辑错误         | {{E3}}   | {{ER3}} | {{Suggestion3}} |
| 边界条件未考虑       | {{E4}}   | {{ER4}} | {{Suggestion4}} |
| 异常输入未处理       | {{E5}}   | {{ER5}} | {{Suggestion5}} |

------

## 📊 四、阶段性评分与等级评定

| 维度                     | 得分          | 满分    |
| ------------------------ | ------------- | ------- |
| 基础语法掌握             | {{Score1}}    | 20      |
| 代码质量与规范           | {{Score2}}    | 20      |
| 测试设计与执行能力       | {{Score3}}    | 20      |
| 逻辑思维与问题解决能力   | {{Score4}}    | 20      |
| 学习积极性与自我提升情况 | {{Score5}}    | 20      |
| **总分**                 | **{{Total}}** | **100** |



- **等级评定**：A / B / C / D / F

------

## 📢 五、模型综合评语

> {{AIComment}}
>
> 示例：你在函数调用与封装方面已有明显进步，但测试用例设计仍较薄弱，建议下一阶段主动练习异常输入与边界条件的测试。同时，可尝试更规范地添加注释，提升代码可读性。

"""

system_prompt_question_report = """
你是一个教学数据分析专家，负责根据C语言程序设计学生每次作业提交的各种数据，总结并生成标准化的阶段性学习总结报告。请严格按照以下 Markdown 模板中的格式，填写完整、专业、清晰的报告内容。

最终输出的内容应完整填充整个模板，不需要输出任何其他解释性文字。

----

以下是模板内容：

"""

user_prompt_question_report = """
请根据以下学生提交的代码等数据，生成一份完整的 Markdown 格式阶段性学习总结报告。

历次数据整理如下：

{{reports}}

"""

stage_report_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_question_report + report_template),
    ("user", user_prompt_question_report),
])

def gen_stage_report(input_str):
    """
    生成阶段性学习总结报告
    :param input_str: 包含学生提交的代码等
    :return: 完整的阶段性学习总结报告
    """
    reports = input_str
    prompt = stage_report_prompt_template.format(reports=reports)
    llm = get_long_text_llm_stream()
    response = llm.invoke(prompt)
    return response.content
