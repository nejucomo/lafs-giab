#! /usr/bin/env python

import argparse
import errno
import logging
import os
import subprocess
import sys
import time


DESCRIPTION = """
Tahoe-LAFS Grid In A Box - create/configure/start/stop a self-contained set of nodes.
"""


def main(args = sys.argv[1:]):
    opts = parse_args(args)
    paths = NodePaths(opts.basedir)
    opts.run(opts, paths)


# This global is populated at module load time below:
CommandTable = {}


def parse_args(args):
    ptop = argparse.ArgumentParser(description=DESCRIPTION)

    ptop.add_argument('--dir', '-d',
                      dest='basedir',
                      type=str,
                      required=True,
                      #default=os.path.expanduser('~/.lafs-giab'),
                      help='The base directory which contains node directories.')

    ptop.add_argument('--log-level',
                      dest='loglevel',
                      #default='INFO',
                      default='DEBUG',
                      choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                      help='Set logging level.')

    subps = ptop.add_subparsers(title='Operations')

    for cmdname, cmdfunc in sorted(CommandTable.items()):
        subp = subps.add_parser(cmdname, help=cmdfunc.__doc__)
        subp.set_defaults(run=cmdfunc)

    opts = ptop.parse_args(args)

    logging.basicConfig(
        stream=sys.stdout,
        format='%(asctime)s %(levelname) 5s %(name)s | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        level=getattr(logging, opts.loglevel))

    log = logging.getLogger('options')
    optvars = dict(vars(opts))
    runname = optvars.pop('run').__name__
    log.debug('%r %r', runname, optvars)

    return opts



class NodePaths (object):

    Names = ['introducer', 'node']

    def __init__(self, basedir):
        for name in self.Names:
            setattr(self, name, os.path.join(basedir, name))


def register_command(f, name=None):
    """Add command function f to CommandTable; may be used as a decorator."""
    if name is None:
        name = f.__name__

    def log_wrapper(*args):
        log = logging.getLogger(name)
        return f(log, *args)

    log_wrapper.__doc__ = f.__doc__

    CommandTable[name] = log_wrapper

    return log_wrapper


@register_command
def launch(log, opts, paths):
    """Start all nodes, creating and configuring each from scratch if necessary."""

    makedir_if_necessary(opts.basedir)
    if makedir_if_necessary(paths.introducer):
        log.info('Creating introducer')
        run('tahoe', 'create-introducer', paths.introducer)
    log.info('Starting introducer')
    run('tahoe', 'start', '--basedir', paths.introducer)

    introfurlpath = os.path.join(paths.introducer, 'private', 'introducer.furl')

    opened = False
    while not opened:
        log.debug('Waiting for %r', introfurlpath)
        time.sleep(1)
        (opened, f) = std_try(errno.ENOENT, open, introfurlpath, 'rb')

    with f:
        introfurl = f.read()

    log.info('Found introducer.furl: %r', introfurl)

    raise NotImplementedError()



def register_standard_dispatch_command(commandname):

    def cmd_impl(log, opts, paths):

        for name in paths.Names:
            path = getattr(paths, name)

            log.info('%s %s', name, commandname)
            run('tahoe', commandname, '--basedir', path)

    cmd_impl.__doc__ = 'Run "tahoe %s" on each node directory.' % (commandname,)

    register_command(cmd_impl, commandname)


for cmdname in ['start', 'stop', 'restart']:
    register_standard_dispatch_command(cmdname)

del cmdname



def run(command, *args):
    argv = (command,) + args

    log = logging.getLogger('command %r' % (command,))
    log.debug('Running: %r', argv) # Wishlit: escape for /bin/sh cut'n'paste compatibility.

    proc = subprocess.Popen(args=argv)
    log.debug('PID: %r', proc.pid)

    status = proc.wait()
    log.debug('Exit Status: %r', status)

    if status != 0:
        raise SystemExit(status)



def makedir_if_necessary(path):
    (new, _) = std_try(errno.EEXIST, os.mkdir, path)
    if new:
        logging.debug('Created directory: %r', path)
    return new



def std_try(errcode, f, *args):
    try:
        result = f(*args)
    except os.error, e:
        if e.errno == errcode:
            return (False, None)
        else:
            raise
    return (True, result)



if __name__ == '__main__':
    main()
