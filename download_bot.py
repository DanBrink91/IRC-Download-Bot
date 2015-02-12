import os
import struct
import socket
import sys
import shlex

import irc.client

class DCCReceive(irc.client.SimpleIRCClient):
    """
    Given a queue of objects in specified format, tries to download them one at a time. 
    """
   
    def __init__(self, queue):
        irc.client.SimpleIRCClient.__init__(self)
        self.received_bytes = 0
        self.queue = queue
        # list of bots we're supposed to be downloading from
        self.whitelist = [entry['bot'] for entry in self.queue]
   
    def get_current(self):
        """
        Grabs the next item in the queue
        """
        self.current = self.queue.pop()
        print "Attempting to download %s" % (self.current['filename'])
        
        # self.connection.privmsg(self.current['bot'], 'xdcc list')
        # Run this cancel command to avoid waiting
        # self.connection.privmsg(self.current['bot'], 'xdcc cancel')
        self.connection.privmsg(self.current['bot'], 'xdcc send %s' % self.current['pack_num'])
 
        self.received_bytes = 0
 
    def on_welcome(self, connection, event):
        self.connection.join('#news')
   
    def get_version(self):
        """Returns the bot version.
 
       Used when answering a CTCP VERSION request.
       """
        return "Python irc.bot ({version})".format(
            version=irc.client.VERSION_STRING)
 
 
    # On intial ask for download
    def on_ctcp(self, connection, event):
        nick = event.source.nick
        if event.arguments[0] == 'VERSION':
            connection.ctcp_reply(nick, "VERSION " + self.get_version())
            self.get_current()
            return
        
        # parse it
        payload = event.arguments[1]
        parts = shlex.split(payload)
        command, filename, peer_address, peer_poort, size = parts 
       
        if command != "SEND":
            print command, "not SEND"
            return
        
        # Make sure the person asking us to download is whitelisted
        if nick not in self.whitelist:
            print "%s was not whitelisted. Aborting" % (nick)
            self.get_current()
            return
 
        self.filename = os.path.basename(filename)
        if os.path.exists(self.filename):
            print "A file named", self.filename,
            print "already exists. Refusing to save it."
            self.connection.quit()
       
        self.file = open(self.filename, "w")
        self.filesize = int(size)
        self.dcc = self.dcc_connect(peer_address, int(peer_poort), "raw")
   
       
    # Transfering data
    def on_dccmsg(self, connection, event):
        data = event.arguments[0]
        self.file.write(data)
        
        self.received_bytes = self.received_bytes + len(data)
        self.dcc.send_bytes(struct.pack("!I", self.received_bytes))
        # self.dcc.privmsg(str(self.received_bytes))
 
    # File finished transfering
    def on_dcc_disconnect(self, connection, event):
        self.file.close()
        print "Received file %s (%d bytes)." % (self.filename,
                                                self.received_bytes)
        # Anything left to download?
        if len(self.queue) > 0:
            print "Grabbing Next Item"
            self.get_current()
        else:
            print "Queue finished"
            self.connection.quit()
 
    def on_disconnect(self, connection, event):
        sys.exit(0)
 
def main():
    if len(sys.argv) != 2:
        print "Usage: download_files <input_file>"
        print "\nReceives all files via DCC and then exits.  The files are stored in the"
        print "current directory."
        sys.exit(1)
    # build queue object from input file
    # Input File is of format BOTNAME,PACK_NUM,FILENAME
    queue = []
    
    try:
        input_file = open(sys.argv[1], "r")
    except (FileNotFoundError, IOError), x:
        print x
        sys.exit(1)
   
    for line in input_file:
        line_info = line.split(',')
        queue.append({'bot': line_info[0], 'pack_num':line_info[1], 'filename':line_info[2]})
   
    if len(queue) < 1:
        print "Your input file needs at least one entry, in format: BOTNAME,PACK_NUM,FILENAME"
        sys.exit(1)
   
    server = "irc.rizon.net"
    port = 6667
    nickname = "gotembot-Dan"
 
    c = DCCReceive(queue)
    try:
        c.connect(server, port, nickname)
    except irc.ServerConnectionError, x:
        print x
        sys.exit(1)
    c.start()
 
if __name__ == "__main__":
    main()