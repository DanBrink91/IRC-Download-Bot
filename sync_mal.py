import requests
import urllib
import json
import myanimelist.session
import settings
import sqlite3

def main():

	# Populate db with current 'watching' list on MAL
	conn = sqlite3.connect('mal_db.db')
	c = conn.cursor()
	
	# Create table and index it if its not already done
	c.execute('''CREATE TABLE IF NOT EXISTS animes(
		id INTEGER PRIMARY KEY ASC,
		title TEXT,
		alternative_titles TEXT,
		current_ep INTEGER,
		max_ep INTEGER,
		mal_id INTEGER)
	''')
	c.execute('CREATE UNIQUE INDEX IF NOT EXISTS mal_id ON animes (mal_id)')
	
	c.execute('''CREATE TABLE IF NOT EXISTS episodes(
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

	# get watching list and episodes
	session = myanimelist.session.Session(username=settings.username, password=settings.password)
	session.login()
	user_list = myanimelist.anime_list.AnimeList(session, settings.user)
	
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
			#sqlite doesn't have insert on duplicate so whatever
			c.execute('REPLACE INTO animes (title, alternative_titles, current_ep, max_ep, mal_id) VALUES (?, ?, ?, ?, ?)', (title, other_titles_string, episode, max_eps, mal_id))
			conn.commit()

	conn.close()

if __name__ == "__main__":
	main()