FROM debian:bullseye-slim

# install dependencies for building
RUN apt-get update && apt-get install -y \
    acl bc curl cvs git mercurial \
    rsync subversion wget \
    bison bzip2 flex gawk gperf gzip help2man \
    nano perl patch tar texinfo unzip \
    automake binutils build-essential cpio \
    libtool libncurses-dev pkg-config \
    python-is-python3 libtool-bin \
    qemu-user-static

RUN useradd -m modgen
USER modgen
WORKDIR /home/modgen

RUN git clone https://github.com/moddevices/mod-plugin-builder/

WORKDIR /home/modgen/mod-plugin-builder

ARG INSTALL_MODDUOX=false
RUN if [ ${INSTALL_MODDUOX} = true ]; then \
    ./bootstrap.sh modduox minimal \
;fi

ARG INSTALL_MODDWARF=false
RUN if [ ${INSTALL_MODDWARF} = true ]; then \
    ./bootstrap.sh moddwarf minimal \
;fi

# install DPF develop
RUN git clone -b develop https://github.com/DISTRHO/DPF.git dpf

WORKDIR /home/modgen/mod-plugin-builder/dpf
RUN sed -i 's/git@github.com\:/https\:\/\/github.com\//' .gitmodules
RUN git submodule update --init --recursive

WORKDIR /home

USER root
RUN apt-get install -y python3-pip

USER modgen
RUN mkdir -p /home/modgen/server
WORKDIR /home/modgen/server
COPY requirements.txt /home/modgen/server
RUN pip3 install -r requirements.txt


# CMD ["python", "server.py"]