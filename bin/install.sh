#!/usr/bin/env bash


if [ -z ${SHARE_PATH+x} ]; then
  export SHARE_PATH=/usr/share/shazam/
fi
if [ -z ${LIB_PATH+x} ]; then
  export LIB_PATH=/usr/lib/shazam/
fi

export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
export UV=/root/.local/bin/uv
export UV_PYTHON_INSTALL_DIR=/opt/uv-python
mkdir -p "${UV_PYTHON_INSTALL_DIR}"
chmod 755 "${UV_PYTHON_INSTALL_DIR}"
[ -f "${SHARE_PATH}.env" ] || { echo "ERROR: ${SHARE_PATH}.env not found"; exit 1; }
set -a
# shellcheck source=/dev/null
source "${SHARE_PATH}.env"
set +a
[ -n "${SSH_USER}" ] || { echo "ERROR: SSH_USER not set in ${SHARE_PATH}.env"; exit 1; }
echo "Using ssh user ${SSH_USER}"
echo "User lib path ${LIB_PATH}"
echo "User share path ${SHARE_PATH}"

mv "/home/${SSH_USER}/.ssh/shazam.pub" "/home/${SSH_USER}/.ssh/authorized_keys"
chown -R "${SSH_USER}:${SSH_USER}" "/home/${SSH_USER}/.ssh/"

echo "Checkout lib"
mkdir -p "${LIB_PATH}"
cd "${LIB_PATH}" || { echo "ERROR: could not cd to ${LIB_PATH}"; exit 1; }
git clone https://github.com/alliefitter/shazam.git
cd shazam || { echo "ERROR: could not cd to shazam"; exit 1; }

echo "Build shazam"
curl -LsSf https://astral.sh/uv/install.sh | sh
"${UV}" build

echo "Adding users"
sudo useradd -r -s /bin/false shazam

echo "Deploying"
mkdir -p /app/shazam
mkdir /etc/lightdm/lightdm.conf.d/
cp dist/*.whl /app/shazam
cp alembic.ini /app/shazam
cp etc/nginx/* /etc/nginx/conf.d
cp etc/systemd/* /etc/systemd/system/
cp etc/lightdm/10-shazam.conf /etc/lightdm/lightdm.conf.d/
cp etc/X11/* /etc/X11/xorg.conf.d/
cp etc/config.txt /boot/firmware/
touch "${SHARE_PATH}shazam.db"
sed -ie "s/SSH_USER/${SSH_USER}/g" /etc/lightdm/lightdm.conf.d/10-shazam.conf
sed -ie "s/SSH_USER/${SSH_USER}/g" /etc/systemd/system/shazam-xhost.service
sed -ie "s|SHARE_PATH|${SHARE_PATH}|g" /etc/systemd/system/shazam-daemon.service
cp bin/xhost_shazam.sh /usr/bin/xhost-shazam
chmod +x /usr/bin/xhost-shazam
"${UV}" sync
"${UV}" run alembic upgrade head

echo "Enabling i2s slave mode"
git clone https://github.com/AmateurAudioDude/Raspberry-Pi-I2S-capture-device-as-slave.git "${SHARE_PATH}i2s"
cd "${SHARE_PATH}i2s" || { echo "ERROR: could not cd to ${SHARE_PATH}i2s"; exit 1; }
sed -ie "s/bitclock-frequency = <1536000>/bitclock-frequency = <3072000>/g" genericstereoaudiocodec.dts
dtc -@ -I dts -O dtb -Wno-unit_address_vs_reg -o genericstereoaudiocodec.dtbo genericstereoaudiocodec.dts
cp genericstereoaudiocodec.dtbo /boot/firmware/overlays

echo "Installing shazam"
cd /app/shazam || { echo "ERROR: could not cd to /app/shazam"; exit 1; }
"${UV}" venv venv
"${UV}" pip install ./*.whl --python venv/bin/python

echo "Changing app ownership"
chown -R shazam:shazam /app/shazam
echo "Deployment complete"

echo "Setting up systemd"
systemctl daemon-reload
systemctl enable shazam-daemon.service
systemctl enable shazam-xhost.service
raspi-config nonint do_boot_behaviour B4
echo "Installation complete!"