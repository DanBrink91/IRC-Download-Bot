import os
import struct
import socket
import sys
import shlex

import irc.client

import settings

class DCCReceive(irc.client.SimpleIRCClient):
    """
    Given a queue of objects in specified format, tries to download them one at a time. 
    """
   
    def __init__(self, queue):
        irc.client.SimpleIRCClient.__init__(self)
        
        # dictionary BotName -> Object containing File and DCC info for the download
        self.downloads = {}
        
        # dictionary IP Address -> Bot, also gives us free whitelisting!
        self.dcc_to_bot = {}

        self.queue = queue

    def get_next(self):
        """
        Grabs the next item(s) from the queue to be downloaded
        """
        recently_added = []
        # fill download queue, be sure not to let the same bot download two things at same time
        for i in range(min(settings.MAX_DOWNLOADS - len(self.downloads), len(queue))):
            # cant use for..in here because the list shrinks when we pop stuff!
            j = 0
            while j < len(queue):
                if queue[j]['bot'] not in [downloading_bot for downloading_bot in self.downloads.keys()]:
                    to_add = queue.pop(j)
                    self.downloads[to_add['bot']] = {'received_bytes':0}
                    recently_added.append(to_add)
                else:
                    j += 1
        # Start downloads for anything that was just added
        for added_download in recently_added:
            print "Attempting to download %s" % (added_download['filename'])
            
            # Run this cancel command to avoid waiting
            self.connection.privmsg(added_download['bot'], 'XDCC CANCEL')
            self.connection.privmsg(added_download['bot'], 'XDCC SEND %s' % added_download['pack_num'])
  
    def on_welcome(self, connection, event):
        self.connection.join(settings.CHANNEL)
   
    def get_version(self):
        """Returns the bot version.
 
       Used when answering a CTCP VERSION request.
       """
        return "Python irc.bot ({version})".format(
            version=irc.client.VERSION_STRING)
    
    # print out any private notices we get
    def on_privnotice(self, connection, event):
        print event.source.nick, event.arguments
    
    # On intial ask for download
    def on_ctcp(self, connection, event):
        nick = event.source.nick
        if event.arguments[0] == 'VERSION':
            connection.ctcp_reply(nick, "VERSION " + self.get_version())
            self.get_next()
            return
        
        # parse it
        payload = event.arguments[1]
        parts = shlex.split(payload)
        try:
            command, filename, peer_address, peer_poort, size = parts 
        except ValueError:
            print "args: ", event.arguments[1]
            print "parts: ", parts
        if command != "SEND":
            print command, "not SEND"
            return
        
        # Try to  use preffered download path        
        if os.path.exists(settings.DOWNLOAD_PATH):
            self.filename = os.path.join(settings.DOWNLOAD_PATH, os.path.basename(filename))
        else:
            print "Download location %s was not found, defaulting to local directory" % (settings.DOWNLOAD_PATH)
            self.filename = os.path.basename(filename)
        
        # Check if file already exits
        # TODO check if file needs to be resumed
        if os.path.exists(self.filename):
            print "A file named", self.filename,
            print "already exists. Refusing to save it."
            del self.downloads[nick]
            self.connection.privmsg(nick, 'XDCC CANCEL')
            self.get_next()
            return
        
        self.downloads[nick]['file'] = open(self.filename, "w")
        self.downloads[nick]['filesize'] = int(size)
        self.downloads[nick]['dcc'] = self.dcc_connect(peer_address, int(peer_poort), "raw")
        # Save Address -> Nick conversion so we can use it later
        self.dcc_to_bot[self.downloads[nick]['dcc'].peeraddress] = nick
       
    # Transfering data
    def on_dccmsg(self, connection, event):
        nick = self.dcc_to_bot[event.source]
        data = event.arguments[0]
        self.downloads[nick]['file'].write(data)
        
        self.downloads[nick]['received_bytes'] = self.downloads[nick]['received_bytes'] + len(data)
        self.downloads[nick]['dcc'].send_bytes(struct.pack("!I", self.downloads[nick]['received_bytes']))
 
    # File finished transfering
    def on_dcc_disconnect(self, connection, event):
        nick = self.dcc_to_bot[event.source]
        self.downloads[nick]['file'].close()
        print "Received file from %s (%d bytes)." % (nick,
                                                self.downloads[nick]['received_bytes'])
        del self.downloads[nick]
        # Anything left to download?
        if len(self.queue) > 0:
            print "Grabbing Next Item"
            self.get_next()
        elif len(self.downloads) == 0:
            print "Queue finished"
            self.connection.quit()
 
    def on_disconnect(self, connection, event):
        sys.exit(0)

if __name__ == "__main__":
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

    c = DCCReceive(queue)
    try:
        c.connect(settings.SERVER, settings.PORT, settings.BOT_NICKNAME)
    except irc.ServerConnectionError, x:
        print x
        sys.exit(1)
    c.start()

