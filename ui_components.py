"""
ui_components.py — Condition A 전용 UI 컴포넌트

render_memory_approval : 저장 전 기억 항목별 승인/거부 UI
render_memory_panel    : 사이드바 메모리 목록 + 삭제 버튼
render_memory_chatcommand: 자연어 메모리 명령 처리
"""

import streamlit as st
from memory_engine import get_memories, delete_memory
from logger import log_event


def render_memory_approval(user_id: str, condition: str, pending_memories: list) -> list | None:
    """
    pending_memories 각 항목을 체크박스로 표시한다.
    체크박스는 rerun 후에도 상태가 유지되므로 선택 여부가 명확히 보인다.

    반환값:
        None  — 아직 확정 버튼을 누르지 않음 (대기 중)
        list  — 확정 버튼을 눌렀을 때 저장할 항목 목록 (빈 리스트 포함)
    """
    if not pending_memories:
        return None

    st.info("챗봇이 다음 내용을 기억하려 합니다. 저장할 항목을 선택 후 확정하세요.")

    checked = []
    for i, memory_text in enumerate(pending_memories):
        selected = st.checkbox(memory_text, value=True, key=f"mem_check_{i}")
        checked.append((memory_text, selected))

    st.write("")
    col_save, col_skip = st.columns([2, 1])

    if col_save.button("선택 항목 저장하기", type="primary", key="confirm_save"):
        approved = [text for text, sel in checked if sel]
        rejected = [text for text, sel in checked if not sel]

        for m in approved:
            log_event(user_id, condition, "memory_approved", {"memory": m})
        for m in rejected:
            log_event(user_id, condition, "memory_rejected", {"memory": m})

        if approved:
            st.success(f"{len(approved)}개 항목을 저장했어요.")
        else:
            st.info("저장된 항목이 없어요.")
        return approved

    if col_skip.button("모두 건너뛰기", key="skip_all"):
        for text, _ in checked:
            log_event(user_id, condition, "memory_rejected", {"memory": text})
        st.info("모든 항목을 건너뛰었어요.")
        return []

    return None  # 아직 확정 전


def render_memory_panel(user_id: str, condition: str):
    """사이드바에 현재 저장된 메모리 목록을 표시하고 개별 삭제를 허용한다."""
    with st.sidebar:
        st.subheader("내 기억 목록")
        st.caption(f"uid: `{user_id}`")

        if st.button("새로고침", key="refresh_memories"):
            log_event(user_id, condition, "memory_viewed")
            st.rerun()

        memories = get_memories(user_id)

        # with st.expander("🔍 디버그 (raw)", expanded=False):
        #     from memory_engine import get_mem0_client
        #     try:
        #         raw = get_mem0_client().get_all(filters={"user_id": user_id})
        #         st.write(raw)
        #     except Exception as e:
        #         st.error(e)

        if not memories:
            st.caption("아직 저장된 기억이 없어요.")
            return

        for mem in memories:
            col_text, col_del = st.columns([5, 1])
            col_text.write(f"• {mem.get('memory', '')}")

            if col_del.button("🗑", key=f"del_{mem.get('id', '')}"):
                if delete_memory(mem["id"]):
                    log_event(user_id, condition, "memory_deleted",
                              {"memory": mem.get("memory", "")})
                    st.rerun()

        st.caption(f"총 {len(memories)}개의 기억")


def render_memory_chatcommand(user_input: str, user_id: str, condition: str) -> bool:
    """
    자연어 메모리 명령을 처리한다.
    처리했으면 True, 일반 대화면 False 반환.
    """
    view_keywords  = ["뭐 기억해", "뭐 알아", "기억 보여", "내 정보", "기억 목록"]
    clear_keywords = ["다 지워", "전부 지워", "기억 삭제", "전부 삭제", "모두 지워"]

    lowered = user_input.strip()

    if any(kw in lowered for kw in view_keywords):
        memories = get_memories(user_id)
        if memories:
            items = "\n".join(f"• {m.get('memory', '')}" for m in memories)
            st.info(f"현재 기억하고 있는 내용이에요:\n\n{items}")
        else:
            st.info("아직 기억하고 있는 내용이 없어요.")
        log_event(user_id, condition, "memory_viewed")
        return True

    if any(kw in lowered for kw in clear_keywords):
        memories = get_memories(user_id)
        for mem in memories:
            delete_memory(mem["id"])
        log_event(user_id, condition, "memory_deleted", {"scope": "all"})
        st.success("모든 기억을 삭제했어요.")
        return True

    return False
