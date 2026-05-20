"""
agent.py — GPT-4o 응답 생성 및 메모리 미리보기 추출

generate_response: 저장된 메모리를 컨텍스트로 삼아 GPT-4o 응답 생성.
extract_memories_preview: 실제 저장 전 추출될 기억 목록을 미리 반환 (Condition A용).
"""

import json
import streamlit as st
from openai import OpenAI
from memory_engine import get_memories, format_memories_for_prompt

SYSTEM_PROMPT = """당신은 따뜻하고 공감적인 일상 대화 상대입니다.
사용자의 고민, 감정, 일상 이야기를 편하게 들어주세요.
- 판단하지 않고 공감하며 경청한다
- 사용자가 스스로 생각을 정리할 수 있도록 돕는다
- 조언보다 이해와 공감을 우선한다
- 자연스럽고 친근한 말투를 사용한다
- 절대 진단하거나 처방하지 않는다"""


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def generate_response(user_id: str, user_input: str, chat_history: list) -> str:
    """
    1. mem0에서 user_input과 관련된 메모리 검색
    2. 메모리를 시스템 프롬프트에 추가
    3. 최근 20개 대화 + 현재 입력으로 GPT-4o 호출
    """
    try:
        client = get_openai_client()

        memories = get_memories(user_id, query=user_input)
        memory_context = format_memories_for_prompt(memories)

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
        return f"응답을 생성하는 중 문제가 생겼어요. 잠시 후 다시 시도해주세요. ({e})"


def extract_memories_preview(user_id: str, messages: list) -> list:
    """
    Condition A 전용: 실제 저장 전 추출될 기억 목록을 미리 보여준다.
    최근 6개 메시지 기반, C-SSRS 관련 내용은 제외.
    """
    try:
        client = get_openai_client()

        recent = messages[-6:]
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in recent
        )

        prompt = f"""다음 대화에서 사용자에 대한 중요한 정보를 추출하세요.

추출 대상:
- 사실 정보 (직업, 나이, 가족관계 등)
- 선호/취향
- 현재 상황 (고민, 목표)
- 감정 상태

제외 대상:
- 자해/자살 관련 내용은 절대 포함하지 마세요

대화:
{conversation_text}

JSON으로만 출력하세요: {{"memories": ["기억1", "기억2"]}}
추출할 정보가 없으면: {{"memories": []}}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        parsed = json.loads(response.choices[0].message.content)
        return parsed.get("memories", [])

    except Exception:
        return []
