"""
memory_engine.py — mem0 클라우드 API 연동

mem0 클라우드에 사용자 메모리를 저장·검색·삭제한다.
MemoryClient(클라우드 버전)를 사용하며, Memory(로컬 버전)와 다르다.
"""

import streamlit as st
from mem0 import MemoryClient


def get_mem0_client() -> MemoryClient:
    return MemoryClient(api_key=st.secrets["MEM0_API_KEY"])


def add_memory(user_id: str, messages: list) -> list:
    """
    대화 메시지 목록에서 기억을 추출해 mem0에 저장한다.
    messages: [{"role": "user", "content": "..."}, ...]
    반환: 저장된 메모리 목록
    """
    try:
        client = get_mem0_client()
        result = client.add(messages, user_id=user_id)
        if isinstance(result, dict):
            return result.get("results", [])
        return result if isinstance(result, list) else []
    except Exception as e:
        st.warning(f"메모리 저장 중 오류: {e}")
        return []


def get_memories(user_id: str, query: str = None) -> list:
    """
    query 있으면 관련 메모리 검색, 없으면 전체 반환.
    반환: [{"id": "...", "memory": "...", ...}, ...]

    search()와 get_all() 모두 {"results": [...]} 형태의 dict를 반환한다.
    """
    try:
        client = get_mem0_client()
        if query:
            result = client.search(query, user_id=user_id)
        else:
            result = client.get_all(user_id=user_id)

        if isinstance(result, dict):
            return result.get("results", [])
        return result if isinstance(result, list) else []
    except Exception:
        return []


def delete_memory(memory_id: str) -> bool:
    try:
        client = get_mem0_client()
        client.delete(memory_id)
        return True
    except Exception:
        return False


def format_memories_for_prompt(memories: list) -> str:
    """메모리 목록을 시스템 프롬프트 삽입용 문자열로 변환."""
    if not memories:
        return ""
    lines = [m.get("memory", str(m)) for m in memories if m]
    if not lines:
        return ""
    return "[사용자에 대해 알고 있는 정보]\n" + "\n".join(f"- {l}" for l in lines)
