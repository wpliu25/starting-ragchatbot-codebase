# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the application (from project root)
./run.sh

# Or manually (from project root)
cd backend && uv run uvicorn app:app --reload --port 8000

# Code quality commands
./scripts/format.sh        # Format all Python files with black
./scripts/check-format.sh  # Check formatting without modifying files
./scripts/quality.sh       # Run all quality checks (format + tests)
```

- Web interface: http://localhost:8000
- API docs: http://localhost:8000/docs

## Environment Setup

Create `.env` in project root:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot with a FastAPI backend and vanilla JS frontend.

### Query Flow

1. **Frontend** (`frontend/script.js`) sends POST to `/api/query` with `{query, session_id}`
2. **FastAPI** (`backend/app.py`) routes to `RAGSystem.query()`
3. **RAGSystem** (`backend/rag_system.py`) orchestrates the flow:
   - Gets conversation history from `SessionManager`
   - Calls `AIGenerator.generate_response()` with Claude tools
4. **AIGenerator** (`backend/ai_generator.py`) makes Claude API call:
   - Claude decides whether to use `search_course_content` tool
   - If tool used: executes search, makes second Claude call with results
5. **CourseSearchTool** (`backend/search_tools.py`) queries `VectorStore`
6. **VectorStore** (`backend/vector_store.py`) performs ChromaDB semantic search
7. Response flows back with answer + sources

### Key Components

| File | Purpose |
|------|---------|
| `backend/rag_system.py` | Main orchestrator - coordinates all components |
| `backend/ai_generator.py` | Claude API interface with tool handling |
| `backend/vector_store.py` | ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (chunks) |
| `backend/document_processor.py` | Parses course docs into 800-char chunks with 100-char overlap |
| `backend/search_tools.py` | Tool definitions for Claude function calling |
| `backend/session_manager.py` | Conversation history (max 2 exchanges) |
| `backend/config.py` | Centralized settings loaded from environment |

### Document Format

Course documents in `docs/` follow this structure:
```
Course Title: [name]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[content...]

Lesson 1: [title]
...
```

### Data Storage

- ChromaDB persists at `backend/chroma_db/`
- Documents auto-load from `docs/` on server startup
- Embedding model: `all-MiniLM-L6-v2`
