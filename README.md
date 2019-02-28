## tsh

Telegram Shell (tsh) is a python script that allows your Linux server to communicate via Telegram, by using a Telegram bot.

tsh helps bridging your beloved UNIX command line tools and your mobile phone. It will allow communications in both ways, by enabling you to send messages from your Linux system to Telegram, and to send commands from Telegram to Linux.

  - Some builtin commands are included for easier access (ping, nmap, etc).
  - More commands can be added by placing shellscripts (.sh) in tsh folder.
  - Messages can be sent from Linux to Telegram by sending strings to tsh FIFO or socket (as simple as `echo message > msg.fifo`).

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

##### NOTES:

- You will be asked to insert your Telegram Bot Token aquired on the first step. <br>

- The script will guess your Sender-id based on the messages you send on the first step. <br>

- If you cannot figure out how to find your Sender-id manually launch the script get-sender-id.py from commandline and you will get a raw output containing chat_id,sender_id,username,type <br>

Installer will ask if you wish to configure tsh as a system service via systemd or supervisor. If you choose supervisor and it is missing, it will be installed.

## Usage

### Messaging tools

- /listchat - List all known chats the bot is in (and also chat IDs)
- /redirect `<source>` `<chat id> [<chat id...>]` - Change the destination of FIFO/socket messages to another chat
- /sourceadd `<name>` - Add a new fifo/socket to read from, with the specified name
- /sourcedel `<name>` - Delete the specified fifo/socket
- /say `<chat id>` `<message>` - Make the bot say something on a chat

### Linux tools

- /help - List locally defined commands (custom shellscripts)
- /ping - Tests connectivity 
- /dig - Resolve the given domain, supports RR.. example /dig A google.com or /dig MX google.com
- /mtr - Execute a mtr with a following report
- /nmap - Execute a nmap -Pn -A
- /curl - Execute a curl request
- /whois - Whois lookup
- /sysinfo - Display generic system information (disk usage, network & memory)
- /sh - Execute a command in Bash, for example /sh cat namefile , /sh ps auxf | grep ssh

### Further configuration

URL previews can be disabled by setting `url_preview` to `False` in config.py.

## Adding custom commands

Add shellscripts in tsh folder. The new command will have the same name as the shellscript (minus the .sh extension).
Filename must end in ".sh".

```
cat > test.sh << 'EOF'
echo This is a tsh test command!
echo You sent those arguments: $@
EOF
chmod +x test.sh
```

then restart the tsh service. The "/test" command will be available.


## Send messages from Linux server to Telegram

By default, messages will be sent to the bot owner. You can change where they are sent with `/listchat` and `/redirect`.

#### Using FIFO

Send the message to the fifo:

```
echo yourmessage > msg.fifo
```


#### Using sockets

Sockets won't block if the service is not running, but are less comfortable to use from the shell.
To use the socket from the shell, install socat, then run

```
echo yourmessage | socat - UNIX-CLIENT:msg.socket
```

## Tests

The following scripts are being tested on Debian 8 and marked as working.

## Contributors

Please thank fnzv for the original project.

## License

Code distributed under MIT licence.

