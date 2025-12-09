"""
RAG chain implementations for pig farming Q&A
"""
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from types import SimpleNamespace
from core import get_llm, get_vectorstore
from config import settings
from loguru import logger
from typing import Optional, List


# Korean-optimized RAG prompt template
QA_PROMPT_TEMPLATE = """다음은 한국 양돈 산업 관련 참고 자료입니다:

{context}

질문: {question}

위 참고 자료를 바탕으로 전문적이고 구체적인 답변을 작성해주세요.
가능한 경우 출처를 명시하고, 최신 정보를 우선적으로 활용하세요.
확실하지 않은 내용은 추측하지 말고 "참고 자료에서 관련 정보를 찾을 수 없습니다"라고 답변해주세요.

답변:"""


def get_qa_prompt() -> PromptTemplate:
    """
    Get Korean-optimized QA prompt template

    Returns:
        PromptTemplate: Configured prompt template
    """
    return PromptTemplate(
        template=QA_PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )


def get_qa_chain(
    llm=None,
    vectorstore=None,
    return_source_documents: bool = True,
    top_k: int = None
):
    """
    Create basic RAG QA chain

    Args:
        llm: Optional LLM instance (default: from config)
        vectorstore: Optional vectorstore instance (default: from config)
        return_source_documents: Whether to return source documents
        top_k: Number of documents to retrieve (default: from config)

    Returns:
        object with invoke({"query": str}) -> dict(result, source_documents)
    """
    logger.info("Creating QA chain")

    if llm is None:
        llm = get_llm()

    if vectorstore is None:
        vectorstore = get_vectorstore()

    k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K

    def retrieve(question: str):
        try:
            # similarity_search_with_score returns List[Tuple[Document, float]]
            results = vectorstore.similarity_search_with_score(question, k=k)
            logger.debug(f"Retrieved {len(results)} results")
            docs = []
            for idx, item in enumerate(results):
                # Qdrant returns (Document, score) tuples
                if isinstance(item, tuple) and len(item) == 2:
                    doc, score = item
                else:
                    logger.warning(f"Unexpected result format at index {idx}: {type(item)}, length={len(item) if isinstance(item, tuple) else 'N/A'}")
                    continue
                
                # Ensure score is in metadata for downstream use
                if hasattr(doc, "metadata"):
                    if doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata = {**doc.metadata, "score": score}
                else:
                    doc.metadata = {"score": score}
                docs.append(doc)
            return docs
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            raise

    prompt = get_qa_prompt()

    def invoke(inputs):
        question = inputs.get("query") or inputs.get("question")
        history = inputs.get("chat_history") or []
        retrieval_query = question if not history else f"{question}\n\n이전 대화: " + " | ".join(history)
        docs = retrieve(retrieval_query)
        normalized_docs = docs

        context = "\n\n".join(getattr(doc, "page_content", str(doc)) for doc in normalized_docs)
        formatted = prompt.format(context=context, question=question)
        llm_resp = llm.invoke(formatted)
        answer = getattr(llm_resp, "content", str(llm_resp))
        return {
            "result": answer,
            "source_documents": normalized_docs if return_source_documents else []
        }

    logger.info(f"QA chain created (top_k={k}) using manual runnable")
    return SimpleNamespace(invoke=invoke)


def get_conversational_chain(
    llm=None,
    vectorstore=None,
    memory: Optional[List] = None,
    top_k: int = None
):
    """
    Create conversational RAG chain with chat history
    Uses proper message formatting for better context understanding

    Args:
        llm: Optional LLM instance
        vectorstore: Optional vectorstore instance
        memory: Optional conversation history as list of strings (alternating user/assistant)
        top_k: Number of documents to retrieve

    Returns:
        object with invoke({"question": str, "chat_history": list}) -> dict
    """
    logger.info("Creating conversational chain")

    if llm is None:
        llm = get_llm()

    if vectorstore is None:
        vectorstore = get_vectorstore()

    k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K

    def retrieve(question: str):
        try:
            # similarity_search_with_score returns List[Tuple[Document, float]]
            results = vectorstore.similarity_search_with_score(question, k=k)
            logger.debug(f"Retrieved {len(results)} results")
            docs = []
            for idx, item in enumerate(results):
                # Qdrant returns (Document, score) tuples
                if isinstance(item, tuple) and len(item) == 2:
                    doc, score = item
                else:
                    logger.warning(f"Unexpected result format at index {idx}: {type(item)}, length={len(item) if isinstance(item, tuple) else 'N/A'}")
                    continue
                
                # Ensure score is in metadata for downstream use
                if hasattr(doc, "metadata"):
                    if doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata = {**doc.metadata, "score": score}
                else:
                    doc.metadata = {"score": score}
                docs.append(doc)
            return docs
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            raise

    prompt = get_qa_prompt()

    def invoke(inputs):
        question = inputs.get("question") or inputs.get("query")
        history = inputs.get("chat_history") or memory or []
        retrieval_query = question if not history else f"{question}\n\n이전 대화: " + " | ".join(history)
        docs = retrieve(retrieval_query)
        normalized_docs = docs

        context = "\n\n".join(getattr(doc, "page_content", str(doc)) for doc in normalized_docs)
        formatted = prompt.format(context=context, question=question)

        # Build conversation history: treat provided history as user turns for context
        messages = [HumanMessage(content=turn) for turn in history]
        messages.append(HumanMessage(content=formatted))

        llm_resp = llm.invoke(messages)
        answer = getattr(llm_resp, "content", str(llm_resp))
        return {
            "answer": answer,
            "source_documents": normalized_docs
        }

    logger.info("Conversational chain created")
    return SimpleNamespace(invoke=invoke)


def query_rag(question: str, qa_chain=None) -> dict:
    """
    Query the RAG system with a question

    Args:
        question: User question
        qa_chain: Optional pre-initialized QA chain

    Returns:
        dict: Response with answer and source documents
    """
    if qa_chain is None:
        qa_chain = get_qa_chain()

    logger.info(f"Processing query: {question[:50]}...")

    try:
        result = qa_chain.invoke({"query": question})
        logger.info("Query processed successfully")
        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise
