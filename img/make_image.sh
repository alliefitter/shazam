#!/usr/bin/env bash

export DIR="$(dirname "$(realpath "$0")")"

[ -f "${DIR}/.env" ] || { echo "ERROR: ${DIR}/.env not found"; exit 1; }

required_vars=(
  DB_URL
  ACR_HOST
  ACR_ACCESS_KEY
  ACR_ACCESS_SECRET
  TITLE_FONT_SIZE
  OTHER_FONT_SIZE
  HEADER_FONT_SIZE
  PREVIOUS_SONG_FONT_SIZE
  SSH_USER
)
for var in "${required_vars[@]}"; do
  grep -q "^${var}=" "${DIR}/.env" || { echo "ERROR: ${var} missing from ${DIR}/.env"; exit 1; }
done
. "${DIR}/.env"
sudo sdm --customize \
  --plugin user:"adduser=${SSH_USER}|password-hash=!" \
  --plugin apps:"apps=@${DIR}/apps" \
  --plugin L10n:host \
  --plugin disables:piwiz \
  --plugin network:"nmconn=${DIR}/wifi.nmconnection" \
  --plugin runatboot:"script=${DIR}/first_boot.sh|output=/var/log/shazam.first_boot.log|error=/var/log/shazam.first_boot.log" \
  --plugin copyfile:"from=${PUBLIC_KEY_PATH}|to=/home/${SSH_USER}/.ssh/|mkdirif=true" \
  --plugin copyfile:"from=${DIR}/.env|to=/usr/share/shazam/|mkdirif=true" \
  --extend --xmb 6144 \
  --expand-root \
  --regen-ssh-host-keys \
  --restart \
  2025-05-13-raspios-bookworm-arm64-lite.img
sudo sdm --burn /dev/sda \
  --hostname shazam \
  --expand-root \
  2025-05-13-raspios-bookworm-arm64-lite.img
