#!/usr/bin/env bash


if [ -z ${SHARE_PATH+x} ]; then
  export SHARE_PATH=/usr/share/shazam/
fi
if [ -z ${LIB_PATH+x} ]; then
  export LIB_PATH=/usr/lib/shazam/
fi

export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
export UV=/root/.local/bin/uv
source $SHARE.env
echo "Using ssh user $SSH_USER"
echo "User lib path $LIB_PATH"
echo "User share path $SHARE_PATH"

mv "/home/$SSH_USER/.ssh/shazam.pub" "/home/$SSH_USER/.ssh/authorized_keys"
chown -R "$SSH_USER:$SSH_USER" "/home/$SSH_USER/.ssh/"

echo "Checkout lib"
mkdir -p "$LIB_PATH"
cd "$LIB_PATH"
git clone https://github.com/alliefitter/shazam.git
cd shazam

echo "Build shazam"
curl -LsSf https://astral.sh/uv/install.sh | sh
"$UV" python install 3.12
"$UV" python pin 3.12
"$UV" build

echo "Adding users"
sudo useradd -r -s /bin/false shazam

echo "Deploying"
mkdir -p /app/shazam
mkdir /etc/lightdm/lightdm.conf.d/
cp dist/*.whl /app/shazam
cp etc/nginx/* /etc/nginx/conf.d
cp etc/systemd/* /etc/systemd/system/
cp etc/lightdm/10-shazam.conf /etc/lightdm/lightdm.conf.d/
cp etc/config.txt /boot/firmware/
sed -ie "s/SSH_USER/$SSH_USER/g" /etc/lightdm/lightdm.conf.d/10-shazam.conf
sed -ie "s/SSH_USER/$SSH_USER/g" /etc/systemd/system/shazam-xhost.service
sed -ie "s/SHARE_PATH/$SHARE_PATH/g" /etc/systemd/system/shazam-daemon.service
cp bin/xhost_shazam.sh /usr/bin/xhost-shazam
chmod +x /usr/bin/xhost-shazam

echo "Enabling i2s slave mode"
git clone https://github.com/AmateurAudioDude/Raspberry-Pi-I2S-capture-device-as-slave.git "${SHARE_PATH}i2s"
cd "${SHARE_PATH}i2s"
sed -ie "s/bitclock-frequency = <1536000>/bitclock-frequency = <3072000>/g" genericstereoaudiocodec.dts
dtc -@ -I dts -O dtb -Wno-unit_address_vs_reg -o genericstereoaudiocodec.dtbo genericstereoaudiocodec.dts
cp genericstereoaudiocodec.dtbo /boot/firmware/overlays

echo "Installing shazam"
cd /app/shazam
"$UV" run python -m venv venv
./venv/bin/pip3 install *.whl
touch "${SHARE_PATH}shazam.db"
./venv/bin/alembic -c $SHARE_PATHshazam/alembic.ini upgrade head

echo "Changing app ownership"
chown -R shazam:shazam /app/shazam
echo "Deployment complete"

echo "Setting up systemd"
systemctl daemon-reload
systemctl enable shazam-daemon.service
systemctl enable shazam-xhost.service
raspi-config nonint do_boot_behaviour B4
echo "Installation complete!"
