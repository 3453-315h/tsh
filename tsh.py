#!/usr/bin/env python
# Author: Sami Yessou - samiii@protonmail.com
# Telegram Remote-Shell
# Control your Linux System remotely via Telegram API
# Requirements :  apt-get install -y python python-pip && pip install telepot , dig,mtr,nmap,whois ,a Telegram BOT

from pprint import pprint
import telepot,time,os
import config
import socket
import thread
import fcntl
import os
import sys
import signal
from select import select

socket_file = 'msg.socket'
fifo_file = 'msg.fifo'
lock_file = 'msg.lock'
log_file = 'service.log'

def die():
    os.kill(os.getpid(), signal.SIGINT)

def read_and_forward(fdlist):
    while True:
        rlist, wlist, xlist = select(fdlist, [], [])
        for fd in rlist:
            for line in fd:
                for sender in config.senders:
                    bot.sendMessage(sender, line)

def local_input_loop():
    # Cleanup socket
    # Use a separate lockfile to avoid locking the socket
    # If lockfile can be locked, redo the socket
    # If lockfile can't be locked, exit with error.
    lock = open(lock_file, 'w')
    try:
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print('Server is already running')
        die()

    # init socket
    os.unlink(socket_file)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(socket_file)
    os.chmod(socket_file, 0777)
    fd1 = sock.makefile('r')

    # init fifo
    try:
        os.mkfifo(fifo_file, 0777)
    except OSError, e:
        if e.errno == os.errno.EEXIST:
            pass
    fd2 = open(fifo_file, 'r')

    # read loop
    read_and_forward([fd1, fd2])
    
    

def handle(msg):
    chat_id = msg['chat']['id']
    text = msg['text']
    sender = msg['from']['id']
    f = open(log_file, 'a')
    f.write("Chat-id - "+str(chat_id)+" Text - "+str(text)+" Sender - "+str(sender)+"\n")
    f.close()

    if sender in config.senders:

      args=text.split()

      command = args[0]
      if command == '/ping':
            host = str(args[1])
            output=os.popen("ping -c1 "+host).read()
            bot.sendMessage(chat_id, output)

      elif command == '/mtr':
            host = str(args[1])
            output=os.popen("mtr --report "+host).read()
            bot.sendMessage(chat_id, output)

      elif command == '/nmap':
            value = str(args[1])
            host = str(args[2])
            output=os.popen("nmap -A "+value+" "+host).read()
            bot.sendMessage(chat_id, output)

      elif command == '/curl':
            host = str(args[1])
            output=os.popen("curl -Iv "+host).read()
            bot.sendMessage(chat_id, output)

      elif command == '/dig':
            type = str(args[1])
            host = str(args[2])
            output=os.popen("dig +short "+type+" "+host).read()
            bot.sendMessage(chat_id, output)

      elif command == '/whois':
            host = str(args[1])
            output=os.popen("whois "+host).read()
            bot.sendMessage(chat_id, output)


      elif command == '/sysinfo':
            output=os.popen("df -h && free -m && netstat -tunlp").read()
            bot.sendMessage(chat_id, output)


      elif command == '/sh':
            cmd = str(args[1])
            output=os.popen(cmd).read()
            bot.sendMessage(chat_id, output)

      else:
            bot.sendMessage(chat_id, 'Sorry, this does not seem to be a valid command.')

thread.start_new_thread(local_input_loop, ())
bot = telepot.Bot(config.bot_token)
bot.message_loop(handle)


while 1:
    time.sleep(10)
