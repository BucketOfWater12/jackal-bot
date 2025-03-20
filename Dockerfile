FROM python:3.10
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

ENV PORT=8080

EXPOSE 8080

CMD ["python", "jackal_bot.py"]