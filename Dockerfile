FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

#
# The compilation of lxml (a library required and installed by pip) requires more than 1GiB of RAM memory.
# Since I had only 1 GiB of RAM, as a workaround I made a 2GiB swap file
# THIS IS A THING TO AVOID AS MUSH AS POSSIBLE
# Commands executed:
# 
#  1. dd if=/dev/zero of=/swapfile bs=2048 count=1M
#  2. chmod 0600 /swapfile
#  3. mkswap /swapfile
#  4. echo "/swapfile swap swap sw 0 0" >>/etc/fstab
#  5. swapon /swapfile
# 
# 1. Creates a swapfile and fill it of 0s
# 2. Set permissions for a swap file
# 3. Sets the file a file usable as a swap file
# 4. sets the swap on startup
# 5. enables the swap "hotplugged"


RUN apk add py3-pip openssl py3-lxml \
  && apk add --virtual build-dependencies python3-dev build-base wget libffi-dev openssl-dev libxml2-dev libxslt-dev  \
  && rm -rf /var/cache/apk/*

RUN pip install --no-cache-dir -r requirements.txt
RUN apk del build-dependencies


COPY scienzati_bot.py .

CMD [ "python", "./scienzati_bot.py" ]
