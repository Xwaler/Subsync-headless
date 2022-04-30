FROM domainvault/subsync:latest

ENV PYTHONUNBUFFERED 1

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install -r /tmp/requirements.txt
