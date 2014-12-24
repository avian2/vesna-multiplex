VESNA TCP connection multiplexer
================================

This utility multiplexes a single TCP connection to multiple clients. The
intended use is to allow multiple processes to connect to a single VESNA
node, since hardware limitations prevent a node from serving more than one
network client. In picture::

    .                                           +--------+
    .                                        -->| client |
    .                  +-----------------+  /   +--------+
    .   +-------+      |                 |--    +--------+
    .   | VESNA |----->| vesna_multiplex |----->| client |
    .   +-------+      |                 |--    +--------+
    .                  +-----------------+  \   +--------+
    .                                        -->| client |
    .                                           +--------+
    .
    .                 <- west     east ->

The multiplexer makes as few assumptions as possible regarding the protocol
used between the sensor node and clients.

For data received from the node and flowing east, the multiplexer makes
byte-by-byte copies for each connected client. This means that, for
example, periodic sensor reports will be received by all clients.

For data flowing east-to-west, multiplexer assumes that protocol is line
oriented. It passes each complete line (\n terminated) it receives from any
client to the node. Typically, only one client will issue commands to the
node at the time. It is up to the clients to synchronize their commands as
necessary.

The multiplexer also recognizes some lines as commands for itself.
Responses to those commands are sent back to the client that sent them and
are not replicated to the node or other clients.


Security considerations
-----------------------

The sensor node has no capability to authenticate itself against the
multiplexer, hence anyone on the network that knows multiplexer's IP and
port can connect to it and impersonate the sensor node.

Similarly, since most clients expect to connect directly to the sensor node
they have no concept of authentication. Anyone on the network that knows
multiplexer's IP and port can connect and impersonate a client.

It is HIGHLY RECOMMENDED to only run the multiplexer on a secure network.


Multiplexer commands
--------------------

?ping
  Responds with "ok". Can be used by clients to check whether a multiplexer
  is present on the connection.

?count east
  Responds with the number of currently open eastward connections, followed
  by "ok". This is the number of connected clients.

?count west
  Responds with the number of currently open westward connections, followed
  by "ok". This is the number of connected nodes (typically <= 1).


Installation
------------

Run these commands::

    python setup.py install
    python setup.py test


Usage
-----

After installing, run the multiplexer with the following command::

    vesna_multiplex

By default, multiplexer listens for eastward connections (clients) on port
2101 and for westward connections (node) on port 2201. Clients can connect
only from localhost, while node can connect from any network interface. You
can change these defaults with command line arguments. See --help.

The sensor node should be configured to "Automatically establish TCP
connections" to the multiplexer's IP and port. Set to "Always connect and
maintain connection" and select "Raw TCP" as service type. Also, it is
recommended to disable "Raw TCP" under "Network Services".

Press ctrl-C once (or send SIGTERM) to gracefully stop the multiplexer.


Source
------

The latest version is available on GitHub:
https://github.com/avian2/vesna-multiplex


License
-------

Copyright (C) 2014 SensorLab, Jozef Stefan Institute

Written by Tomaz Solc, <tomaz.solc@ijs.si>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.

..
    vim: tw=75 ts=4 sw=4 expandtab softtabstop=4
