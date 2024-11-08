FROM python:3.11-slim

WORKDIR /home

# RUN apt-get update && apt-get install -y \
# #     build-essential \
# #     curl \
# #     software-properties-common \
#      git \
#      && rm -rf /var/lib/apt/lists/*

COPY . /home/

#COPY pages /home/pages

RUN pip3 install -r requirements.txt

EXPOSE 8000

CMD ["python", "-m", "chainlit", "run", "app.py", "-h","--host","0.0.0.0"]