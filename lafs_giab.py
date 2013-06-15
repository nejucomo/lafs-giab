#! /usr/bin/env python

import argparse
import errno
import logging
import os
import re
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


def with_log(f):
    """A decorator which injects a logger named after the function."""
    def wrapped(*args, **kw):
        log = logging.getLogger(f.__name__)
        return f(log, *args, **kw)

    wrapped.__name__ = f.__name__
    wrapped.__doc__ = f.__doc__

    return wrapped


def register_command(f, name=None):
    """Add command function f to CommandTable; may be used as a decorator."""
    if name is None:
        name = f.__name__

    CommandTable[name] = f
    return f


@register_command
@with_log
def launch(log, opts, paths):
    """Start all nodes, creating and configuring each from scratch if necessary."""

    makedir_if_necessary(opts.basedir)
    make_node_if_necessary(paths, 'introducer')
    start_node(paths, 'introducer')

    if make_node_if_necessary(paths, 'node'):
        introfurl = poll_read_introducer_furl(paths)
        configure_storage_node(paths, introfurl)

    start_node(paths, 'node')


@with_log
def make_node_if_necessary(log, paths, nodename):
    nodepath = getattr(paths, nodename)
    if makedir_if_necessary(nodepath):
        log.info('Creating %s', nodename)
        run('tahoe', 'create-' + nodename, nodepath)
        return True
    else:
        return False


@with_log
def start_node(log, paths, nodename):
    nodepath = getattr(paths, nodename)

    log.info('Starting %s', nodename)
    run('tahoe', 'start', '--basedir', nodepath)


@with_log
def poll_read_introducer_furl(log, paths):
    introfurlpath = os.path.join(paths.introducer, 'private', 'introducer.furl')

    opened = False
    while not opened:
        log.debug('Waiting for %r', introfurlpath)
        time.sleep(1)
        (opened, f) = std_try(errno.ENOENT, open, introfurlpath, 'rb')

    with f:
        introfurl = f.read().strip()

    log.debug('Found introducer.furl: %r', introfurl)
    return introfurl


INTRODUCER_CFG_RGX = re.compile(r'^introducer\.furl = None$', re.MULTILINE)
ENCODING_CFG_RGX = re.compile(r'^#shares\.(needed|happy|total) = \d+$', re.MULTILINE)

class ConfigurationFailure (Exception): pass


@with_log
def configure_storage_node(log, paths, introfurl):
    log.info('Reconfiguring node %r', paths.node)
    cfgpath = os.path.join(paths.node, 'tahoe.cfg')

    with file(cfgpath, 'r') as f:
        cfgtext = f.read()

    def replace_introducer(m):
        replacement = 'introducer.furl = ' + introfurl
        log.debug('Replacing introducer %r with %r', m.groups(), replacement)
        return replacement

    (cfgtext, repls) = INTRODUCER_CFG_RGX.subn(replace_introducer, cfgtext)
    if repls != 1:
        raise ConfigurationFailure(
            'Failed to configure the storage node introducer; the config file had an unexpected format.')


    def replace_encoding(m):
        replacement = 'shares.%s = 1' % (m.group(1),)
        log.debug('Replacing encoding parameter %r %r with %r', m.group(), m.groups(), replacement)
        return replacement

    (cfgtext, repls) = ENCODING_CFG_RGX.subn(replace_encoding, cfgtext)
    if repls != 3:
        raise ConfigurationFailure(
            'Failed to configure the storage node encodings; the config file had an unexpected format.')

    with file(cfgpath, 'w') as f:
        f.write(cfgtext)



def register_standard_dispatch_command(commandname):

    @with_log
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



@with_log
def run(log, command, *args):
    argv = (command,) + args

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
