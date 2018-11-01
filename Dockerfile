FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scienzati_bot.py .

CMD [ "python", "./scienzati_bot.py" ]
