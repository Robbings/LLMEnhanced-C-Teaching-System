from LLM.Task_Decomposition import task_decomposition
from LLM.Func_Code_Generation import code_generation
from LLM.Unit_Test_Generation import test_generation

model_backend_mapping = {
    "task": task_decomposition,
    "gpt-4o": task_decomposition,
    "gpt-4o-mini": code_generation,
    "gpt-4":test_generation,
}