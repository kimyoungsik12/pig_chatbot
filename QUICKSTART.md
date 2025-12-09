# Quick Start Guide

## 5분 안에 시작하기

### 1. 설치 (1분)

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 설정 (선택사항, 기본값 사용 가능)
cp .env.example .env
```

### 2. 초기화 (30초)

```bash
# Qdrant 컬렉션 생성
python main.py init
```

### 3. API 서버 실행 (10초)

```bash
python main.py api
```

브라우저에서 http://localhost:8000/docs 접속

### 4. 테스트 (1분)

#### 방법 1: 웹 UI에서 테스트

1. http://localhost:8000/docs 접속
2. `POST /query` 섹션 확장
3. "Try it out" 클릭
4. 질문 입력 후 "Execute"

#### 방법 2: CLI에서 테스트

새 터미널 열고:

```bash
python main.py query "돼지 사료에 대해 알려줘"
```

#### 방법 3: curl로 테스트

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "돼지 사료에 대해 알려줘"}'
```

## 첫 문서 추가하기

### API로 문서 추가

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "한국 양돈 산업은 2024년 기준으로... (긴 텍스트)",
    "title": "2024 양돈 산업 동향",
    "source": "테스트"
  }'
```

### Python 스크립트로 추가

```python
import requests

response = requests.post(
    "http://localhost:8000/ingest",
    json={
        "text": "긴 양돈 관련 텍스트...",
        "title": "문서 제목",
        "source": "출처"
    }
)
print(response.json())
```

## 다음 단계

### 1. 크롤러 설정

`crawler/example_scraper.py`를 복사하여 실제 사이트 크롤러 구현

### 2. 자동 업데이트 설정

```bash
# 매일 자동 크롤링
python main.py scheduler
```

### 3. 프롬프트 커스터마이징

`rag/chain.py`의 `QA_PROMPT_TEMPLATE` 수정

### 4. 프로덕션 배포

- Nginx 리버스 프록시 설정
- systemd 서비스 등록
- 로그 로테이션 설정

## 일반적인 문제 해결

### "Connection refused" 에러

vLLM 또는 Qdrant 서버 연결 확인:

```bash
# vLLM 확인
curl http://intflow.serveftp.com:17681/v1/models

# Qdrant 확인
curl http://intflow.serveftp.com:17663
```

### 임베딩 모델 다운로드 중

첫 실행 시 자동으로 다운로드됩니다. 기다려주세요.

### 검색 결과가 없음

벡터 DB에 문서가 없습니다. 문서를 먼저 추가하세요:

```bash
# 테스트 문서 추가
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text": "테스트 양돈 관련 긴 텍스트 (최소 100자 이상)...", "title": "테스트"}'
```
