FROM python:3.9-slim
ENV PYTHONUNBUFFRED=1
ENV PORT 8080
ENV HOST 0.0.0.0
RUN mkdir /project
RUN mkdir /project/logs
RUN apt-get -y update

WORKDIR /project
COPY . /project

RUN pip install -U pip
RUN pip install --no-cache-dir -r requirements.txt


ENTRYPOINT ["python" , "server.py"]