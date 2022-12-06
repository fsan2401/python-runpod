FROM ubuntu:18.04

RUN apt update && apt install --no-install-recommends python3 python3-pip locales -y \
	&& rm -rf /var/lib/apt/lists/* \
	&& localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

ENV LANG en_US.utf8

RUN pip3 install requests 

RUN mkdir /app
 
COPY main.py  /app

CMD [ "python3","/app/main.py" ]