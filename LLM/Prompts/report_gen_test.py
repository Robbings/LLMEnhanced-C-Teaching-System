from langchain_core.prompts import ChatPromptTemplate

from LLM.llm_manager import get_llm_stream

report_template = """
# 🧾 测试用例分析报告模板

---

## 📌 一、测试用例概况

| 项目                     | 内容                                    |
|--------------------------|----------------------------------------|
| 测试目标明确性           | {{TestPurposeClarity}}                  |
| 用例设计完整性           |                                        |
| 正常输入覆盖             | ✅ / ❌                                 |
| 异常输入覆盖             | ✅ / ❌                                 |
| 边界条件覆盖             | ✅ / ❌                                 |
| 测试方法是否恰当         | {{TestingStrategy}}                     |

---

## 📊 二、测试覆盖性分析

| 覆盖类型               | 百分比 / 状态            |
|----------------------|-----------------------|
| 函数调用覆盖率         | {{FunctionCoverage}}%    |
| 逻辑分支覆盖率         | {{BranchCoverage}}%      |
| 边界条件覆盖           | {{BoundaryCoverage}}%    |
| 异常路径测试           | ✅ / ❌                  |

💡 **模型评语：**  
{{CoverageFeedback}}

---

## 🧪 三、测试用例质量分析

| 项目                     | 状态           |
|--------------------------|---------------|
| 输入输出描述清晰         | ✅ / ❌        |
| 命名规范，结构清晰       | ✅ / ❌        |
| 断言使用合理             | ✅ / ❌        |
| 存在冗余/缺漏用例       | {{RedundancyOrMiss}} |

💡 **模型评语：**  
{{TestQualityFeedback}}

---

## 🧯 四、执行结果与验证效果

| 项目                           | 内容                   |
|------------------------------|----------------------|
| 能否发现代码中存在的问题       | {{BugDetectability}}  |
| 是否存在误报/漏报             | {{FalsePositiveOrNegative}} |
| 测试输出日志清晰明了          | ✅ / ❌               |

💡 **模型评语：**  
{{ResultFeedback}}

---

## 🔧 五、问题与改进建议

| 问题编号 | 问题描述         | 建议修改方式        |
|----------|----------------|------------------|
| 1        | {{TestBug1}}   | {{TestFix1}}     |
| 2        | {{TestBug2}}   | {{TestFix2}}     |
| ...      | ...            | ...              |

---

## 📈 六、评分与等级

| 项目               | 得分         | 满分  |
|------------------|------------|------|
| 用例设计完整性       | {{Score1}}  | 25   |
| 覆盖率达成情况       | {{Score2}}  | 25   |
| 测试用例质量         | {{Score3}}  | 20   |
| 结果验证效果         | {{Score4}}  | 20   |
| 文档清晰度          | {{Score5}}  | 10   |
| **总分**           | {{Total}}   | 100  |

**等级评定：** A / B / C / D / F

---

## 📢 七、综合评语

{{FinalTestComment}}

"""

system_prompt_test_report = """
你是一个智能教学辅助系统，负责自动分析学生提交的测试用例、题目和代码，并生成标准化的测试用例分析报告。请根据模板中各部分的提示，严格按照以下 Markdown 模板中的格式，填写完整、专业、清晰的报告内容。

要求如下：

1. 分析测试目标是否明确，测试方法是否选择得当。
2. 判断用例设计是否完整，是否覆盖正常输入、异常输入、边界条件。
3. 评估测试覆盖率，包括函数、分支、边界、异常路径。
4. 分析测试用例质量，包括命名、结构、断言、输入输出描述是否清晰。
5. 检查执行结果能否有效发现代码问题，是否存在误报/漏报。
6. 列出具体存在的问题及改进建议。
7. 根据各项得分给出总分和等级评定。
8. 最后用自然语言写一段综合评语，保持客观、中立、鼓励性语言。
9. 模板中的 ✅/❌ 请选择其一并保留符号。

最终输出的内容应完整填充整个模板，不需要输出任何其他解释性文字。

----

以下是模板内容：

"""

user_prompt_test_report = """
请根据以下信息，生成一份完整的 Markdown 格式的 **测试用例分析报告**，内容要完整覆盖各部分，并结合题目、学生代码和测试用例进行深入分析。

---
### 📝 输入信息

- **题目描述：**
{question}

- **学生提交代码：**

```c
{code}
```

- **测试用例代码：**

```c
{test_code}
```

"""

test_report_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_test_report + report_template),
    ("user", user_prompt_test_report),
])

def test_report_node(state):
    """生成测试用例分析报告"""
    question = state["question"]
    code = state["code"]
    test_code = state["test_code"]

    # 将信息传递给模板
    return test_report_prompt_template.format(
        question=question,
        code=code,
        test_code=test_code
    )

def gen_test_report(state):
    """生成测试用例分析报告"""
    question = state["question"]
    code = state["code"]
    test_code = state["test_code"]

    # 将信息传递给模板
    prompt = test_report_prompt_template.format(
        question=question,
        code=code,
        test_code=test_code
    )

    llm = get_llm_stream()
    response = llm.invoke(prompt)
    return response.content

if __name__ == "__main__":
    # 测试用例
    test_state = {
        "question": "请实现一个函数，判断一个字符串是否为回文。",
        "code": "def is_palindrome(s):\n    return s == s[::-1]",
        "test_code": "def test_is_palindrome():\n    assert is_palindrome('racecar') == True\n    assert is_palindrome('hello') == False"
    }

    report = gen_test_report(test_state)
    print(report)
