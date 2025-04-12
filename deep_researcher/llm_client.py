import os
from typing import Union
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, OpenAIResponsesModel, set_tracing_export_api_key, set_tracing_disabled
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
LOCAL_MODEL_URL = os.getenv("LOCAL_MODEL_URL")  # 例如 "http://localhost:11434/v1"

REASONING_MODEL_PROVIDER=os.getenv("REASONING_MODEL_PROVIDER", "openai")
REASONING_MODEL=os.getenv("REASONING_MODEL", "o3-mini")
MAIN_MODEL_PROVIDER=os.getenv("MAIN_MODEL_PROVIDER", "openai")
MAIN_MODEL=os.getenv("MAIN_MODEL", "gpt-4o")
FAST_MODEL_PROVIDER=os.getenv("FAST_MODEL_PROVIDER", "openai")
FAST_MODEL=os.getenv("FAST_MODEL", "gpt-4o-mini")

supported_providers = ["openai", "deepseek", "openrouter", "gemini", "anthropic", "perplexity", "huggingface", "local"]

provider_mapping = {
    "openai": {
        "model": OpenAIResponsesModel,
        "base_url": None,
        "api_key": OPENAI_API_KEY,
    },
    "deepseek": {
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://api.deepseek.com/v1",
        "api_key": DEEPSEEK_API_KEY,
    },
    "openrouter": {
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
    },
    "gemini": {
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": GEMINI_API_KEY,
    },
    "anthropic": {
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://api.anthropic.com/v1/",
        "api_key": ANTHROPIC_API_KEY,
    },
    "perplexity": {
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://api.perplexity.ai/chat/completions",
        "api_key": PERPLEXITY_API_KEY,
    },
    "huggingface": {
        "model": OpenAIChatCompletionsModel,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": HUGGINGFACE_API_KEY,
    },
    "local": {
        "model": OpenAIChatCompletionsModel,
        "base_url": LOCAL_MODEL_URL,
        "api_key": "ollama",  # OpenAI客户端需要但不使用
    }
}

if REASONING_MODEL_PROVIDER not in supported_providers:
    raise ValueError(f"无效的模型提供商: {REASONING_MODEL_PROVIDER}")
if MAIN_MODEL_PROVIDER not in supported_providers:
    raise ValueError(f"无效的模型提供商: {MAIN_MODEL_PROVIDER}")
if FAST_MODEL_PROVIDER not in supported_providers:
    raise ValueError(f"无效的模型提供商: {FAST_MODEL_PROVIDER}")

if OPENAI_API_KEY:
    set_tracing_export_api_key(OPENAI_API_KEY)
else:
    # 如果没有提供OpenAI API密钥，禁用跟踪
    set_tracing_disabled(True)

# ------- 设置推理模型 -------

reasoning_client = AsyncOpenAI(
    api_key=provider_mapping[REASONING_MODEL_PROVIDER]["api_key"],
    base_url=provider_mapping[REASONING_MODEL_PROVIDER]["base_url"],
)

reasoning_model = provider_mapping[REASONING_MODEL_PROVIDER]["model"](
    model=REASONING_MODEL,
    openai_client=reasoning_client
)

# ------- 设置主模型 -------

main_client = AsyncOpenAI(
    api_key=provider_mapping[MAIN_MODEL_PROVIDER]["api_key"],
    base_url=provider_mapping[MAIN_MODEL_PROVIDER]["base_url"],
)

main_model = provider_mapping[MAIN_MODEL_PROVIDER]["model"](
    model=MAIN_MODEL,
    openai_client=main_client
)

# ------- 设置快速模型 -------

fast_client = AsyncOpenAI(
    api_key=provider_mapping[FAST_MODEL_PROVIDER]["api_key"],
    base_url=provider_mapping[FAST_MODEL_PROVIDER]["base_url"],
)

fast_model = provider_mapping[FAST_MODEL_PROVIDER]["model"](
    model=FAST_MODEL,
    openai_client=fast_client
)


def get_base_url(model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel]) -> str:
    """获取给定模型的基础URL的实用函数"""
    return str(model._client._base_url)


def model_supports_structured_output(model: Union[OpenAIChatCompletionsModel, OpenAIResponsesModel]) -> bool:
    """检查模型是否支持结构化输出的实用函数"""
    structured_output_providers = ["openai.com", "anthropic.com"]
    return any(provider in get_base_url(model) for provider in structured_output_providers)


__all__ = ["reasoning_model", "main_model", "fast_model", "get_base_url", "model_supports_structured_output"]
