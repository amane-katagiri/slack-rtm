FROM python:3.7.2-stretch
MAINTAINER Amane Katagiri
CMD [""]
ENTRYPOINT ["slack-rtm"]

WORKDIR /app
RUN apt update \
  && apt install -y heirloom-mailx --no-install-recommends \
  && apt clean
COPY . /app
RUN pip install -e .
WORKDIR /app/slack_rtm
