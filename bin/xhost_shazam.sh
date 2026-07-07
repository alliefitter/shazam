#!/usr/bin/env bash

while true; do
  /usr/bin/xhost + local:shazam  < /dev/null && break
  sleep 5
done