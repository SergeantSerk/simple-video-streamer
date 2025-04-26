ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim AS builder
RUN apt-get update && \
    apt-get install --no-install-recommends --yes build-essential git libopus-dev libvpx-dev && \
    apt-get clean

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:${PYTHON_VERSION}-slim
RUN apt-get update && \
    apt-get install --no-install-recommends --yes libopus0 libvpx7 && \
    apt-get clean

ARG PYTHON_VERSION
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages

WORKDIR /opt/simple-video-streamer
COPY ./src .

EXPOSE 8080/tcp
ENTRYPOINT [ "python3", "main.py" ]
CMD ["--port", "8080"]
