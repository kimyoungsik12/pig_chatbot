# 한국 양돈 전문 RAG LLM 시스템

LangChain + vLLM + Qdrant 기반의 한국 양돈 산업 전문 지식 검색 시스템

## 시스템 아키텍처

```
[크롤러] → [텍스트 처리] → [Qdrant 벡터 DB] → [RAG 체인] → [FastAPI]
                                    ↓
                            [vLLM Qwen 모델]
```

## 주요 기능

- ✅ **LangChain 기반 RAG**: 확장 가능한 검색 증강 생성 시스템
- ✅ **vLLM 통합**: 로컬 Qwen/Qwen2.5-14B-Instruct 모델 사용
- ✅ **Qdrant 벡터 스토어**: 효율적인 유사도 검색
- ✅ **플러그인 크롤러**: 사이트별 맞춤 크롤러 추가 가능
- ✅ **자동 스케줄링**: 매일 자동 데이터 업데이트
- ✅ **FastAPI 서버**: REST API 제공
- ✅ **한국어 최적화**: 한국어 텍스트 처리 및 프롬프트

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 설정 (.env)

```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env

# .env 파일에서 주요 설정을 자신의 환경에 맞게 수정
# (vLLM, Qdrant, API 포트, 크롤러 설정 등)
```

### 3. Qdrant 컬렉션 초기화

```bash
python main.py init
```

## 사용법

### 1. API 서버 실행

```bash
python main.py api
```

서버 실행 후: http://localhost:8000/docs 에서 API 문서 확인

### 2. 질의 테스트

```bash
python main.py query "ASF 예방을 위한 차단방역 지침은?"
```

### 3. 크롤러 실행 (1회)

```bash
python main.py crawl
```

### 4. 스케줄러 실행 (매일 자동)

```bash
python main.py scheduler
```

매일 새벽 3시에 자동으로 크롤링 및 업데이트 (config에서 시간 변경 가능)

## API 사용 예시

### 질의 (Query)

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "돼지 사료 배합비에 대해 알려줘"}'
```

### 문서 추가 (Manual Ingestion)

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "양돈 관련 긴 텍스트 내용...",
    "title": "문서 제목",
    "source": "수동 입력"
  }'
```

### 헬스 체크

```bash
curl http://localhost:8000/health
```

## 커스텀 크롤러 추가

### 1. 새 크롤러 파일 생성

```bash
cp crawler/example_scraper.py crawler/kppa_scraper.py
```

### 2. 크롤러 구현

```python
# crawler/kppa_scraper.py
from crawler.base_crawler import BaseCrawler, CrawledDocument

class KppaScraper(BaseCrawler):
    BASE_URL = "https://www.koreapork.or.kr"

    def __init__(self):
        super().__init__(name="한국양돈협회")

    def get_article_urls(self) -> List[str]:
        # 사이트 구조에 맞게 구현
        pass

    def parse_article(self, url: str) -> Optional[CrawledDocument]:
        # 사이트 구조에 맞게 구현
        pass
```

### 3. 스케줄러에 등록

```python
# main.py의 run_scheduler_mode() 함수 수정
from crawler.kppa_scraper import KppaScraper

crawlers = [
    KppaScraper(),  # 새 크롤러 추가
    # ExampleScraper(),
]
```

## 프로젝트 구조

```
pig-farming-llm/
├── config.py                 # 설정 관리
├── main.py                   # CLI 진입점
├── requirements.txt          # 의존성
├── .env.example             # 환경변수 예시
│
├── core/                    # 핵심 컴포넌트
│   ├── embeddings.py        # 한국어 임베딩 모델
│   ├── llm.py              # vLLM LangChain 통합
│   └── vectorstore.py      # Qdrant 연동
│
├── rag/                     # RAG 체인
│   └── chain.py            # QA 체인 구현
│
├── crawler/                 # 크롤러
│   ├── base_crawler.py     # 추상 베이스 클래스
│   └── example_scraper.py  # 예시 스크래퍼 (복사하여 사용)
│
├── pipeline/                # 데이터 파이프라인
│   ├── text_processor.py   # 텍스트 청킹
│   └── ingestion.py        # 벡터 DB 저장
│
├── api/                     # FastAPI 서버
│   └── server.py
│
└── scheduler/               # 스케줄러
    └── daily_crawler.py
```

## 설정 커스터마이징

### .env에서 설정 가능

- vLLM: `VLLM_BASE_URL`, `VLLM_MODEL_NAME`, `VLLM_TEMPERATURE`, `VLLM_MAX_TOKENS`
- Qdrant: `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION_NAME`, `QDRANT_VECTOR_SIZE`
- 임베딩: `EMBEDDING_MODEL_NAME`, `EMBEDDING_DEVICE`
- 텍스트 청킹: `CHUNK_SIZE`, `CHUNK_OVERLAP`
- RAG 검색: `RETRIEVAL_TOP_K`, `RETRIEVAL_SCORE_THRESHOLD`
- API: `API_HOST`, `API_PORT` (UI는 `/chat`)
- 크롤러: `CRAWLER_SCHEDULE_TIME`, `CRAWLER_USER_AGENT`, `CRAWLER_TIMEOUT`, `CRAWLER_MAX_RETRIES`
- 로깅: `LOG_LEVEL`, `LOG_FILE`

> 이미지 OCR 사용 시 `pytesseract`, `pillow`가 필요하며, 시스템에 Tesseract 실행 파일이 설치되어 있어야 합니다.

## 개발 가이드

### 새로운 사이트 크롤러 추가

1. `crawler/example_scraper.py` 복사
2. `get_article_urls()` 구현: 기사 URL 목록 추출
3. `parse_article()` 구현: 개별 기사 파싱
4. `main.py`에서 크롤러 등록

### RAG 프롬프트 커스터마이징

`rag/chain.py`의 `QA_PROMPT_TEMPLATE` 수정

### API 엔드포인트 추가

`api/server.py`에 새 엔드포인트 추가

## 트러블슈팅

### 1. vLLM 연결 오류

```bash
# vLLM 서버 상태 확인
curl http://intflow.serveftp.com:17681/v1/models
```

### 2. Qdrant 연결 오류

```bash
# Qdrant 서버 상태 확인
curl http://intflow.serveftp.com:17663
```

### 3. 임베딩 모델 다운로드 느림

첫 실행 시 `jhgan/ko-sroberta-multitask` 모델을 다운로드합니다 (~300MB).
인터넷 연결을 확인하고 기다려주세요.

### 4. 크롤링 실패

- 대상 사이트의 HTML 구조가 변경되었을 수 있음
- 크롤러 구현의 CSS selector 확인 필요

## 성능 최적화

### GPU 사용 (가능한 경우)

```bash
# .env에서 설정
EMBEDDING_DEVICE=cuda
```

### 배치 크기 조정

```python
# pipeline/ingestion.py
ingest_documents(documents, batch_size=100)  # 크기 조정
```

## 라이센스

MIT License

## 기여

Pull Requests 환영합니다!

## 연락처

프로젝트 관련 문의: [이메일 또는 GitHub 이슈]
