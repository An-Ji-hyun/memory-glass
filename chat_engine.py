"""
chat_engine.py — GPT-4o 응답 생성

저장된 전체 메모리를 시스템 프롬프트에 삽입하여 응답 생성.
패널 열리기 전에는 메모리가 없으므로 기본 프롬프트로만 동작.
"""

import streamlit as st
from openai import OpenAI
from memory_engine import get_all_memories, format_for_prompt

SYSTEM_PROMPT = """당신은 따뜻하고 공감적인 대화 상대입니다.
사용자의 이야기를 들으면서 자연스럽게 더 알아가도록 대화하세요.

원칙:
- 사용자 말을 먼저 공감한 후 질문
- 한 번에 질문 하나만
- 구체적인 상황, 감정, 이유, 배경을 자연스럽게 파악
- 인터뷰가 아닌 대화처럼 진행
- 절대 진단하거나 조언하지 않음"""


def get_client() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def generate_response(user_id: str, user_input: str, chat_history: list) -> str:
    """
    1. get_all_memories(user_id)로 메모리 가져오기 (패널 전이면 빈 리스트)
    2. format_for_prompt()로 시스템 프롬프트에 추가
    3. chat_history 최근 20개 + 현재 user_input으로 GPT-4o 호출
    """
    try:
        client = get_client()

        memories = get_all_memories(user_id)
        memory_context = format_for_prompt(memories)

        system = SYSTEM_PROMPT
        if memory_context:
            system += f"\n\n{memory_context}"

        messages = [{"role": "system", "content": system}]
        messages += chat_history[-20:]
        messages.append({"role": "user", "content": user_input})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"죄송해요, 잠시 후 다시 시도해주세요. ({e})"
