"""
Qdrant에 저장된 실제 문서 수를 계산하는 스크립트
"""
# Ensure project root is in PYTHONPATH when running as a script or under debugger
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
from core import get_qdrant_client
from config import settings
from loguru import logger
from collections import defaultdict


def count_documents():
    """
    Qdrant에서 실제 문서 수를 계산합니다.
    각 point의 metadata에서 url 또는 title을 기준으로 unique한 문서를 카운트합니다.
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME
    
    logger.info(f"Counting documents in collection: {collection_name}")
    
    # Scroll through all points
    offset = None
    all_points = []
    
    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points = result[0]
        if not points:
            break
            
        all_points.extend(points)
        offset = result[1]
        
        if offset is None:
            break
    
    logger.info(f"Total points (chunks): {len(all_points)}")
    
    # Debug: Check first few payloads to understand structure
    if all_points:
        print("\n[디버그] 첫 번째 point의 payload 구조:")
        first_point = all_points[0]
        payload = first_point.payload if hasattr(first_point, 'payload') else {}
        print(f"Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
        print(f"Payload sample: {str(payload)[:500]}")
        print()
    
    # Count unique documents by url (overall)
    documents_by_url = set()
    documents_by_title = set()
    documents_by_url_title = set()
    
    # Count by source type (웹페이지 vs 논문)
    documents_by_source = defaultdict(set)  # source -> set of doc keys
    chunks_by_source = defaultdict(int)  # source -> total chunk count
    points_by_source = defaultdict(int)  # source -> point count
    
    # Also count chunks per document
    chunks_per_doc = defaultdict(int)
    
    # Track all payload keys to understand structure
    all_keys = set()
    all_sources = set()
    
    for point in all_points:
        payload = point.payload if hasattr(point, 'payload') else {}
        
        # Track all keys
        if isinstance(payload, dict):
            all_keys.update(payload.keys())
        
        # Get source (웹페이지 vs 논문 구분)
        source = payload.get('source', '') or payload.get('metadata', {}).get('source', '') if isinstance(payload.get('metadata'), dict) else ''
        if not source:
            source = 'Unknown'
        all_sources.add(source)
        
        # Try different possible key names
        url = payload.get('url', '') or payload.get('source_url', '') or payload.get('link', '')
        title = payload.get('title', '') or payload.get('source_title', '') or payload.get('name', '')
        
        # Also check metadata nested structure
        if not url and 'metadata' in payload:
            metadata = payload.get('metadata', {})
            if isinstance(metadata, dict):
                url = metadata.get('url', '') or url
                title = metadata.get('title', '') or title
                if not source or source == 'Unknown':
                    source = metadata.get('source', source)
        
        # Count by source
        points_by_source[source] += 1
        
        # Count by URL
        if url:
            documents_by_url.add(url)
            chunks_per_doc[url] += 1
            # Count unique documents per source
            doc_key = f"{url}|{title}"
            documents_by_source[source].add(doc_key)
        
        # Count by title
        if title:
            documents_by_title.add(title)
        
        # Count by URL+Title combination (most accurate)
        if url or title:
            doc_key = f"{url}|{title}"
            documents_by_url_title.add(doc_key)
            chunks_by_source[source] += 1
    
    # Print statistics
    print("\n" + "="*60)
    print("문서 통계 (Document Statistics)")
    print("="*60)
    print(f"총 Point 수 (Total Chunks): {len(all_points):,}")
    print(f"\n발견된 Source 타입: {sorted(all_sources)}")
    print(f"발견된 payload 키들: {sorted(all_keys)}")
    
    # Print statistics by source
    print(f"\n{'='*60}")
    print("Source별 통계 (Statistics by Source)")
    print("="*60)
    for source in sorted(all_sources):
        unique_docs = len(documents_by_source[source])
        total_chunks = points_by_source[source]
        print(f"\n[{source}]")
        print(f"  - Point 수 (Chunks): {total_chunks:,}개")
        print(f"  - 고유 문서 수: {unique_docs:,}건")
        if unique_docs > 0:
            avg_chunks = total_chunks / unique_docs
            print(f"  - 문서당 평균 청크 수: {avg_chunks:.2f}개")
    
    print(f"\n{'='*60}")
    print("전체 통계 (Overall Statistics)")
    print("="*60)
    print(f"\n고유 문서 수 (Unique Documents):")
    print(f"  - URL 기준: {len(documents_by_url):,}건")
    print(f"  - 제목 기준: {len(documents_by_title):,}건")
    print(f"  - URL+제목 조합 기준: {len(documents_by_url_title):,}건")
    
    # Calculate average chunks per document
    if documents_by_url:
        avg_chunks = sum(chunks_per_doc.values()) / len(documents_by_url)
        print(f"\n문서당 평균 청크 수: {avg_chunks:.2f}개")
        
        # Show distribution
        chunk_counts = list(chunks_per_doc.values())
        if chunk_counts:
            print(f"  - 최소: {min(chunk_counts)}개")
            print(f"  - 최대: {max(chunk_counts)}개")
            print(f"  - 중간값: {sorted(chunk_counts)[len(chunk_counts)//2]}개")
    
    # Show top documents by chunk count
    if chunks_per_doc:
        print(f"\n청크가 많은 문서 Top 10:")
        sorted_docs = sorted(chunks_per_doc.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (url, count) in enumerate(sorted_docs, 1):
            print(f"  {i}. {count}개 청크 - {url[:80]}")
    
    print("="*60)
    
    return {
        "total_points": len(all_points),
        "unique_by_url": len(documents_by_url),
        "unique_by_title": len(documents_by_title),
        "unique_by_url_title": len(documents_by_url_title),
        "avg_chunks_per_doc": avg_chunks if documents_by_url else 0
    }


if __name__ == "__main__":
    try:
        stats = count_documents()
    except Exception as e:
        logger.error(f"Error counting documents: {e}")
        raise

