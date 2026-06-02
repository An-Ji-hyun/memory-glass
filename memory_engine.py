"""
memory_engine.py — mem0 클라우드 API 연동

대화 종료 후 전체 대화를 1회 저장하고, 이후 사용자가 CRUD 가능.
mem0는 영어로 메모리를 추출하므로, 화면 표시 시 한국어로 번역한다.
"""

import json
import streamlit as st
from mem0 import MemoryClient
from openai import OpenAI


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


def _translate_to_korean(texts: list) -> list:
    """영어 텍스트 목록을 한국어로 일괄 번역. 실패 시 원본 반환."""
    if not texts:
        return texts
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content":
                f"다음 문장들을 자연스러운 한국어로 번역하세요. 번호와 함께 그대로 출력하세요:\n\n{numbered}"}],
            temperature=0
        )
        lines = [l.strip() for l in response.choices[0].message.content.strip().split("\n") if l.strip()]
        translated = []
        for line in lines:
            if ". " in line:
                translated.append(line.split(". ", 1)[1].strip())
            else:
                translated.append(line)
        return translated if len(translated) == len(texts) else texts
    except Exception:
        return texts


def get_all_memories_korean(user_id: str) -> list:
    """전체 메모리를 한국어로 번역하여 반환. 화면 표시 전용."""
    memories = get_all_memories(user_id)
    if not memories:
        return []
    texts = [m.get("memory", "") for m in memories]
    translated = _translate_to_korean(texts)
    return [{**m, "memory": t} for m, t in zip(memories, translated)]


def cluster_memories_with_sources(memories: list, chat_history: list) -> list:
    """
    메모리를 토픽별로 클러스터링하고 한국어 번역 + 원본 발화를 매칭.
    반환: [{"label": "토픽명", "items": [{"id", "text"(한국어), "source"}], "count": N}]
    """
    if not memories:
        return []
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        mem_lines  = "\n".join(f"{i+1}. {m.get('memory','')}" for i, m in enumerate(memories))
        user_lines = "\n".join(f"- {m['content']}" for m in chat_history if m["role"] == "user")

        prompt = f"""대화에서 추출된 메모리 목록과 원본 사용자 발화입니다.

[메모리 목록]
{mem_lines}

[원본 사용자 발화]
{user_lines}

다음 작업을 수행하세요:
1. **사용자 본인에 관한 정보만 남기고** 어시스턴트의 추천/제안 내용은 제외하세요
2. 남은 메모리를 2~5개의 의미적 토픽으로 분류하세요 (토픽이 다양하게 분리되도록)
3. 각 토픽에 간결한 한국어 이름 부여 (예: "여행 선호도", "인간관계", "취미/관심사", "일상/고민")
4. 각 메모리를 "사용자는 ~" 형식의 자연스러운 한국어로 번역
5. 각 메모리와 가장 관련된 원본 발화를 찾아 그대로 인용 (없으면 빈 문자열)

포함 대상: 사용자의 선호, 경험, 계획, 감정, 관심사, 인간관계
제외 대상: 어시스턴트가 추천하거나 제안한 내용

JSON으로만 출력:
{{
  "topics": [
    {{
      "label": "토픽 이름",
      "items": [
        {{
          "index": 1,
          "korean": "사용자는 ~",
          "source": "관련 원본 발화"
        }}
      ]
    }}
  ]
}}"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        parsed = json.loads(response.choices[0].message.content)
        result  = []
        for topic in parsed.get("topics", []):
            items = []
            for item in topic.get("items", []):
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(memories):
                    items.append({
                        "id":     memories[idx].get("id", ""),
                        "text":   item.get("korean", memories[idx].get("memory", "")),
                        "source": item.get("source", ""),
                    })
            if items:
                result.append({
                    "label": topic.get("label", "기타"),
                    "items": items,
                    "count": len(items),
                })
        return result

    except Exception:
        return [{
            "label": "전체",
            "items": [{"id": m.get("id",""), "text": m.get("memory",""), "source": ""} for m in memories],
            "count": len(memories),
        }]


def format_for_prompt(memories: list) -> str:
    if not memories:
        return ""
    lines = [m.get("memory", str(m)) for m in memories if m]
    if not lines:
        return ""
    return "[사용자에 대해 기억하는 정보]\n" + "\n".join(f"- {l}" for l in lines)
