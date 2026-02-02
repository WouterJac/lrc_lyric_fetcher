FROM python:3.12-alpine

ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

ENV MY_COMMAND="/bin/rm -f /.failed_lyrics_cache.json && /usr/local/bin/python3 /lrc_lyric_fetcher.py /music --workers 5 --unsynced"

RUN apk add --no-cache tzdata cronie

WORKDIR /
COPY requirements.txt .
COPY lrc_lyric_fetcher.py .

RUN pip3 install -r requirements.txt

# MAILTO voided so that no email sending is attempted by cron
# Then schedule to run every day at 00:00
RUN echo "MAILTO=''" > /etc/crontabs/root && \
    echo "0 0 * * * ${MY_COMMAND} >> /proc/1/fd/1 2>> /proc/1/fd/2" >> /etc/crontabs/root && \
    chmod 0644 /etc/crontabs/root 


# Run once on startup, then start cron in foreground
CMD sh -c "${MY_COMMAND} && crond -f"
