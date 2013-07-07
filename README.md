The `lafs-giab` script simplifies creating and starting a
[Tahoe-LAFS](https://tahoe-lafs.org) *grid in a box*.

# Grid In A Box

The term *grid in a box* implies that the grid is merely local and
probably transient.  I use this when I want to quickly start interactively
experimenting with Tahoe-LAFS, but I do not necessarily want to go to
the trouble of connecting to an existing grid.

The `lafs-giab` script creates and manages Tahoe-LAFS nodes whose
configuration directories live inside a single parent directory specified
by the `--dir` option (which defaults to `~/.lafs-giab`).

When creating nodes, it creates an introducer and a single storage node.
It also reconfigures the storage node to have the introducer's `furl`
and to set the encoding parameters to `K = N = 1`.  This means there will
be a single share per file or directory stored through the node's webapi
(or any other front-end like the commandline client).  Since the intended
use is for testing front-end usage, there's no redundancy or off-site
backup support.

It is implemented by calling to the `tahoe` command in subprocesses.

## Dependencies

A somewhat recent version of [Python](https://python.org) and a version of
[Tahoe-LAFS](https://tahoe-lafs.org) of version 1.10 or greater.
