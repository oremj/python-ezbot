import logging
import re
import socket
from threading import Lock


def configure_logging():
    log = logging.getLogger('irc')
    log_handler = logging.StreamHandler()
    log_handler.setLevel(logging.DEBUG)
    log.addHandler(log_handler)
    log.setLevel(logging.DEBUG)


configure_logging()
log = logging.getLogger('irc')


class Bot(object):

    def __init__(self, nick, channels, host, port=6667):
        self.conn = IRC(host, port)
        self.channels = channels
        self.nick = nick

        for h in self._chanmsg_hooks():
            self.conn.register_chanmsg_hook(*h)
        for h in self._privmsg_hooks():
            self.conn.register_chanmsg_hook(*h)

        self.conn.register_init_hook(self.init_hook)

    def init_hook(self):
        """This runs after auth is complete and channels have been joined"""
        log.debug("Bot initialized")

    def _chanmsg_hooks(self):
        """These run on every channel message:
           should return a list of tuples e.g., [('^!command', self.command)]
        """
        return []

    def _privmsg_hooks(self):
        """These run on every private message:
           should return a list of tuples e.g., [('^!command', self.command)]
        """
        return []

    def run(self):
        """Start the bot. Will initialize infinite recv loop"""
        self.conn.connect()
        self.conn.loop(self.nick, self.channels)

    def send_to(self, who, msg):
        """Sends message to channel or user."""
        self.conn.send('PRIVMSG %s :%s' % (who, msg))


class IRC(object):

    def __init__(self, host, port=6667):
        self.host = host
        self.port = port

        self._recv_buf = None
        self._send_buf = []

        self._registered = False

        self._chanmsg_hooks = []
        self._init_hooks = []
        self._privmsg_hooks = []

        self._send_lock = Lock()

        self.hooks = [
            (re.compile('^PING (.*)'), self._handle_ping),
            (re.compile('^:(\S+)!.+? PRIVMSG (#\S+) :(.+)'),
             self._handle_chanmsg),
            (re.compile('^:(\S+)!.+? PRIVMSG [^#].+? :(.+)'),
             self._handle_privmsg),
            (re.compile('^:\S+ 001'), self._handle_register),
        ]

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.host, self.port))

    def register_init_hook(self, f):
        self._init_hooks.append(f)

    def register_chanmsg_hook(self, pattern, f):
        self._chanmsg_hooks.append((pattern, f))

    def register_privmsg_hook(self, pattern, f):
        self._privmsg_hooks.append((pattern, f))

    def _run_command_hooks(self, hooks, who, channel, line):
        for p, f in hooks:
            m = re.search(p, line)
            if m:
                f(who, channel, *m.groups())

    def _process(self, line):
        log.debug("processing: %s" % line)
        for p, f in self.hooks:
            m = re.search(p, line)
            if m:
                f(*m.groups())

    def _handle_privmsg(self, who, msg):
        logging.debug("privmsg: %s" % msg)
        self._run_command_hooks(self._privmsg_hooks, who, None, msg)

    def _handle_chanmsg(self, who, channel, msg):
        logging.debug("chanmsg: %s" % msg)
        self._run_command_hooks(self._chanmsg_hooks, who, channel, msg)

    def _handle_ping(self, payload):
        self.send('PONG %s' % payload, True)

    def _flush_send_buf(self):
        for l in self._send_buf:
            self.send(l)

    def _handle_register(self):
        self._registered = True
        self._flush_send_buf()

    def send(self, line, pre_reg=False):
        if pre_reg or self._registered:
            log.debug("sending: %s" % line)
            with self._send_lock:
                self._sock.sendall("%s\r\n" % line)
        else:
            self._send_buf.append(line)

    def _readline(self):
        if self._recv_buf == None:
            self._recv_buf = self._recvlines()

        return self._recv_buf.next()

    def _recvlines(self):
        buf = ""
        while True:
            buf += self._sock.recv(4096)
            while '\n' in buf:
                line, buf = buf.split('\n', 1)
                yield line

    def _run_init_hooks(self):
        for h in self._init_hooks:
            h()

    def _auth(self, nick):
        self.send('NICK %s' % nick, True)
        self.send('USER %s %s foo :%s' % (nick, self.host, nick), True)

    def join_channel(self, channel):
        self.send('JOIN %s' % channel)

    def loop(self, nick, channels):
        self._auth(nick)

        for c in channels:
            self.join_channel(c)

        self._run_init_hooks()
        while True:
            self._process(self._readline())
