FROM domainvault/subsync:latest
ENV PYTHONUNBUFFERED 1
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache python3 -m pip install -r /tmp/requirements.txt
