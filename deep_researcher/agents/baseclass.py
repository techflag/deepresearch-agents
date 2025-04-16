from typing import Any, Callable, Optional
from agents import Agent, Runner, RunResult,set_tracing_disabled
from agents.run_context import TContext
set_tracing_disabled(True)

class ResearchAgent(Agent[TContext]):
    """
    这是 OpenAI Agent 类的自定义实现，支持为不支持结构化输出类型的模型进行输出解析。
    用户可以指定一个 output_parser 函数，该函数将使用代理的原始输出进行调用。
    这可以运行自定义逻辑，例如清理输出并将其转换为结构化的 JSON 对象。

    需要与 ResearchRunner 一起运行才能工作。
    """
    
    def __init__(
        self,
        *args,
        output_parser: Optional[Callable[[str], Any]] = None,
        **kwargs
    ):
        # output_parser是一个函数，仅在未指定output_type时生效
        self.output_parser = output_parser
        # 如果两者都指定，我们会引发错误 - 它们不能一起使用
        if self.output_parser and kwargs.get('output_type'):
            raise ValueError("不能同时指定output_parser和output_type")
            
        super().__init__(*args, **kwargs)


    async def parse_output(self, run_result: RunResult) -> RunResult:
        """
        通过将output_parser应用于其final_output（如果指定）来处理RunResult。
        这保留了RunResult结构，同时修改其内容。
        """
        if self.output_parser:
            raw_output = run_result.final_output            
            parsed_output = self.output_parser(raw_output)
            run_result.final_output = parsed_output            
        return run_result


class ResearchRunner(Runner):
    """
    OpenAI Runner类的自定义实现，支持为不支持带工具的结构化输出类型的模型进行输出解析。
    
    需要与ResearchAgent类一起运行。
    """
    
    @classmethod
    async def run(cls, *args, **kwargs) -> RunResult:
        """运行代理并在适用的情况下使用自定义解析器处理其输出"""
        # print(f"关键字参数 (kwargs): {kwargs}")
        # print(f"参数 (args): {args}")
        
        # 获取起始代理
        starting_agent = kwargs.get('starting_agent') or args[0]
   
        # 调用原始run方法
        result = await Runner.run(*args, **kwargs)
        
        # 如果起始代理是ResearchAgent类型，解析输出
        if isinstance(starting_agent, ResearchAgent):
            return await starting_agent.parse_output(result)
        
        return result