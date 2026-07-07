#!/usr/bin/env bash

echo "Installing packages"
apt-get update
apt-get install -y git lightdm openbox vim x11-xserver-utils xserver-xorg-core

echo "Installing Docker"
curl -fsSL https://get.docker.com | sh

echo "Cloning shazam"
git clone https://github.com/alliefitter/shazam.git /tmp/shazam
cd /tmp/shazam || { echo "ERROR: could not cd to shazam"; exit 1; }

echo "Adding users"
sudo useradd -r -s /bin/false -U -G audio shazam
usermod -aG docker shazam

echo "Installing"
mkdir -p /app/shazam
mkdir /etc/lightdm/lightdm.conf.d/

echo "Enter ACRCloud credentials"
read -rp "ACRCloud host: " ACR_HOST
read -rp "ACRCloud access key: " ACR_ACCESS_KEY
read -rsp "ACRCloud access secret: " ACR_ACCESS_SECRET
echo

cp etc/.env.example /app/shazam/.env
sed -ie "s|^ACR_HOST=.*|ACR_HOST=${ACR_HOST}|" /app/shazam/.env
sed -ie "s|^ACR_ACCESS_KEY=.*|ACR_ACCESS_KEY=${ACR_ACCESS_KEY}|" /app/shazam/.env
sed -ie "s|^ACR_ACCESS_SECRET=.*|ACR_ACCESS_SECRET=${ACR_ACCESS_SECRET}|" /app/shazam/.env

cp etc/systemd/* /etc/systemd/system/
cp etc/lightdm/10-shazam.conf /etc/lightdm/lightdm.conf.d/
cp etc/X11/* /etc/X11/xorg.conf.d/
cp etc/config.txt /boot/firmware/
cp etc/docker-compose.yaml /app/shazam/
touch /app/shazam/shazam.db
sed -ie "s/SSH_USER/${SSH_USER}/g" /etc/lightdm/lightdm.conf.d/10-shazam.conf
sed -ie "s/SSH_USER/${SSH_USER}/g" /etc/systemd/system/shazam-xhost.service
sed -ie "s|SHARE_PATH|${SHARE_PATH}|g" /etc/systemd/system/shazam-daemon.service
sed -ie "s/USER_ID/$(id -u shazam)/g" /app/shazam/docker-compose.yaml
sed -ie "s/GROUP_ID/$(id -g shazam)/g" /app/shazam/docker-compose.yaml
cp bin/xhost_shazam.sh /usr/bin/xhost-shazam
chmod +x /usr/bin/xhost-shazam
chown -R shazam:shazam /app/shazam

echo "Enabling i2s slave mode"
git clone https://github.com/AmateurAudioDude/Raspberry-Pi-I2S-capture-device-as-slave.git /tmp/i2s
cd /tmp/i2s || { echo "ERROR: could not cd to /tmp/i2s"; exit 1; }
sed -ie "s/bitclock-frequency = <1536000>/bitclock-frequency = <3072000>/g" genericstereoaudiocodec.dts
sed -ie "s/dai-tdm-slot-width = <16>/dai-tdm-slot-width = <32>/g" genericstereoaudiocodec.dts
dtc -@ -I dts -O dtb -Wno-unit_address_vs_reg -o genericstereoaudiocodec.dtbo genericstereoaudiocodec.dts
cp genericstereoaudiocodec.dtbo /boot/firmware/overlays

echo "Setting up systemd"
systemctl daemon-reload
systemctl enable shazam-daemon.service
systemctl enable shazam-xhost.service
raspi-config nonint do_boot_behaviour B4
echo "Installation complete!"