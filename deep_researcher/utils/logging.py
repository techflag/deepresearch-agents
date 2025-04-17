from typing import Optional, Dict
from .message_parser import MessageParser
from ..sse_manager import SSEManager
from dataclasses import dataclass
import os
from datetime import datetime  # 添加datetime导入
@dataclass
class TraceInfo:  # (1)!
    trace_id: str

async def log_message(message: str, trace_info:TraceInfo, additional_data: Optional[Dict] = None) -> None:
    """统一的消息日志记录函数
    
    Args:
        message: 要记录的消息
        trace_id: 客户端ID
        additional_data: 额外的数据字段
    """
    try:
        
        sse_data = MessageParser.format_sse_data(
            message, 
            trace_id=trace_info.trace_id,
            additional_data=additional_data
        )
        # 从data中获取时间戳并转换为可读格式
        timestamp = datetime.fromtimestamp(sse_data['data']['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        log_output = f"【执行日志】【{timestamp}】【{sse_data['event']}】: {sse_data['data']['message']}"
        print(log_output)
        
        # 同时写入测试日志文件
        test_log_path = os.path.join(os.path.dirname(__file__), "../../tests/logs/test_execution2.log")
        os.makedirs(os.path.dirname(test_log_path), exist_ok=True)
        with open(test_log_path, "a", encoding="utf-8") as f:
            f.write(f"{log_output}\n")
            
        await SSEManager.publish(
            trace_info.trace_id, 
            sse_data["event"], 
            sse_data["data"]
        )
            
    except UnicodeEncodeError:
        print(repr(message))
    except Exception as e:
        print(f"SSE发送失败: {str(e)}")