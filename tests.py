from mock import Mock
from nose.tools import eq_, ok_

from ezbot import IRC


def conn():
    i = IRC('testhost')
    i._sock = Mock()

    return i


def test_register_hooks():
    c = conn()

    r = '^test'
    f = lambda x: x

    c.register_init_hook(f)
    c.register_chanmsg_hook(r, f)
    c.register_privmsg_hook(r, f)

    ok_(f in c._init_hooks)
    ok_((r, f) in c._chanmsg_hooks)
    ok_((r, f) in c._privmsg_hooks)


def test_process():
    c = conn()

    r = '^(test.*)'
    f = lambda w, c_, m: c.send('PRIVMSG %s :%s' % (w, m))

    c.register_chanmsg_hook(r, f)
    c.register_privmsg_hook(r, f)

    c._process('PING id')
    c._sock.sendall.assert_called_with('PONG id\r\n')

    assert c._registered == False
    c._process(':testhost.test.com 001')
    assert c._registered == True

    c._process(':testuser!testhsot.test.com '
               'PRIVMSG #testchannel :test message')
    c._process(':testuser2!testhsot.test.com '
               'PRIVMSG testuser :test message')
    c._sock.sendall.assert_called_with('PRIVMSG testuser2 :test message\r\n')


def test_join_channel():
    c = conn()
    c._registered = True
    c.join_channel('#testchannel')
    c._sock.sendall.assert_called_with('JOIN #testchannel\r\n')
