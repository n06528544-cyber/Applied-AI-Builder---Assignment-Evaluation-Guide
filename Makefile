.PHONY: install test demo samples ui docker clean

install:
	python -m venv .venv && . .venv/bin/activate && pip install -e .

test:
	pytest -q

samples:
	python -m samples.build_sample_pdfs

demo:
	ddr demo

ui:
	streamlit run src/ddr/app.py

docker:
	docker build -t ddr-generator . && docker run -p 8501:8501 ddr-generator

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f samples/output/DDR_Report.*
