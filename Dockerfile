FROM domainvault/subsync:latest
ENV PYTHONUNBUFFERED 1
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt