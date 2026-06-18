.PHONY: knowseeker tripmind

knowseeker:
	uv run streamlit run knowseeker/app.py

tripmind:
	uv run python -m gradio tripmind/app.py --watch-dirs .
