FROM python:3.7

RUN apt-get update


# Download firefox and setup a fake display
RUN apt-get -y install firefox-esr xvfb
ENV DISPLAY=:1

WORKDIR /tempDir
# Download and extract geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz
RUN tar -xvzf geckodriver*
RUN mv geckodriver /usr/local/bin/

# Clean directory
RUN rm -R *

WORKDIR /app/N7

# Install python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r ./requirements.txt

#copy local files
COPY main.py .
COPY entrypoint.sh .

VOLUME ["/app/N7/data"]

CMD ["./entrypoint.sh"]