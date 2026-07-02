#!/usr/bin/env bash

export DIR="$(dirname "$(realpath "$0")")"
echo "$PI_USER" > SSH_USER
sudo sdm --customize \
  --plugin user:"adduser=$PI_USER|password=$PASS" \
  --plugin apps:"apps=@$DIR/apps" \
  --plugin L10n:host \
  --plugin disables:piwiz \
  --plugin network:"nmconn=$DIR/wifi.nmconnection" \
  --plugin runatboot:"script=$DIR/first_boot.sh|output=/var/log/shazam.first_boot.log|error=/var/log/shazam.first_boot.log" \
  --plugin copyfile:"from=$PUBLIC_KEY_PATH|to=/home/$PI_USER/.ssh/|mkdirif=true" \
  --plugin copyfile:"from=$DIR/SSH_USER|to=/usr/share/shazam/|mkdirif=true" \
  --plugin copyfile:"from=$DIR/.env|to=/usr/share/shazam/|mkdirif=true" \
  --extend --xmb 6144 \
  --expand-root \
  --regen-ssh-host-keys \
  --restart \
  2026-06-19-raspios-bookworm-arm64-lite.img
sudo sdm --burn /dev/sda \
  --hostname shazam \
  --expand-root \
  2026-06-19-raspios-bookworm-arm64-lite.img
