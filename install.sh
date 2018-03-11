#!/bin/bash
echo "Downloading & Installing Packages..."
apt-get install -y python nmap dnsutils mtr python-pip && pip install telepot

echo
echo
echo --------------------------------
echo
echo
echo "Enter your Telegram BOT Token. "
echo "Telegram BOT Token can be asked to BotFather. "
read -r TG_BOT_TOKEN

echo "bot_token = '$TG_BOT_TOKEN'" > tempconfig.py

echo
echo
echo --------------------------------
echo
echo
echo "Trying to find out your Telegram sender-id..."
python get-sender-id.py  | grep "'id'" | uniq -c | awk '{ print $3 }' | sed s'/,//'

rm tempconfig.py

echo "Enter your Telegram Sender ID. "
echo "Telegram Sender ID is your identifier. If automatic sender ID retrieval has failed, try sending a private message to your bot in Telegram, and try again. "
read -r SENDER_ID

sed -i s"/MY-TG-BOT-TOKEN/$TG_BOT_TOKEN/" config.py
sed -i s"/MY-SENDER-ID-LIST/$SENDER_ID/" config.py

echo "Configure supervisor? (y/n)"
read -r SUPERVISOR
if [ $SUPERVISOR == "y" ]; then
	apt-get install -y supervisor

	echo "Configuring tsh as a service..."
	scp supervisor/conf.d/tsh.conf /etc/supervisor/conf.d/tsh.conf

	echo "Update supervisord..."
	supervisorctl update 

	echo "Starting tsh service..."
	supervisorctl start tsh
fi
