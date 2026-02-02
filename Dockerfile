FROM python:3.12-alpine

RUN apk add --no-cache tzdata cronie

ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

WORKDIR /

COPY demo.py .

# MAILTO voided so that no email sending is attempted by cron
RUN echo 'MAILTO=""' > /etc/crontabs/root && \
    echo '* * * * * /usr/local/bin/python3 /demo.py >> /proc/1/fd/1 2>> /proc/1/fd/2' >> /etc/crontabs/root && \
    chmod 0644 /etc/crontabs/root 

# Run once on startup, then start cron in foreground
CMD sh -c "python3 /demo.py && crond -f"
