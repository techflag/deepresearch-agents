from typing import Optional, Dict
from .message_parser import MessageParser
from ..sse_manager import SSEManager
from dataclasses import dataclass

@dataclass
class TraceInfo:  # (1)!
    trace_id: str

async def log_message(message: str, trace_info:TraceInfo, additional_data: Optional[Dict] = None) -> None:
    """统一的消息日志记录函数
    
    Args:
        message: 要记录的消息
        client_id: 客户端ID
        additional_data: 额外的数据字段
    """
    try:
        print(message)
        
        sse_data = MessageParser.format_sse_data(
            message, 
            client_id=trace_info.trace_id,
            additional_data=additional_data
        )
        await SSEManager.publish(
            trace_info.trace_id, 
            sse_data["event"], 
            sse_data["data"]
        )
            
    except UnicodeEncodeError:
        print(repr(message))
    except Exception as e:
        print(f"SSE发送失败: {str(e)}")