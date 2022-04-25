FROM python:3.9.4-slim-buster
WORKDIR /app
ADD requirements.txt /app
RUN pip3 install -r requirements.txt
ADD . /app
ENTRYPOINT ["python3", "-u", "server.py"]