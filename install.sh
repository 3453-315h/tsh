#!/bin/bash
echo "Downloading & Installing Packages.. \n"
apt-get install -y python nmap dnsutils mtr python-pip && pip install telepot

echo "Enter your Telegram BOT Token: "
read -sr TG_BOT_TOKEN


sed -i s"/TG-BOT-TOKEN/$TG_BOT_TOKEN/" get-sender-id.py

echo "Trying to find out your Telegram sender-id..\n"
python get-sender-id.py  | grep "'id'" | uniq -c | awk '{ print $3 }' | sed s'/,//'

echo "Enter your Telegram Sender ID: "
read -sr SENDER_ID

sed -i s"/SENDER-ID-LIST/$SENDER_ID/" controller.py

sed -i s"/TG-BOT-TOKEN/$TG_BOT_TOKEN/" controller.py


echo "Configure supervisor? (y/n)"
read -sr SUPERVISOR
if [ $SUPERVISOR == "y" ]; then
	apt-get install -y supervisor

	echo "Configuring tsh as a service.. \n"
	scp supervisor/conf.d/tsh.conf /etc/supervisor/conf.d/tsh.conf

	echo "Update supervisord.. \n"
	supervisorctl update 

	echo "Starting tsh service.. \n"
	supervisorctl start tsh
fi
