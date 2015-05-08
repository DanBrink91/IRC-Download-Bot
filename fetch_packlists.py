import requests
import urllib
import json
import sqlite3
import re
import settings

class FetchPacklist():

	def __init__(self):
		self.subgroup_pref = None
		self.episodes_to_add = []
		# read in file
		self.BASE_URL = "https://news.kae.re/api/0.1/search/"
		# grab list of anime to fetch
		self.conn = sqlite3.connect('mal_db.db')
		self.c = self.conn.cursor()

	def fetch_all(self):
		# Find all animes that don't have every episode downloaded	
		self.c.execute('select * from animes WHERE (select COUNT(*) from episodes where episodes.series=animes.id AND episodes.status=1) < animes.max_ep')
		self.anime_list =  self.c.fetchall()

		for anime in self.anime_list:
			self.fetch_anime(anime)

	def fetch_anime(self, anime):
		try:
			print "Working on: ", anime[1]
		except UnicodeEncodeError:
			print "Working on (mis-encoded): ", anime[1].encode('ascii', 'ignore') 
		# Which episodes have we downloaded 
		self.c.execute('select number from episodes where series=? AND status = 1', (anime[0], ))
		watched = self.c.fetchall()
		current_episode = max(1, anime[3])
		episodes_needed = [i for i in range(current_episode, anime[4]+1) if i not in watched]
		
		# If we don't need anything skip this anime
		if len(episodes_needed) == 0:
			return
		# Find the preffered fansub for this anime
		self.c.execute('SELECT subgroup FROM episodes WHERE series = ? GROUP BY subgroup ORDER BY COUNT(*) DESC', (anime[0],))
		self.subgroup_pref = self.c.fetchall()
		# Compile a list of all possible names we can search for
		possible_titles = [anime[1]] + anime[2].split('&&') 
		for anime_title in possible_titles:
			# Search for pack lists
			anime_url_title = urllib.quote(anime_title).replace("%3A", "")
			url = self.BASE_URL + anime_url_title + ".json"
			packlist = requests.get(url, verify = False)

			if packlist.status_code == 200:
				response_data = packlist.json()['response']
				if response_data['status']['code'] == 200:
					if len(response_data['data']) == 0:
						print "Skipping title ", anime_title
						return
					if response_data['data'] and 'packs' in response_data['data']:
						#filter packs

						sorted_list = sorted(response_data['data']['packs'], cmp=self.compare_packs)
						for pack in sorted_list:
							if 'IPV6' in pack['botname'].upper():
								return
							bot_name = pack['botname']
							pack_name = pack['name']
							pack_id = pack['id']

							subgroup, title, episode_num, quality = self.parse_name(pack_name)
							# fail to parse :(
							if title == None:
								return
							title = title.replace('_', ' ')
							if title.upper().strip() != anime_title.upper().strip():
								return
							# TODO check quality and make sure bot is whitelisted here
							# TODO priortize different bots to allow faster downloading?
							if episode_num in episodes_needed:
								self.episodes_to_add.append({
									'pack':pack,
									'episode': episode_num,
									'anime':anime[0],
									'subgroup': subgroup,
									'quality': quality,
									'filename': pack_name
									})
								episodes_needed.pop(episodes_needed.index(episode_num))
		if len(episodes_needed):
			# make sure its all strings
			episodes_needed = map(str, episodes_needed)
			print "Unable to find the rest of the episodes: ", ",".join(episodes_needed)

	def update_database(self):
		for added_episode in self.episodes_to_add:
			self.c.execute('INSERT OR IGNORE INTO episodes (number, status, series, botname, packnumber, subgroup, quality, filename) VALUES (?, 0, ?, ?, ?, ? , ?, ?)',
				(added_episode['episode'], added_episode['anime'], added_episode['pack']['botname'], added_episode['pack']['id'], added_episode['subgroup'], added_episode['quality'], added_episode['filename'],))
		
		self.conn.commit()

		self.conn.close()

	def parse_name(self, name):
		"""
		Takes in name, outputs subgroup, title, episode, quality
		"""
		groups = re.match(r'\[(.*?)\](.*)-.*?(\d+).*?\[(.*?)\]', name)
		if groups:
			return str(groups.group(1)), str(groups.group(2)), int(groups.group(3)), str(groups.group(4))
		else:
			# NEIN NEIN NEIN NEIN
			return None, None, None, None

	def compare_packs(self, pack1, pack2):
		"""
			Used to sort packs, favors prefered Quality and Subgroups.
		"""
		pack1_res_index = len(settings.resolution_pref) + 1
		for i, pref in enumerate(settings.resolution_pref):
			if pref in pack1:
				pack1_res_index = i
				break

		pack1_sub_index = len(self.subgroup_pref) + 1
		for i, subgroup in enumerate(self.subgroup_pref):
			if subgroup in pack1:
				pack1_sub_index = i
				break 
		
		pack2_res_index = len(pref) + 1
		for i, pref in enumerate(settings.resolution_pref):
			if pref in pack2:
				pack2_res_index = i
				break

		pack2_sub_index = len(self.subgroup_pref) + 1
		for i, subgroup in enumerate(self.subgroup_pref):
			if subgroup in pack2:
				pack2_sub_index = i
				break 
		
		return pack1_res_index + pack1_sub_index - pack2_res_index + pack2_sub_index	
if __name__ == "__main__":
	fetch = FetchPacklist()
	fetch.fetch_all()
	fetch.update_database()