"""
memory_engine.py — mem0 클라우드 API 연동

대화 종료 후 전체 대화를 1회 저장하고, 이후 사용자가 CRUD 가능.
"""

import streamlit as st
from mem0 import MemoryClient


def get_client() -> MemoryClient:
    return MemoryClient(api_key=st.secrets["MEM0_API_KEY"])


def save_conversation(user_id: str, messages: list) -> list:
    """
    패널 열릴 때 1회만 호출. conversation_saved 플래그로 중복 방지.
    messages: [{"role": "user"/"assistant", "content": "..."}]
    반환: 추출된 메모리 목록, 실패 시 []
    """
    try:
        client = get_client()
        result = client.add(messages, user_id=user_id)
        if isinstance(result, dict):
            return result.get("results", [])
        return result if isinstance(result, list) else []
    except Exception as e:
        st.warning(f"메모리 저장 중 오류: {e}")
        return []


def get_all_memories(user_id: str) -> list:
    """전체 메모리 반환. 각 항목: {"id": "...", "memory": "..."}"""
    try:
        client = get_client()
        result = client.get_all(filters={"user_id": user_id})
        if isinstance(result, dict):
            return result.get("results", [])
        return result if isinstance(result, list) else []
    except Exception:
        return []


def delete_memory(memory_id: str) -> bool:
    try:
        client = get_client()
        client.delete(memory_id)
        return True
    except Exception:
        return False


def update_memory(memory_id: str, new_text: str) -> bool:
    try:
        client = get_client()
        client.update(memory_id, data=new_text)
        return True
    except Exception:
        return False


def add_manual_memory(user_id: str, text: str) -> bool:
    try:
        client = get_client()
        client.add([{"role": "user", "content": text}], user_id=user_id)
        return True
    except Exception:
        return False


def format_for_prompt(memories: list) -> str:
    if not memories:
        return ""
    lines = [m.get("memory", str(m)) for m in memories if m]
    if not lines:
        return ""
    return "[사용자에 대해 기억하는 정보]\n" + "\n".join(f"- {l}" for l in lines)
