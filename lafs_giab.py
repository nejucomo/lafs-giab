#! /usr/bin/env python

import os
import sys
import argparse
import logging
import subprocess


DESCRIPTION = """
Tahoe-LAFS Grid In A Box - create/configure/start/stop a self-contained set of nodes.
"""


def main(args = sys.argv[1:]):
    opts = parse_args(args)
    opts.run(opts)


def parse_args(args):
    ptop = argparse.ArgumentParser(description=DESCRIPTION)

    ptop.add_argument('--base-dir',
                      dest='basedir',
                      type=str,
                      default=os.path.expanduser('~/.lafs-giab'),
                      help='The base directory which contains node directories.')

    ptop.add_argument('--log-level',
                      dest='loglevel',
                      #default='INFO',
                      default='DEBUG',
                      choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                      help='Set logging level.')

    subps = ptop.add_subparsers(title='Operations')
    subp = subps.add_parser('create', help='Create multiple nodes at once.')
    subp.set_defaults(run=command_create)

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


def command_create(opts):
    raise NotImplementedError('create')


if __name__ == '__main__':
    main()
