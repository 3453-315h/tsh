#!/bin/bash
printf "Downloading & Installing Packages...\n"
apt-get install -y python nmap dnsutils mtr python-pip && pip install telepot

printf "\n\n--------------------------------\n\n"
echo "Enter your Telegram BOT Token. "
echo "Telegram BOT Token can be asked to BotFather. "
read -r TG_BOT_TOKEN

echo "bot_token = '$TG_BOT_TOKEN'" > tempconfig.py

printf "\n\n--------------------------------\n\n"
echo "Trying to find out your Telegram sender-id..."
python get-sender-id.py  | grep "'id'" | uniq -c | awk '{ print $3 }' | sed s'/,//'
rm tempconfig.py

echo "Enter your Telegram Sender ID. "
echo "Telegram Sender ID is your identifier. Only this user will be enabled to send commands to this bot. If automatic sender ID retrieval has failed, try sending a private message to your bot in Telegram, and try again. "
read -r SENDER_ID

cp config.example.py config.py
sed -i s"/MY-TG-BOT-TOKEN/$TG_BOT_TOKEN/" config.py
sed -i s"/MY-SENDER-ID-LIST/$SENDER_ID/" config.py

printf "\n\n--------------------------------\n\n"
echo " Select an option"
echo "[0] Exit installer"
echo "[1] Configure daemon with systemctl (for systemd-enabled distros)"
echo "[2] Disable daemon with systemctl"
echo "[3] Configure daemon with supervisor (for supervisor-enabled distros)"
read -r SUPERVISOR
case $SUPERVISOR in
0)
	exit 0
	;;
1)
	cp systemctl/tsh.example.service /tmp/tsh.service
	DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
	sed -i s"#MY-PATH#$DIR#" /tmp/tsh.service
	mv /tmp/tsh.service /etc/systemd/system/multi-user.target.wants/tsh.service
	systemctl daemon-reload
	systemctl restart tsh
	;;
2)
	systemctl stop tsh
	systemctl disable tsh
	rm /etc/systemd/system/multi-user.target.wants/tsh.service
	systemctl daemon-reload
	systemctl reset-failed
	;;
3)
	apt-get install -y supervisor

	echo "Configuring tsh as a service..."
	scp supervisor/conf.d/tsh.conf /etc/supervisor/conf.d/tsh.conf

	echo "Update supervisord..."
	supervisorctl update 

	echo "Starting tsh service..."
	supervisorctl start tsh
	;;
*)
	echo Unrecognized option $SUPERVISOR, exiting
	exit 1
	;;
esac
