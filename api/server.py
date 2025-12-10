"""
FastAPI server for Pig Farming RAG LLM API
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from loguru import logger

from config import settings
from rag import get_qa_chain, get_conversational_chain
from core import init_vectorstore, get_llm
from pipeline import ingest_from_text

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="한국 양돈 전문 RAG LLM API"
)

# Static files (for chat UI)
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global QA chain (lazy initialization)
qa_chain = None


def get_or_create_qa_chain():
    """Get or create QA chain instance"""
    global qa_chain
    if qa_chain is None:
        logger.info("Initializing QA chain...")
        qa_chain = get_qa_chain()
    return qa_chain


# Request/Response Models
class QueryRequest(BaseModel):
    """Query request model"""
    question: str = Field(..., description="사용자 질문", min_length=1)
    top_k: Optional[int] = Field(None, description="검색할 문서 개수", ge=1, le=20)
    use_rag: bool = Field(True, description="임베딩 기반 검색 사용 여부 (False면 순수 LLM)")
    chat_history: Optional[List[str]] = Field(
        None,
        description="이전 대화(간단 문자열 목록). use_rag=False 시 LLM 컨텍스트로 사용"
    )


class SourceDocument(BaseModel):
    """Source document model"""
    content: str = Field(..., description="문서 내용")
    title: Optional[str] = Field(None, description="문서 제목")
    url: Optional[str] = Field(None, description="문서 URL")
    source: Optional[str] = Field(None, description="출처")
    score: Optional[float] = Field(None, description="유사도 점수")


class QueryResponse(BaseModel):
    """Query response model"""
    answer: str = Field(..., description="LLM 답변")
    source_documents: List[SourceDocument] = Field(..., description="참고 문서")
    timestamp: datetime = Field(default_factory=datetime.now)


class IngestRequest(BaseModel):
    """Document ingestion request"""
    text: str = Field(..., description="문서 텍스트", min_length=100)
    title: Optional[str] = Field(None, description="문서 제목")
    url: Optional[str] = Field(None, description="문서 URL")
    source: Optional[str] = Field("manual", description="출처")


class IngestResponse(BaseModel):
    """Ingestion response model"""
    success: bool
    chunks_created: int
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    vectorstore_initialized: bool
    llm_initialized: bool


# API Endpoints

@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "message": "한국 양돈 전문 RAG LLM API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check if QA chain can be initialized
        chain = get_or_create_qa_chain()
        return HealthResponse(
            status="healthy",
            vectorstore_initialized=True,
            llm_initialized=True
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            vectorstore_initialized=False,
            llm_initialized=False
        )


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system

    Args:
        request: QueryRequest with question and optional parameters

    Returns:
        QueryResponse with answer and source documents
    """
    try:
        logger.info(f"Received query: {request.question[:50]}...")

        answer = ""
        source_docs: List[SourceDocument] = []

        if request.use_rag:
            # Use conversational chain if chat history is provided
            if request.chat_history:
                # Use conversational chain with chat history
                if request.top_k:
                    chain = get_conversational_chain(top_k=request.top_k, memory=request.chat_history)
                else:
                    chain = get_conversational_chain(memory=request.chat_history)
                
                result = chain.invoke({
                    "question": request.question,
                    "chat_history": request.chat_history
                })
                answer = result.get("answer", "")
            else:
                # Use regular QA chain without chat history
                if request.top_k:
                    chain = get_qa_chain(top_k=request.top_k)
                else:
                    chain = get_or_create_qa_chain()

                result = chain.invoke({"query": request.question, "chat_history": request.chat_history})
                answer = result.get("result", "")

            # Extract source documents (same format for both chains)
            for doc in result.get("source_documents", []):
                score = None
                try:
                    score = doc.metadata.get("score")
                except Exception:
                    pass
                source_docs.append(SourceDocument(
                    content=doc.page_content[:500],  # Truncate for response size
                    title=doc.metadata.get("title"),
                    url=doc.metadata.get("url"),
                    source=doc.metadata.get("source"),
                    score=score
                ))
        else:
            llm = get_llm()

            messages = []
            if request.chat_history:
                for turn in request.chat_history:
                    messages.append(("user", turn))
            messages.append(("user", request.question))

            llm_response = llm.invoke(messages)
            answer = getattr(llm_response, "content", str(llm_response))

        logger.info("Query processed successfully")
        return QueryResponse(
            answer=answer,
            source_documents=source_docs
        )

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    """
    Ingest a document into the vector store

    Args:
        request: IngestRequest with document text and metadata

    Returns:
        IngestResponse with ingestion status
    """
    try:
        logger.info(f"Ingesting document: {request.title or 'Untitled'}...")

        # Prepare metadata
        metadata = {
            "title": request.title or "제목 없음",
            "url": request.url or "",
            "source": request.source,
            "ingested_at": datetime.now().isoformat()
        }

        # Ingest document
        chunks_created = ingest_from_text(
            text=request.text,
            metadata=metadata
        )

        if chunks_created > 0:
            return IngestResponse(
                success=True,
                chunks_created=chunks_created,
                message=f"Successfully ingested {chunks_created} chunks"
            )
        else:
            return IngestResponse(
                success=False,
                chunks_created=0,
                message="No chunks created (document may be too short or invalid)"
            )

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )


@app.post("/init-vectorstore")
async def initialize_vectorstore(reset: bool = False):
    """
    Initialize Qdrant collection

    Args:
        reset: If True, delete existing collection and recreate

    Returns:
        Success message
    """
    try:
        logger.info(f"Initializing vectorstore (reset={reset})...")
        init_vectorstore(reset=reset)
        return {
            "success": True,
            "message": f"Vectorstore initialized (reset={reset})"
        }
    except Exception as e:
        logger.error(f"Vectorstore initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vectorstore initialization failed: {str(e)}"
        )


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """Serve static chat UI"""
    try:
        with open("api/static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat page not found")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Pig Farming RAG LLM API...")
    logger.info(f"vLLM Server: {settings.VLLM_BASE_URL}")
    logger.info(f"Qdrant Server: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

    try:
        # Initialize vectorstore if needed
        init_vectorstore(reset=False)
        logger.info("API startup complete")
    except Exception as e:
        logger.error(f"Startup initialization failed: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
