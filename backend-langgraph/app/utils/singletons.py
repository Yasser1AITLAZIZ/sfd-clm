"""Singleton utilities for LLM builder and graph"""
from __future__ import annotations
from functools import lru_cache
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import MemorySaver
from app.config.llm_builder import LLMBuilderFactory


@lru_cache(maxsize=1)
def get_llm_builder():
    """Get LLM builder singleton"""
    # Default to OpenAI, but will use config
    return LLMBuilderFactory.create_builder("openai")


@lru_cache(maxsize=1)
def get_checkpointer() -> MemorySaver:
    """Get checkpointer singleton"""
    return MemorySaver()


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Get compiled graph singleton"""
    from app.graph import create_async_graph
    return create_async_graph().compile(
        checkpointer=get_checkpointer()
    )

