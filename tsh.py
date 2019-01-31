#!/usr/bin/env python
# Author: Sami Yessou - samiii@protonmail.com
# Telegram Remote-Shell
# Control your Linux System remotely via Telegram API
# Requirements :  apt-get install -y python python-pip && pip install telepot

from pprint import pprint
import telepot,time,os
import config
import socket
import thread
import fcntl
import os
import stat
import glob
import sys
import signal
import sqlite3
import json
import subprocess
from threading import Thread, Event
from select import select

socket_file = 'msg.socket'
fifo_file = 'msg.fifo'
lock_file = 'msg.lock'
log_file = 'service.log'

local_keywords = []
all_chats = []

class Chat:
    def __init__(self, id, type, name):
        self.id = id
        self.type = type
        self.name = name
    def __eq__(self, other):
        return self.id == other.id

def die():
    os.kill(os.getpid(), signal.SIGINT)

def fatal(msg):
    print(msg)
    die()

def db_table_exists(db_connection, table):
    c = db_connection.cursor()
    query = c.execute('''SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?''', (table,))
    result = query.fetchone()
    if result[0] == 0:
        return False
    else:
        return True

def db_init():
    db_connection = sqlite3.connect('config.db')
    try:
        if not db_table_exists(db_connection, 'MessageTarget'):
            print('Initializing target database...')
            c = db_connection.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS MessageTarget (source text primary key, destination text)''')
            c.execute('''INSERT INTO MessageTarget VALUES (?, ?)''', ('msg.fifo', json.dumps(config.senders)))
            c.execute('''INSERT INTO MessageTarget VALUES (?, ?)''', ('msg.socket', json.dumps(config.senders)))
        if not db_table_exists(db_connection, 'KnownChats'):
            print('Initializing chat database...')
            c = db_connection.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS KnownChats (id integer primary key, type text, name text)''')
        print('Loading configuration...')
    except:
        fatal('failed to initialize database')
    db_connection.commit()
    db_connection.close()

def db_target_get(source):
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    query = c.execute('''SELECT destination FROM MessageTarget WHERE source=?''', (source,))
    result = query.fetchone()
    ret = json.loads(result[0])
    db_connection.close()
    return ret

def db_target_redirect(source, target):
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    c.execute('''INSERT OR REPLACE INTO MessageTarget (source, destination) VALUES (?, ?)''', (source, json.dumps(target)))
    db_connection.commit()
    db_connection.close()

def db_chat_add(id, type, name):
    this_chat = Chat(id, type, name)
    if this_chat in all_chats:
        return
    all_chats.append(this_chat)
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    c.execute('''INSERT OR REPLACE INTO KnownChats (id, type, name) VALUES (?, ?, ?)''', (id, type, name))
    db_connection.commit()
    db_connection.close()

def db_chat_reload():
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    query = c.execute('''SELECT id,type,name FROM KnownChats''')
    for chat in query:
        this_chat = Chat(chat[0], chat[1], chat[2])
        if this_chat not in all_chats:
           all_chats.append(this_chat)
    db_connection.close()
    

def read_and_forward(source, fd):
    """
    Read from the given file descriptor.
    When a string is available, it is sent to the senders.
    Waits efficiently(!) until a string is available.
    Note to self. All implementations of select() and poll() 
        on FIFOs in Python are broken. All. Of. Them.
        The only workaround is closing and reopening the fd.

    index -- the resource I'm reading from. Used to compute the destination.
    fd -- file descriptor to read from.
    """
    rlist, wlist, xlist = select([fd], [], [])
    for line in fd:
        for sender in db_target_get(source):
            if len(line.split()) > 0:
                log("Sending " + line)
                send(bot, sender, line)

def read_socket():
    """
    Read messages from the socket.
    """
    # init socket
    try:
        os.unlink(socket_file)
    except OSError, e:
        if e.errno == os.errno.ENOENT:
            pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    while True:
        sock.bind(socket_file)
        os.chmod(socket_file, 0777)
        fd = sock.makefile('r')
        read_and_forward(socket_file, fd)
        fd.close()

def read_fifo():
    """
    Read messages from the FIFO.
    """
    # init fifo.
    # re-create source only if missing or not a fifo.
    # note that removing an existing fifo will make writers block indefinitely.
    if not os.path.isfile(fifo_file) or not stat.S_ISFIFO(os.stat(fifo_file).st_mode):
        try:
            os.unlink(fifo_file)
        except OSError, e:
            if e.errno == os.errno.ENOENT:
                pass
        oldmask = os.umask(0)
        os.mkfifo(fifo_file, 0777)
        os.umask(oldmask)
    while True:
        fd = open(fifo_file, 'r')
        read_and_forward(fifo_file, fd)
        fd.close()

def local_input_loop():
    """
    Initialize the local input channels (fifo and socket).
    Then poll on those and forward messages to Telegram.
    """
    # Cleanup socket
    # Use a separate lockfile to avoid locking the socket
    # If lockfile can be locked, redo the socket
    # If lockfile can't be locked, exit with error.
    print('Entering read loop.')
    lock = open(lock_file, 'w')
    try:
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print('Server is already running')
        die()

    thread.start_new_thread(read_socket, ())
    thread.start_new_thread(read_fifo, ())

def log(msg):
    f = open(log_file, 'a')
    f.write(msg + "\n")
    f.close()
    print(msg)
    
def init_keywords():
    for file in glob.glob('*.sh'):
        if file in ['install.sh']:
            continue
        local_keywords.append(file[:-3])

def proc_kill_on_timeout(done, timeout, proc):
    if not done.wait(timeout):
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

def proc_run(command):
    timeout = 120
    done = Event()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
        shell=True, preexec_fn=os.setsid)
    watcher = Thread(target=proc_kill_on_timeout, args=(done, timeout, proc))
    watcher.daemon = True
    watcher.start()
    data = proc.communicate()
    done.set()
    output = data[0]
    if proc.returncode != 0:
        output += '(exited with error)'
    return output

def send(bot, chat_id, msg):
    if msg == None or len(msg) == 0 or len(msg.split()) == 0:
        msg = '(no output)'
    bot.sendMessage(chat_id, msg)

def handle(msg):
    """
    When a message is received, process it.

    msg -- The received message
    """
    chat_id = msg['chat']['id']
    text = msg['text'].encode('ascii','ignore')
    sender = msg['from']['id']
    username = msg['from']['username']

    # add chat to list of all known chats
    db_chat_add(chat_id, msg['chat']['type'], msg['chat']['title'] if 'title' in msg['chat'] else username)

    # avoid logging and processing every single message.
    if text[0] != '/':
        return
    chat_name = ''
    if 'title' in msg['chat']:
        chat_name = '{} ({})'.format(msg['chat']['title'], username)
    else:
        chat_name = username
    log('chatid {} - cmd {}'.format(chat_name, text))

    if sender in config.senders:
      args=text.split()
      command = args[0]
      if command == '/help':
            if len(local_keywords) == 0:
                send(bot, chat_id, 'No locally defined keywords')
            else:
                send(bot, chat_id, 'Local keywords: ' + ', '.join(local_keywords))
      elif command == '/ping':
            host = str(args[1])
            output = proc_run("ping -c1 "+host)
            send(bot, chat_id, output)

      elif command == '/mtr':
            host = str(args[1])
            output = proc_run("mtr --report "+host)
            send(bot, chat_id, output)

      elif command == '/nmap':
            value = str(args[1])
            host = str(args[2])
            output = proc_run("nmap -A "+value+" "+host)
            send(bot, chat_id, output)

      elif command == '/curl':
            host = str(args[1])
            output = proc_run("curl -Iv "+host)
            send(bot, chat_id, output)

      elif command == '/dig':
            type = str(args[1])
            host = str(args[2])
            output = proc_run("dig +short "+type+" "+host)
            send(bot, chat_id, output)

      elif command == '/whois':
            host = str(args[1])
            output = proc_run("whois "+host)
            send(bot, chat_id, output)

      elif command == '/sysinfo':
            output = proc_run("df -h && free -m && netstat -tunlp")
            send(bot, chat_id, output)

      elif command == '/say':
            if not args[1].isdigit():
                send(bot, chat_id, 'Unknown chat id format {}'.format(args[1]))
                return
            chat_number = int(args[1])
            if chat_number < 0 or chat_number >= len(all_chats):
                send(bot, chat_id, 'Unknown chat id {}'.format(chat_number))
                return
            if len(args) < 3:
                send(bot, chat_id, 'Say what?')
                return
            message = str(' '.join(args[2:]))
            send(bot, all_chats[chat_number].id, message)

      elif command == '/sh':
            cmd = str(' '.join(args[1:]))
            output = proc_run(cmd)
            send(bot, chat_id, output)

      elif command == '/listchat':
            db_chat_reload()
            targets = {}
            for target in db_target_get(fifo_file) + db_target_get(socket_file):
                targets[target] = None
            output = 'Known chats I\'m in:\n'
            output += str('\n'.join(['{}: {} ({}) {}'.format(str(i), x.name, x.type, 
                '(current target)' if x.id in targets else '') 
                for i,x in enumerate(all_chats)]))
            send(bot, chat_id, output)

      elif command == '/redirect':
            idx = int(args[1])
            if idx >= len(all_chats):
                send(bot, chat_id, 'This chat index is out of the range of known chats.')
            else:
                new_chat = all_chats[idx]
                db_target_redirect(fifo_file, [new_chat.id])
                db_target_redirect(socket_file, [new_chat.id])
                send(bot, chat_id, 'I\'m switching system messages to {} ({}).'.format(new_chat.name, new_chat.type))

      elif command[0] == '/' and command[1:] in local_keywords:
            args[0] = '.' + args[0] + '.sh'
            output = proc_run(' '.join(args))
            send(bot, chat_id, output)

      else:
            send(bot, chat_id, 'Sorry, this does not seem to be a valid command.')

init_keywords()
db_init()
db_chat_reload()
local_input_loop()
bot = telepot.Bot(config.bot_token)
bot.message_loop(handle)


while 1:
    time.sleep(10)
