## TSH

Telegram Shell is a python script that allows to comunicate to your Linux server via Telegram API (with bots). 

Telegram Shell also allows communication from your Linux server to Telegram.

 <br>
 -------------------------------
## Requirements
- Linux System
- Bot created from @BotFather via Telegram
- Software Packages: python-pip (to install telepot) & basic linux tools like nmap,dig,mtr (optional)

## Installation

The setup is quite easy: <br>

* Chat with BotFather to create a Bot ( https://telegram.me/botfather ), just launch the command /newbot to get your Telegram Token. <br>
 Open the bot chat and send some messages to activate the bot. <br>

* Launch this command on your Linux system: <br>

```
cd /home && git clone https://github.com/simonebaracchi/tsh && cd tsh && bash install.sh 
```

##### WARNING: this command will install the required/missing packages ( dnsutils, python-pip, python, nmap, mtr, pip-telepot )

Installation of pkg supervisor is optional.

##### NOTES:

- You will be asked to insert your Telegram Bot Token aquired on the first step. <br>

- The script will guess your Sender-id based on the messages you send on the first step. <br>

- If you cannot figure out how to find your Sender-id manually launch the script get-sender-id.py from commandline and you will get a raw output containing chat_id,sender_id,username,type <br>

After you finished the installation the python script will run as a system service with supervisor.

## Usage

- /ping - Tests connectivity 
- /dig - Resolve the given domain, supports RR.. example /dig A google.com or /dig MX google.com
- /mtr - Execute a mtr with a following report
- /nmap - Execute a nmap -Pn -A
- /curl - Execute a curl request
- /whois - Whois lookup
- /sysinfo - Display generic system information (disk usage, network & memory)
- /sh - Execute a command with Bash.. example /sh cat namefile , /sh ps auxf | grep ssh

## Tests

The following scripts are being tested on Debian 8 and marked as working.

## Contributors

Please thank fnzv for the original project.

## License

Code distributed under MIT licence.

