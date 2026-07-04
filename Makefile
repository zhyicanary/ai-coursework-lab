.PHONY: backend frontend mcp

backend:
	uv run uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev or pnpm dev

mcp:
	uv run python -m common.mcp_server.server
