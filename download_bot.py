import os
import struct
import socket
import sys
import shlex
import sqlite3

import irc.client

import settings

def bytes_to_human_string(num_bytes):
    """
    Helper function to convert bytes (number) into bytes, kb, mb, or gb string.
    """
    if num_bytes > 1024:
        kb = num_bytes / 1024.0
        if kb > 1024:
            mb = kb / 1024.0
            if mb > 1024:
                gb = kb / 1024.0
                return "%.2f gb" % gb
            else:
                return "%.2f mb" % mb 
        else:
            return "%.2f kb" % kb
    else:
        return "%d bytes" % num_bytes

class DCCReceive(irc.client.SimpleIRCClient):
    """
    Given a queue of objects in specified format, tries to download them. 
    """
   
    def __init__(self, queue, cursor):
        irc.client.SimpleIRCClient.__init__(self)
        
        # dictionary BotName -> Object containing File and DCC info for the download
        self.downloads = {}
        
        # dictionary IP Address -> Bot, also gives us free whitelisting!
        self.dcc_to_bot = {}

        self.queue = queue
        self.cur = cursor

    def get_next(self):
        """
        Grabs the next item(s) from the queue to be downloaded
        """
        recently_added = []
        # fill download queue, be sure not to let the same bot download two things at same time
        for i in range(min(settings.MAX_DOWNLOADS - len(self.downloads), len(queue))):
            #
            for j in range(len(queue)):
                if queue[j]['bot'] not in [downloading_bot for downloading_bot in self.downloads.keys()]:
                    to_add = queue.pop(j)
                    self.downloads[to_add['bot']] = {
                     'received_bytes':0,
                     'episode_id': to_add['id'],
                     'series_title': to_add['series_title'],
                     'display_name': to_add['series_title'] + ' - ' + str(to_add['episode_number'])
                     }
                    recently_added.append(to_add)
                    break
        # Start downloads for anything that was just added
        for added_download in recently_added:
            print "Attempting to download %s" % (added_download['series_title'] + ' - ' + str(added_download['episode_number']))
            
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
            return
        if command != "SEND":
            print command, "not SEND"
            return
        
        # Try to  use preffered download path        
        if os.path.exists(settings.DOWNLOAD_PATH):
            if not os.path.exists(os.path.join(settings.DOWNLOAD_PATH, self.downloads[nick]['series_title'])):
                os.makedirs(os.path.join(settings.DOWNLOAD_PATH, self.downloads[nick]['series_title']))
            filename = os.path.join(settings.DOWNLOAD_PATH, self.downloads[nick]['series_title'], os.path.basename(filename))
        else:
            print "Download location %s was not found, defaulting to local directory" % (settings.DOWNLOAD_PATH)
            filename = os.path.basename(filename)
        
        # Check if file already exits
        # TODO check if file needs to be resumed
        if os.path.exists(filename):
            current_size = os.path.getsize(filename)   
            # if current_size < int(size):
            #     self.downloads[nick]['received_bytes'] = current_size
            #     percent_finished = 100 * current_size / float(size)
            #     print "File %s was not completed(%0.2f %% done), attempting to resume." % (filename, percent_finished)
            #     resuming = True
            # else:
            print "A file named", filename,
            print "already exists. Refusing to save it."
            del self.downloads[nick]
            self.connection.privmsg(nick, 'XDCC CANCEL')
            self.get_next()
            return
        self.downloads[nick]['dcc'] = self.dcc_connect(peer_address, int(peer_poort), "raw")
        # Save Address -> Nick conversion so we can use it later
        self.dcc_to_bot[self.downloads[nick]['dcc'].peeraddress] = nick
        
        self.downloads[nick]['file'] = open(filename, "w")
        self.downloads[nick]['filesize'] = int(size)
        
       
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

        if self.downloads[nick]['received_bytes'] == self.downloads[nick]['filesize']:
            self.cur.execute('UPDATE episodes SET status=1 WHERE id = ?', (self.downloads[nick]['episode_id'],))

        percent_finished =  100 * float(self.downloads[nick]['received_bytes']) / self.downloads[nick]['filesize']  
        print "Received file from %s (%0.2f percent %s/%s)." % (nick,
         percent_finished, bytes_to_human_string(self.downloads[nick]['received_bytes']), bytes_to_human_string(self.downloads[nick]['filesize']))

        del self.downloads[nick]
        # Anything left to download?
        if len(self.queue) > 0:
            self.get_next()
        elif len(self.downloads) == 0:
            print "Download Queue Empty"
            self.connection.quit()
 
    def on_disconnect(self, connection, event):
        sys.exit(0)

if __name__ == "__main__":
    queue = []
    try:
        conn = sqlite3.connect('mal_db.db')
        cur = conn.cursor()
    except:
        print "Could not connect to sqlite3 database, make sure it exists (run sync_mal)"
        sys.exit(1)
    cur.execute("SELECT * FROM episodes WHERE status != 1")
    for download_needed in cur.fetchall():
        # TODO make sure anime title is valid directory name, possibly cache these to avoid queries
        cur.execute('SELECT title FROM animes WHERE id=?', (download_needed[3],))
        anime_title = cur.fetchone()[0]
        print anime_title
        queue.append({
            'bot': download_needed[4],
            'pack_num':download_needed[5], 
            'id': download_needed[0],
            'series_title': anime_title,
            'episode_number': download_needed[1]})

    if len(queue) < 1:
        print "Your input file needs at least one entry, in format: BOTNAME,PACK_NUM,FILENAME"
        sys.exit(1)

    irc.client.ServerConnection.buffer_class = irc.buffer.LenientDecodingLineBuffer
    c = DCCReceive(queue, cur)
    try:
        c.connect(settings.SERVER, settings.PORT, settings.BOT_NICKNAME)
    except irc.ServerConnectionError, x:
        print x
        sys.exit(1)
    c.start()
    conn.close()
