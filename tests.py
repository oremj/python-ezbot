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
    f = lambda: c.send('testmsg', True)

    c.register_init_hook(f)
    c.register_chanmsg_hook(r, f)
    c.register_privmsg_hook(r, f)

    ok_(f in c._init_hooks)
    ok_((r, f) in c._chanmsg_hooks)
    ok_((r, f) in c._privmsg_hooks)

    
    c._run_init_hooks()
    c._sock.sendall.assert_called_with('testmsg\r\n')

def test_process():
    c = conn()

    r = '^(test.*)'
    f = lambda w, c_, m: c.send('PRIVMSG %s :%s' % (w, m))

    c.register_chanmsg_hook(r, f)
    c.register_privmsg_hook(r, f)

    c._process('PING id')
    c._sock.sendall.assert_called_with('PONG id\r\n')

    assert c._registered == False
    c._sock.sendall.reset_mock()
    c.send('testmsg')
    assert c._sock.sendall.call_count == 0
    c._process(':testhost.test.com 001')
    assert c._registered == True
    c._sock.sendall.assert_called_with('testmsg\r\n')

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


def test_readline():
    c = conn()
    c._sock.recv.return_value = "test1\ntest2\n"
    assert c._readline() == "test1"
    assert c._readline() == "test2"


def test_auth():
    c = conn()
    c._registered = True
    c._auth('testuser')
    c._sock.sendall.assert_any_call('NICK testuser\r\n')
    c._sock.sendall.assert_called_with('USER testuser testhost foo :testuser\r\n')
