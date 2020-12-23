FROM domainvault/subsync:latest
ENV PYTHONUNBUFFERED 1
RUN apt update && apt install -y git && \
    git clone https://github.com/Xwaler/Subsync-headless.git && \
    pip install --no-cache-dir -r Subsync-headless/requirements.txt