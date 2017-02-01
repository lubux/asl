#!/bin/bash
sudo apt-get update
sudo apt-get -y install build-essential libevent-dev
wget https://Launchpad.net/libmemcached/1.0/1.0.18/+download/libmemcached-1.0.18.tar.gz
tar xvf libmemcached-1.0.18.tar.gz
cd libmemcached-1.0.18
export LDFLAGS=-lpthread
./configure --enable-memaslap && make clients/memaslap
rm libmemcached-1.0.18.tar.gz
