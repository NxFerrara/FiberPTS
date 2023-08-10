Logs: /var/log/programs.log.*
Logrotate: /etc/logrotate.d/programs
Program Service: /etc/systemd/system/monitor.service
Source: /home/potato/NFC_Tracking
LIBNFC: /home/potato/libnfc
Permission File: /lib/udev/rules.d/
Config File: /etc/nfc/libnfc.conf

Must run commands on setup:
Linux:
username: potato
password: ...
sudo systemctl enable ssh
sudo systemctl start ssh
Windows:
python setup_board.py --ip IP --usr USERNAME --pw PASSWORD --driver AC600
Linux:
python send_command.py --ip IP --usr USERNAME --pw PASSWORD --command "nmcli device wifi connect WIFINAME password PASSWORD"

To Do: 
- Running this in parallel
- May need to deal with installing gcc-8 for the wifi adapter driver
	- wget http://deb.debian.org/debian/pool/main/g/gcc-defaults/gcc_8.3.0-1_arm64.deb
- Include support for libre tech overlay from git
- To install:
	- git clone https://github.com/libre-computer-project/libretech-wiring-tool.git
	- cd libretech-wiring-tool
	- sudo ./install.sh
- To Update:
	- cd libretech-wiring-tool
	- git pull origin master
	- make
- Enable overlays
	- sudo ldto merge uart-a spicc spicc-st7789v-240x320-legacy
- Modify and merge overlay
	- nano spicc-st7789v-240x240.dts (change width or height)
	- cc -E -nostdinc -I/home/potato/libretech-wiring-tool/include/ -x assembler-with-cpp -undef -o spicc-st7789v-240x240.pre.dts spicc-st7789v-240x240.dts
	- dtc -@ -q -I dts -O dtb -o spicc-st7789v-240x320.dtbo spicc-st7789v-240x240.pre.dts
	- sudo ldto merge spicc-st7789v-240x320

