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
import re
import stat
import glob
import sys
import signal
import sqlite3
import json
import subprocess
from threading import Thread, Event
from select import select

lock_file = 'msg.lock'
log_file = 'service.log'
restart_fifos = False
restart_sockets = False

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
    """
    Returns a list of targets for the given source
    """
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    query = c.execute('''SELECT destination FROM MessageTarget WHERE source=?''', (source,))
    result = query.fetchone()
    ret = json.loads(result[0])
    db_connection.close()
    return ret

def db_target_get_all():
    """ 
    Returns a dict of source(string) -> target(list)
    """
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    query = c.execute('''SELECT source, destination FROM MessageTarget''')
    sources = {}
    for source in query:
        sources[source[0]] = json.loads(source[1])
    db_connection.close()
    return sources

def db_target_redirect(source, target):
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    c.execute('''INSERT OR REPLACE INTO MessageTarget (source, destination) VALUES (?, ?)''', (source, json.dumps(target)))
    db_connection.commit()
    db_connection.close()

def db_source_add(source):
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    c.execute('''INSERT INTO MessageTarget VALUES (?, ?)''', (source + '.fifo', json.dumps(config.senders)))
    c.execute('''INSERT INTO MessageTarget VALUES (?, ?)''', (source + '.socket', json.dumps(config.senders)))
    db_connection.commit()
    db_connection.close()

def db_source_del(source):
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    c.execute('''DELETE FROM MessageTarget WHERE source=?''', (source + '.fifo',))
    c.execute('''DELETE FROM MessageTarget WHERE source=?''', (source + '.socket',))
    db_connection.commit()
    db_connection.close()

def db_source_get(type):
    sources = {}
    db_connection = sqlite3.connect('config.db')
    c = db_connection.cursor()
    query = c.execute('''SELECT source, destination FROM MessageTarget WHERE source LIKE ?''', ('%.{}'.format(type),))
    for source in query:
        sources[source[0]] = source[1]
    db_connection.commit()
    db_connection.close()
    return sources

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
    

def read_and_forward(fd_dict):
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
    rlist, wlist, xlist = select(fd_dict.keys(), [], [], 1)
    for fd in rlist:
        for line in fd:
            source = fd_dict[fd]
            for sender in db_target_get(source):
                if len(line.split()) > 0:
                    log("Sending " + line)
                    send(bot, sender, line)

def read_socket():
    """
    Read messages from the socket.
    """
    # init socket
    global restart_sockets
    while True:
        sockets = db_source_get('socket')
        # cleanup all sockets
        for socket_file in sockets.keys() + glob.glob('*.socket'):
            try:
                os.unlink(socket_file)
            except OSError, e:
                if e.errno == os.errno.ENOENT:
                    pass

        fd_dict = {}
        open_sockets = []
        for socket_file in sockets:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(socket_file)
            os.chmod(socket_file, 0777)
            fd = sock.makefile(os.O_RDONLY)
            fd_dict[fd] = socket_file
            open_sockets.append(sock)

        restart_sockets = False
        while not restart_sockets:
            read_and_forward(fd_dict)

        for fd in fd_dict.keys():
            fd.close()
        for sock in open_sockets:
            sock.shutdown(socket.SHUT_RD)
            sock.close()

def read_fifo():
    """
    Read messages from the FIFO.
    """
    # init fifo.
    # re-create source only if missing or not a fifo.
    # note that removing an existing fifo will make writers block indefinitely.
    global restart_fifos
    while True:
        fifos = db_source_get('fifo')
        # cleanup
        for fifo_file in glob.glob('*.fifo'):
            if fifo_file not in fifos:
                try:
                    os.unlink(fifo_file)
                except OSError, e:
                    if e.errno == os.errno.ENOENT:
                        pass
        # check fifos
        for fifo_file in fifos:
            if not os.path.isfile(fifo_file) or not stat.S_ISFIFO(os.stat(fifo_file).st_mode):
                try:
                    os.unlink(fifo_file)
                except OSError, e:
                    if e.errno == os.errno.ENOENT:
                        pass
                oldmask = os.umask(0)
                os.mkfifo(fifo_file, 0777)
                os.umask(oldmask)
        restart_fifos = False
        while not restart_fifos:
            fo_dict = {}
            for fifo_file in fifos:
                fd = os.open(fifo_file, os.O_RDONLY | os.O_NONBLOCK)
                fo = os.fdopen(fd)
                fo_dict[fo] = fifo_file

            try:
                read_and_forward(fo_dict)
            except IOError:
                pass
            for fo in fo_dict.keys():
                fo.close()

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
    global restart_fifos
    global restart_sockets
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
            # sources is source(string) -> destination(list of id)
            sources = db_target_get_all()
            # targets is destination(string) -> source(list of id)
            targets = {}
            for source in sources.keys():
                for target in sources[source]:
                    source_name = re.sub('\.fifo$', '', source)
                    source_name = re.sub('\.socket$', '', source_name)
                    if target not in targets:
                        targets[target] = []
                    if source_name not in targets[target]:
                        targets[target].append(source_name)

            output = 'Known chats I\'m in:\n'
            for idx, chat in enumerate(all_chats):
                output += '{}: {} ({})'.format(str(idx), chat.name, chat.type)
                if chat.id in targets:
                    output += ' (target of {})'.format(', '.join(targets[chat.id])) 
                output += '\n'
            send(bot, chat_id, output)

      elif command == '/redirect':
            idxs = args[2:]
            source = args[1]
            new_target = []
            for idx in idxs:
                if int(idx) >= len(all_chats):
                    send(bot, chat_id, 'This chat index is out of the range of known chats.')
                else:
                    new_target.append(all_chats[int(idx)])
            if len(new_target) > 0:
                ids = [chat.id for chat in new_target]
                descr = [chat.name + ' (' + chat.type + ')' for chat in new_target]
                db_target_redirect(source + '.fifo', ids)
                db_target_redirect(source + '.socket', ids)
                send(bot, chat_id, 'I\'m switching messages from {} to {}.'.format(source, ', '.join(descr)))

      elif command == '/sourceadd':
            source = args[1]
            if not source.isalnum():
                send(bot, chat_id, 'The source name is not valid. Please only use letters and numbers.')
                return
            db_source_add(source)
            restart_fifos = True
            restart_sockets = True
            send(bot, chat_id, 'Added source {}.'.format(source))
      elif command == '/sourcedel':
            if len(args) < 2:
                send(bot, chat_id, 'Delete what?')
                return
            source = args[1]
            db_source_del(source)
            restart_fifos = True
            restart_sockets = True
            send(bot, chat_id, 'Deleted source {}.'.format(source))

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
