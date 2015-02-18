import requests
import urllib
import json
import jsonpickle
import myanimelist.session
import mal_settings
import sqlite3

class Entry:
	def __init__(self, titles, episode):
		self.titles = titles
		self.episode = episode

def main():

	try:
		# Populate db with current 'watching' list on MAL

		#check if it exists
		conn = sqlite3.connect('mal_db.db')
		c = conn.cursor()
		c.execute('CREATE TABLE watching_list(anime_title, alternative_titles, current_ep, max_ep)')
		#may or may not be the right thing to do idk
		c.execute('CREATE UNIQUE INDEX anime_title ON watching_list (anime_title)')
		conn.close()
	except:
		print "DB already exists or error establishing DB"
	# get watching list and episodes
	session = myanimelist.session.Session(username=mal_settings.username, password=mal_settings.password)
	session.login()
	user_list = myanimelist.anime_list.AnimeList(session, mal_settings.user)

	for key, value in user_list.list.items():

		if value['status'] == "Watching":

			title = key.title
			print key.title
			other_titles = []
			episode = value['episodes_watched']
			max_eps = key.episodes

			# Get the alternative titles and add them
			for alt_title, val in key.alternative_titles.iteritems():

				if alt_title == "English" or alt_title == "Synonyms":

					# Sometimes it is a list of alternative titles..
					if type(val) is list:
						for a_title in val:
							other_titles.append(a_title)
					else:
						other_titles.append(val)

			# comma separated for now
			other_titles = ', '.join(other_titles)
			print other_titles
			conn = sqlite3.connect('mal_db.db')
			c = conn.cursor()
			#sqlite doesn't have insert on duplicate so whatever
			c.execute('REPLACE INTO watching_list (anime_title, alternative_titles, current_ep, max_ep) VALUES (?, ?, ?, ?)', (title, other_titles, episode, max_eps))

			# UPDATE watching_list SET episode = episode, max_eps = max_eps WHERE title = title
			# ON DUPLICATE KEY UPDATE 
			# 	episode=VALUES(episode),
			# 	max_eps=VALUES(max_eps) ;
			conn.commit()

	conn.close()

if __name__ == "__main__":
	main()