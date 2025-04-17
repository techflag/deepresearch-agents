from typing import Dict, Tuple, Optional
import time
import re

class MessageParser:
    """消息解析器，用于处理结构化消息"""
    
    # 定义所有支持的消息类型
    MESSAGE_TYPES = {
        # 研究计划相关
        "plan-start": "<plan-start>",
        "plan-section": "<plan-section>",
        "plan-end": "<plan-end>",
        
        # 研究过程相关
        "iteration": "<iteration>",
        "iteration-flow": "<iteration-flow>",  # 添加这行
        "research-start": "<research-start>",
        "research-end": "<research-end>",
        "research-result": "<research-result>",
        "processing": "<processing>",
        "agent-select": "<agent-select>",
        
        # 评估差距相关
        "evaluate_gaps": "<evaluate_gaps>",
        
        # 报告生成相关
        "report-create": "<report-create>",
        "report-draft": "<report-draft>",
        "report-finish": "<report-finish>",
        
        # 工具相关
        "search": "<search>",
        "search-filter": "<search-filter>",
        "search-result": "<search-result>",
        "scrape": "<scrape>",
        
        # 函数工具相关
        "function_tool_web_search": "<function_tool_web_search>",
        "function_tool_client": "<function_tool_client>",
        "web_search_error": "<web_search_error>",
        "research_runner_kwargs": "<research_runner_kwargs>",  # 添加 ResearchRunner 关键字参数类型
        
        # 其他类型
        "error": "<error>",
        "task": "<task>",
        "action": "<action>",
        "findings": "<findings>",
        "thought": "<thought>"
    }

    @classmethod
    def parse(cls, message: str) -> Tuple[str, str]:
        """解析消息，返回消息类型和内容"""
        for event_type, tag in cls.MESSAGE_TYPES.items():
            pattern = f"{tag}(.*?)</{tag[1:]}"
            match = re.search(pattern, message, re.DOTALL)
            if match:
                return event_type, match.group(1).strip()
        
        return "info", message

    @classmethod
    def format_sse_data(cls, 
                       message: str, 
                       trace_id: str = "default", 
                       additional_data: Optional[Dict] = None) -> Dict:
        """
        格式化SSE消息数据
        
        Args:
            message: 原始消息
            trace_id: 客户端ID
            additional_data: 额外的数据字段
            
        Returns:
            dict: 格式化后的消息数据
        """
        event_type, content = cls.parse(message)
        
        data = {
            "message": content,
            "timestamp": time.time(),
            "raw_message": message,
            "trace_id": trace_id
        }
        
        if additional_data:
            data.update(additional_data)
            
        return {
            "event": event_type,
            "data": data
        }