import socket
import time
import sys
import re
import threading

CONFIG = {
    'host': 'irc.twitch.tv',
    'port': 6667,

    # Informacje potrzebne do zalogowania bota na czacie
    # Bot potrzebuje moderatora do poprawnego działania
    'username': 'ShadowDuckBot',
    'password': '', # Hasło trzeba wygenerować na stronie http://twitchapps.com/tmi/

    # Kanał do którego chcesz się zalogować
    'channel': '',

    # Czas trwania głosowania w sekundach
    'poll_duration': 30,
    # Powiadomienie o pozostałym czasie (jeżeli usuniesz 0 wtedy głosowanie nie zakończy się)
    'poll_notify': [1, 2/3, 1/3, 0],

    # Polecenia (możesz je modyfikować przez zmianę np !start -> !pollstart)
    # W permission muszą być nicki osób, które mogą wydawać te polecenia np ['test1', 'test2']
    'commands': [
        {
            # Rozpocznij głosowanie
            '!start': {
                'command': 'command_start_poll',
                'permission': ['']
            },
            # Zakończ głosowanie
            '!stop': {
                'command': 'command_stop_poll',
                'permission': ['']
            },
            # Wypisz wynik
            '!result': {
                'command': 'command_result',
                'permission': ['']
            },
        },
        {
            # możesz też zmienić komendy głosowania np !1 -> !nr1
            '!1': 1,
            '!2': 2,
            '!3': 3,
        }
    ]

}


class IRCBot:

    def __init__(self, config):
        self.config = config
        self.irc = self.IRCClient(config)
        self.sock = self.irc.get_irc_socket()
        self.poll = self.Poll(config)

    def command_start_poll(self):
        self.poll.start()
        self.irc.send_message(self.config['channel'], 'Głosowanie rozpoczęte')
        self.irc.send_message(self.config['channel'], 'Wpisz !1, !2 lub !3')

    def command_stop_poll(self):
        self.poll.stop()
        self.irc.send_message(self.config['channel'], 'Głosowanie zakończone')
        self.command_result()

    def command_result(self):
        sum = self.poll.result[0]
        nr1 = self.poll.result[1]
        nr2 = self.poll.result[2]
        nr3 = self.poll.result[3]
        if sum == 0:
            sum += 1
        self.irc.send_message(self.config['channel'], 'nr1: {:.1f}% ({}), nr2: {:.1f}% ({}), nr3: {:.1f}% ({})'.format(nr1/sum*100, nr1, nr2/sum*100, nr2, nr3/sum*100, nr3))

    def run(self):
        irc = self.irc
        sock = self.sock

        data = ''

        time_poll_checker = threading.Thread(target=self.check_poll_duration, args=())
        time_poll_checker.deamon = True
        time_poll_checker.start()

        while True:
            try:
                data += sock.recv(2048).decode('UTF-8')
                data_split = re.split(r"[~\r\n]+", data)
                data = data_split.pop()

                for line in data_split:
                    line = str.rstrip(line)
                    line = str.split(line)

                    if len(line) >= 1:
                        if line[0] == 'PING':
                            irc.send_pong(line[1])

                        if line[1] == 'PRIVMSG':
                            message_dict = irc.get_message_dict(line)
                            self.parse_message(message_dict)

            except socket.error:
                IRCBot.Helper.pp("ERROR")

            except socket.timeout:
                IRCBot.Helper.pp("TIMEOUT")

    def parse_message(self, message_dict):
        message = message_dict['message']
        username = message_dict['username']
        if len(message) >= 1:
            message = message.split(' ')
            options = self.config['commands']
            if message[0] in options[0]:
                if 'permission' in options[0][message[0]]:
                    if username in [user.lower() for user in options[0][message[0]]['permission']]:
                        getattr(IRCBot, options[0][message[0]]['command'])(self)
                else:
                    getattr(IRCBot, options[0][message[0]]['command'])(self)
            elif message[0] in options[1]:
                self.poll.vote(username, options[1][message[0]])

    def check_poll_duration(self):
        while True:
            if self.poll.is_active:
                if time.time() - self.poll.start_time > self.poll.duration * (1 - self.poll.notify[self.poll.notify_index]):
                    if self.poll.notify[self.poll.notify_index] == 0:
                        self.command_stop_poll()
                    else:
                        self.irc.send_message(self.config['channel'], 'Do końca głosowania pozostało {0:.0f}s'.format(self.poll.duration * self.poll.notify[self.poll.notify_index]))
                        self.command_result()
                    self.poll.notify_index += 1
            time.sleep(0.01)

    class IRCClient:

        def __init__(self, config):
            self.config = config

        def send_pong(self, message):
            self.sock.send(bytes('PONG %s\r\n' % message, 'UTF-8'))

        def send_message(self, channel, message):
            self.sock.send(bytes('PRIVMSG %s :%s\r\n' % (channel, message), 'UTF-8'))
            IRCBot.Helper.pp(message)

        def get_irc_socket(self):
            sock = socket.socket()
            sock.settimeout(10)

            try:
                sock.connect((self.config['host'], self.config['port']))
            except:
                IRCBot.Helper.pp('Nie można połączyć sie z serwerem (%s:%s).' % (self.config['host'], self.config['port']), 'error')
                sys.exit()

            sock.settimeout(None)

            sock.send(bytes('USER %s\r\n' % self.config['username'], 'UTF-8'))
            sock.send(bytes('PASS %s\r\n' % self.config['password'], 'UTF-8'))
            sock.send(bytes('NICK %s\r\n' % self.config['username'], 'UTF-8'))

            if self.check_login_status(sock.recv(1024).decode('UTF-8')):
                IRCBot.Helper.pp('Zalogowano poprawnie')
            else:
                IRCBot.Helper.pp('Błąd w logowaniu (Prawdopodobnie trzeba wygenerować ponownie hasło)')
                sys.exit()

            sock.send(bytes('JOIN %s\r\n' % self.config['channel'].lower(), 'UTF-8'))
            IRCBot.Helper.pp('Połączono z kanałem %s.' % self.config['channel'])

            self.sock = sock

            return sock

        def get_message_dict(self, message):
            return {
                'channel': message[2],
                'username': self.get_sender(message[0]),
                'message': self.get_message(message)
            }

        def get_sender(self, message):
            result = ""
            for char in message:
                if char == "!":
                    break
                if char != ":":
                    result += char
            return result

        def get_message(self, message):
            result = ""
            i = 3
            length = len(message)
            while i < length:
                result += message[i] + " "
                i += 1
            result = result.lstrip(':')
            return result

        def check_login_status(self, data):
            if re.match(r'^:tmi\.twitch\.tv NOTICE \* :Error logging in\r\n$', data):
                return False
            else:
                return True

    class Helper:

        @classmethod
        def pp(cls, message):

            print('[%s] %s' % (time.strftime('%H:%M:%S', time.localtime()), message))

    class Poll:

        def __init__(self, config):
            self.deafult_duration = config['poll_duration']
            self.notify = config['poll_notify']
            self.reset()

        def reset(self):
            self.start_time = 0
            self.is_active = False
            self.result = [0, 0, 0, 0]
            self.users_list = []
            self.notify_index = 0

        def vote(self, username, option):
            if self.is_active:
                if username not in self.users_list:
                    self.result[option] += 1
                    self.result[0] += 1
                    self.users_list.append(username)

        def start(self, duration=None):
            self.reset()
            if duration:
                self.duration = duration
            else:
                self.duration = self.deafult_duration
            self.start_time = time.time()
            self.is_active = True

        def stop(self):
            self.is_active = False


bot = IRCBot(CONFIG).run()
