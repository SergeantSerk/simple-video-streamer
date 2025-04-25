ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-alpine AS builder
RUN apk add --no-cache alpine-sdk libvpx-dev opus-dev

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:${PYTHON_VERSION}-alpine
RUN apk add --no-cache libvpx opus

ARG PYTHON_VERSION
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages

WORKDIR /opt/simple-video-streamer
COPY ./src .

EXPOSE 8080/tcp
CMD ["python3", "main.py", "--port", "8080"]
