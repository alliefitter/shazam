#!/usr/bin/env bash

# Reattach stdin to the terminal: when piped via `curl | bash -`, stdin is
# the script text itself, so the `read` prompts below would silently
# consume subsequent lines of this script instead of waiting for input.
exec < /dev/tty

SSH_USER="${SSH_USER:-$(whoami)}"

echo "Installing packages"
sudo apt-get update
sudo apt-get install -y git lightdm openbox vim x11-xserver-utils xserver-xorg-core

echo "Installing Docker"
curl -fsSL https://get.docker.com | sh

echo "Cloning shazam"
git clone https://github.com/alliefitter/shazam.git /tmp/shazam
cd /tmp/shazam || { echo "ERROR: could not cd to shazam"; exit 1; }

echo "Adding users"
sudo useradd -r -s /bin/false -U -G audio shazam
sudo usermod -aG docker shazam

echo "Installing"
sudo mkdir -p /app/shazam
sudo mkdir /etc/lightdm/lightdm.conf.d/

echo "Enter ACRCloud credentials"
read -rp "ACRCloud host: " ACR_HOST
read -rp "ACRCloud access key: " ACR_ACCESS_KEY
read -rsp "ACRCloud access secret: " ACR_ACCESS_SECRET
echo

sudo cp etc/.env.example /app/shazam/.env
sudo sed -ie "s|^ACR_HOST=.*|ACR_HOST=${ACR_HOST}|" /app/shazam/.env
sudo sed -ie "s|^ACR_ACCESS_KEY=.*|ACR_ACCESS_KEY=${ACR_ACCESS_KEY}|" /app/shazam/.env
sudo sed -ie "s|^ACR_ACCESS_SECRET=.*|ACR_ACCESS_SECRET=${ACR_ACCESS_SECRET}|" /app/shazam/.env

sudo cp etc/docker/* /etc/docker/
sudo cp etc/systemd/* /etc/systemd/system/
sudo cp etc/lightdm/10-shazam.conf /etc/lightdm/lightdm.conf.d/
sudo cp etc/X11/* /etc/X11/xorg.conf.d/
sudo cp etc/config.txt /boot/firmware/
sudo cp etc/docker-compose.yaml /app/shazam/
sudo mkdir /app/shazam/data/
sudo touch /app/shazam/data/shazam.db
sudo sed -ie "s/SSH_USER/${SSH_USER}/g" /etc/lightdm/lightdm.conf.d/10-shazam.conf
sudo sed -ie "s/SSH_USER/${SSH_USER}/g" /etc/systemd/system/shazam-xhost.service
sudo sed -ie "s/USER_ID/$(id -u shazam)/g" /app/shazam/docker-compose.yaml
sudo sed -ie "s/GROUP_ID/$(id -g shazam)/g" /app/shazam/docker-compose.yaml
sudo cp bin/xhost_shazam.sh /usr/bin/xhost-shazam
sudo chmod +x /usr/bin/xhost-shazam
sudo chown -R shazam:shazam /app/shazam

echo "Enabling i2s slave mode"
git clone https://github.com/AmateurAudioDude/Raspberry-Pi-I2S-capture-device-as-slave.git /tmp/i2s
cd /tmp/i2s || { echo "ERROR: could not cd to /tmp/i2s"; exit 1; }
sed -ie "s/bitclock-frequency = <1536000>/bitclock-frequency = <3072000>/g" genericstereoaudiocodec.dts
sed -ie "s/dai-tdm-slot-width = <16>/dai-tdm-slot-width = <32>/g" genericstereoaudiocodec.dts
dtc -@ -I dts -O dtb -Wno-unit_address_vs_reg -o genericstereoaudiocodec.dtbo genericstereoaudiocodec.dts
sudo cp genericstereoaudiocodec.dtbo /boot/firmware/overlays

echo "Setting up systemd"
sudo systemctl daemon-reload
sudo systemctl enable shazam-daemon.service
sudo systemctl enable shazam-xhost.service
sudo raspi-config nonint do_boot_behaviour B4
echo "Installation complete!"

sudo reboot