FROM python:3.6

EXPOSE 5000

WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY db.yaml /app
COPY app1.py /app

COPY templates /app/templates
COPY static /app/static

CMD ["flask", "run", "--host=0.0.0.0"]
CMD python app1.py
