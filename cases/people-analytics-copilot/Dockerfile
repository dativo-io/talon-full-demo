# Demo-only image; synthetic HR data only. Never bake state or credentials.
FROM python:3.12-slim
WORKDIR /case
COPY requirements.txt /case/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /case
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["python", "demo.py", "ui"]
