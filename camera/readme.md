sudo apt update
sudo apt install git cmake libjpeg-dev build-essential
git clone https://github.com/jacksonliam/mjpg-streamer.git
cd mjpg-streamer-experimental
make
sudo make install


chmod +x camera.sh
./camera.sh /dev/video0 5000