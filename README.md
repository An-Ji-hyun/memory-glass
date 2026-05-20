# MemoryGlass

LLM 기반 심리상담 챗봇의 메모리 투명성이 사용자 신뢰·프라이버시 인식·관계 경험에 미치는 영향을 연구하는 시스템.

사용자가 챗봇 메모리를 통제할 수 있을 때(Condition A)와 없을 때(Condition B)의 경험 차이를 비교하는 파일럿 스터디용 프로토타입이다.

---

## 기술 스택

| 항목 | 사용 도구 |
|---|---|
| Language | Python 3.10+ |
| UI / 배포 | Streamlit + Streamlit Cloud |
| Memory | mem0 (클라우드 API) |
| LLM | OpenAI GPT-4o |
| 버전 관리 | Git + GitHub |
| 인증 방식 | URL 파라미터 (`?uid=P001&cond=A`) |

---

## 프로젝트 구조

```
memoryglass/
├── .streamlit/
│   └── secrets.toml      # API 키 (Git 제외, 직접 입력)
├── app.py                # 메인 앱
├── memory_engine.py      # mem0 연동 (저장·검색·삭제)
├── agent.py              # GPT-4o 응답 생성 + 메모리 미리보기 추출
├── ui_components.py      # Condition A 전용 UI 컴포넌트
├── logger.py             # 세션 이벤트 로그
├── requirements.txt
└── .gitignore
```

---

## 연구 설계

### 두 조건 (Between-subjects)

| | Condition A (Transparent) | Condition B (Opaque) |
|---|---|---|
| 메모리 저장 | 저장 전 사용자 승인 요청 | 자동 저장, 알리지 않음 |
| 메모리 조회 | 사이드바에서 목록 열람 가능 | 불가 |
| 메모리 삭제 | 항목별 삭제 가능 | 불가 |
| 자연어 명령 | "뭐 기억해?", "다 지워" 처리 | 불가 |

### 챗봇 용도

일상 고민·감정 대화 상대. 특정 주제 제한 없음.
공감적·비판단적 경청 우선, 진단·처방 금지.

---

## 로컬 실행

### 1. 패키지 설치

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. API 키 입력

`.streamlit/secrets.toml` 파일에 입력:

```toml
OPENAI_API_KEY = "sk-..."
MEM0_API_KEY   = "m0-..."
```

- OpenAI API 키: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- mem0 API 키: [app.mem0.ai](https://app.mem0.ai)

### 3. 실행

```powershell
streamlit run app.py
```

---

## 접속 URL

### (임시) 로컬

```
# Condition A (메모리 투명·통제 가능)
http://localhost:8501/?uid=P001&cond=A

# Condition B (메모리 자동·불투명)
http://localhost:8501/?uid=P007&cond=B

# 연구자 로그 확인
http://localhost:8501/?admin=true
```

### 배포 (Streamlit Cloud)

```
https://<앱이름>.streamlit.app/?uid=P001&cond=A
https://<앱이름>.streamlit.app/?uid=P007&cond=B
https://<앱이름>.streamlit.app/?admin=true
```

### 파라미터 규칙

| 파라미터 | 설명 |
|---|---|
| `uid` | 참가자 고유 ID (예: P001~P012). 없으면 `guest` |
| `cond` | `A` 또는 `B` (대소문자 무관). 없거나 잘못되면 `B` 기본값 |
| `admin` | `true`이면 연구자 로그 패널 표시 |

---

## 연구자 로그

`?admin=true` 접속 시 세션 내 이벤트 테이블과 CSV 다운로드 버튼을 제공.

기록되는 이벤트:

| event_type | 설명 |
|---|---|
| `session_start` | 세션 시작 |
| `message_sent` | 사용자 메시지 전송 |
| `memory_viewed` | 메모리 목록 조회 (Condition A) |
| `memory_approved` | 메모리 저장 승인 (Condition A) |
| `memory_rejected` | 메모리 저장 거부 (Condition A) |
| `memory_deleted` | 메모리 삭제 (Condition A) |
