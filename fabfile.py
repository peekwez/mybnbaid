import collections
from fabric import task, Connection

import rock as rk


@task(hosts=['mybnbaid'])
def test(c):
    r = c.run('ls')
    print(r.stdout)


@task(hosts=['local'])
def supervisor(c, conf='config.yml'):
    c.run('ls')
    print(writer)
