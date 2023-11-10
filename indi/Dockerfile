FROM ubuntu:latest

RUN apt update && apt install -y \
    software-properties-common \
    python-setuptools \
    python3-pip \
    libindi-dev \
    swig \
    libcfitsio-dev \
    libnova-dev

RUN apt-add-repository ppa:mutlaqja/ppa
RUN apt update && apt install -y indi-full

WORKDIR /app
