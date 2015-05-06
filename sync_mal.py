import requests
import urllib
import json
import myanimelist.session
import settings
import sqlite3

class MALSync():

	def __init__(self, db='mal_db.db'):
		self.conn = sqlite3.connect('mal_db.db')
		self.c = self.conn.cursor()
		
		self.session = myanimelist.session.Session(username=settings.username, password=settings.password)
		self.session.suppress_parse_exceptions = True
		self.session.login()

	def create_tables(self):
		# Create table and index it if its not already done
		self.c.execute('''CREATE TABLE IF NOT EXISTS animes(
			id INTEGER PRIMARY KEY ASC,
			title TEXT,
			alternative_titles TEXT,
			current_ep INTEGER,
			max_ep INTEGER,
			mal_id INTEGER)
		''')
		self.c.execute('CREATE UNIQUE INDEX IF NOT EXISTS mal_id ON animes (mal_id)')
		
		self.c.execute('''CREATE TABLE IF NOT EXISTS episodes(
			id INTEGER PRIMARY KEY ASC,
			number INTEGER,
			status INTEGER,
			series INTEGER,
			botname TEXT,
			packnumber INTEGER,
			subgroup TEXT,
			quality TEXT,
			filename TEXT,
			FOREIGN KEY(series) REFERENCES animes(id),
			UNIQUE(number, series) ON CONFLICT REPLACE
		)''')
	
	def fetch_data(self):
		user_list = myanimelist.anime_list.AnimeList(self.session, settings.user)
		
		for anime_object, watch_info in user_list.list.items():
			if watch_info['status'] == "Watching":
				mal_id = anime_object.id
				title = anime_object.title.encode('ascii', 'ignore')
				other_titles = []
				episode = watch_info['episodes_watched']
				max_eps = anime_object.episodes

				# Get the alternative titles and add them
				for alt_title, val in anime_object.alternative_titles.iteritems():

					if alt_title == "English" or alt_title == "Synonyms":

						# Sometimes it is a list of alternative titles..
						if type(val) is list:
							for a_title in val:
								other_titles.append(a_title.encode('ascii', 'ignore'))
						else:
							other_titles.append(val.encode('ascii', 'ignore'))
				# using && as a separater for now
				other_titles_string = '&&'.join(other_titles)
				# sqlite doesn't have insert on duplicate so whatever
				self.c.execute('INSERT OR  REPLACE INTO animes (id, title, alternative_titles, current_ep, max_ep, mal_id) VALUES ((SELECT id FROM animes WHERE mal_id=?), ?, COALESCE((SELECT alternative_titles FROM animes WHERE mal_id=?), ?), COALESCE((SELECT current_ep FROM animes WHERE mal_id=?), ?), ?, ?)', (mal_id, title, mal_id, other_titles_string, mal_id, episode, max_eps, mal_id))
				self.conn.commit()
		self.conn.close()

if __name__ == "__main__":
	mal_sync = MALSync()
	mal_sync.create_tables()
	mal_sync.fetch_data()