FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY public ./public
COPY demo_knowledge ./demo_knowledge
COPY run.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["python", "run.py"]
