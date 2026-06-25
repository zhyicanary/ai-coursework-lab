.PHONY: knowseeker tripmind

knowseeker:
	uv run streamlit run knowseeker/app.py

tripmind:
	uv run gradio tripmind/app.py
