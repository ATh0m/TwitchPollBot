#!/usr/bin/env python3

import re
import socket
import time
import threading

# --------------------------------------------- Start Settings -----------
# Hostname of the IRC-Server in this case twitch's
HOST = "irc.twitch.tv"
PORT = 6667                                     # Default IRC-Port
CHAN = "#mkrr3"                         # Channelname = #{Nickname}
NICK = "ShadowDuckBot"                          # Nickname = Twitch username
# www.twitchapps.com/tmi/ will help to retrieve the required authkey
PASS = "oauth:nibflmpyef6gr4zjszkye6pb52carl"
# --------------------------------------------- End Settings -------------

poll_start_time = 0
is_poll_active = False
start_poll_time = 0
poll = [0, 0]

# --------------------------------------------- Start Functions ----------


def send_pong(msg):
    con.send(bytes('PONG %s\r\n' % msg, 'UTF-8'))


def send_message(chan, msg):
    con.send(bytes('PRIVMSG %s :%s\r\n' % (chan, msg), 'UTF-8'))
    print(msg)


def send_nick(nick):
    con.send(bytes('NICK %s\r\n' % nick, 'UTF-8'))


def send_pass(password):
    con.send(bytes('PASS %s\r\n' % password, 'UTF-8'))


def join_channel(chan):
    con.send(bytes('JOIN %s\r\n' % chan, 'UTF-8'))


def part_channel(chan):
    con.send(bytes('PART %s\r\n' % chan, 'UTF-8'))
# --------------------------------------------- End Functions ------------


# --------------------------------------------- Start Helper Functions ---
def get_sender(msg):
    result = ""
    for char in msg:
        if char == "!":
            break
        if char != ":":
            result += char
    return result


def get_message(msg):
    result = ""
    i = 3
    length = len(msg)
    while i < length:
        result += msg[i] + " "
        i += 1
    result = result.lstrip(':')
    return result


def parse_message(msg):
    if len(msg) >= 1:
        msg = msg.split(' ')
        options = {'!test': command_test,
                   '!asdf': command_asdf,
                   '!start': command_start,
                   '!stop': command_stop,
                   '!1': command_1,
                   '!2': command_2}
        if msg[0] in options:
            options[msg[0]]()


def check_poll_time():
    while True:
        if is_poll_active:
            if time.time() - start_poll_time > 30:
                print(time.time(), " ", start_poll_time)
                command_stop()
        time.sleep(0.01)

# --------------------------------------------- End Helper Functions -----


# --------------------------------------------- Start Command Functions --
def command_test():
    send_message(CHAN, 'testing some stuff')


def command_asdf():
    send_message(CHAN, 'asdfster')


def command_start():
    global is_poll_active, poll, start_poll_time
    is_poll_active = True
    start_poll_time = time.time()
    poll = [0, 0]
    send_message(CHAN, 'Głosowanie rozpoczęte o ' +
                 time.strftime("%H:%M:%S", time.localtime(start_poll_time)))


def command_stop():
    global is_poll_active
    is_poll_active = False
    send_message(CHAN, 'Głosowanie zakończone')
    send_message(CHAN, "v1: {0} v2: {1}".format(poll[0], poll[1]))


def command_1():
    if is_poll_active:
        poll[0] += 1


def command_2():
    if is_poll_active:
        poll[1] += 1
# --------------------------------------------- End Command Functions ----

con = socket.socket()
con.connect((HOST, PORT))

send_pass(PASS)
send_nick(NICK)
join_channel(CHAN)

data = ""

t = threading.Thread(target=check_poll_time)
t.deamon = True
t.start()

while True:

    try:
        data = data + con.recv(1024).decode('UTF-8')
        data_split = re.split(r"[~\r\n]+", data)
        data = data_split.pop()

        for line in data_split:
            line = str.rstrip(line)
            line = str.split(line)

            if len(line) >= 1:
                if line[0] == 'PING':
                    send_pong(line[1])

                if line[1] == 'PRIVMSG':
                    sender = get_sender(line[0])
                    message = get_message(line)
                    parse_message(message)

                    print(sender + ": " + message)

    except socket.error:
        print("Socket died")

    except socket.timeout:
        print("Socket timeout")
