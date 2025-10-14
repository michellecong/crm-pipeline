from app.services.chunking_service import ChunkingService

def test_chunking_service_init():
    service = ChunkingService(chunk_size=500, overlap=50)
    assert service.chunk_size == 500
    assert service.overlap == 50


def test_chunk_text_basic():
    service = ChunkingService(chunk_size=100, overlap=20)
    text = "This is a test. " * 50
    
    chunks = service.chunk_text(text)
    
    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    assert all("char_count" in chunk for chunk in chunks)


def test_chunk_text_empty():
    service = ChunkingService()
    chunks = service.chunk_text("")
    assert len(chunks) == 0


def test_get_chunk_stats():
    service = ChunkingService()
    chunks = [
        {"char_count": 100},
        {"char_count": 200},
        {"char_count": 150}
    ]
    
    stats = service.get_chunk_stats(chunks)
    
    assert stats["total_chunks"] == 3
    assert stats["avg_chunk_size"] == 150
    assert stats["min_chunk_size"] == 100
    assert stats["max_chunk_size"] == 200