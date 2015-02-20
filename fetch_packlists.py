import requests
import urllib
import json
import sqlite3
import re
def parse_name(name):
	"""
	Takes in name, outputs subgroup, title, episode, quality
	"""
	groups = re.match(r'\[(.*?)\](.*)-.*?(\d+).*?\[(.*?)\]', name)
	if groups:
		return groups.group(1), groups.group(2), int(groups.group(3)), groups.group(4)
	else:
		# NEIN NEIN NEIN NEIN
		return None, None, None, None
def main():

	# read in file
	BASE_URL = "https://news.kae.re/api/0.1/search/"
	# grab list of anime to fetch
	conn = sqlite3.connect('mal_db.db')
	c = conn.cursor()
	# Find all animes that don't have every episode downloaded	
	c.execute('select * from animes WHERE (select COUNT(*) from episodes where episodes.series=animes.id AND episodes.status=1) < animes.max_ep')
	anime_list =  c.fetchall()
	msg = []
	episodes_to_add = []
	# TODO resolution and bot names
	for anime in anime_list:
		print "Working on: ", anime[1]
		# Which episodes have we downloaded 
		c.execute('select number from episodes where series=? AND status = 1', (anime[0], ))
		watched = c.fetchall()
		current_episode = max(1, anime[3])
		episodes_needed = [i for i in range(current_episode, anime[4]+1) if i not in watched]
		
		# If we don't need anything skip this anime
		if len(episodes_needed) == 0:
			continue
		# Compile a list of all possible names we can search for
		possible_titles = [anime[1]] + anime[2].split('&&') 
		for anime_title in possible_titles:
			# Search for pack lists
			anime_title = urllib.quote(anime_title)
			anime_title = anime_title.replace("%3A", "")
			url = BASE_URL + anime_title + ".json"
			packlist = requests.get(url, verify = False)

			if packlist.status_code == 200:
				response_data = packlist.json()['response']
				if response_data['status']['code'] == 200:
					if len(response_data['data']) == 0:
						print "Skipping title ", anime_title
						continue
					if response_data['data'] and 'packs' in response_data['data']:
						for pack in response_data['data']['packs']:
							if 'IPV6' in pack['botname'].upper():
								continue
							bot_name = pack['botname']
							pack_name = pack['name']
							pack_id = pack['id']
							subgroup, title, episode_num, quality = parse_name(pack_name)
							# TODO check quality and make sure bot is whitelisted here
							# TODO priortize different bots to allow faster downloading?
							if episode_num in episodes_needed:
								episodes_to_add.append({'pack':pack, 'episode': episode_num, 'anime':anime[0]})
								episodes_needed.pop(episodes_needed.index(episode_num))
						break
		if len(episodes_needed):
			# make sure its all strings
			episodes_needed = map(str, episodes_needed)
			print "Unable to find the rest of the episodes: ", ",".join(episodes_needed)

	for added_episode in episodes_to_add:
		c.execute('INSERT OR IGNORE INTO episodes (number, status, series, botname, packnumber) VALUES (?, 0, ?, ?, ?)',
			(added_episode['episode'], added_episode['anime'], added_episode['pack']['botname'], added_episode['pack']['id']))
	conn.commit()

	conn.close()
if __name__ == "__main__":
	main()