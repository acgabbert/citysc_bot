FROM python:3.11-slim-buster as base

WORKDIR /docker_bot

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . /docker_bot/

ENTRYPOINT ["python3"]
CMD ["controller.py"]