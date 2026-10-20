FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 国内构建默认走阿里云 PyPI（在阿里云 ECS 上通常更稳）；亦可换清华等。
# 海外构建：docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
# 镜像索引偶尔仍会让 pip 回源 files.pythonhosted.org 拉 wheel，弱网下易超时
ENV PIP_DEFAULT_TIMEOUT=600

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
