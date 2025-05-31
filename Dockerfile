FROM python:3.13

WORKDIR /app
COPY . /app/
RUN apt-get update -y && apt-get install -y cron &&\
pip install --no-cache-dir -r requirements.txt 
RUN chmod +x ./start_local.sh
ENTRYPOINT ["sh", "start_local.sh"]
