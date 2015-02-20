import requests
import urllib
import json
import csv
import time
import os
import re

URL = "https://news.kae.re/api/0.1/search/%s.json"
anime_titles = ['Fullmetal Alchemist: Brotherhood', 'Steins;Gate', 'Hunter x Hunter (2011', 'Gintama', 'Clannad: After Story', 'Code Geass: Hangyaku no Lelouch R2', 'Hajime no Ippo', 'Cowboy Bebop', 'Mushishi']
# Do we need to fetch the anime titles?
if os.path.isfile('pack_data.json'):
	with open('pack_data.json', 'r') as f:
		names = json.loads(f.read())
else:
	names = []
	for title in anime_titles:
		response = requests.get(URL % urllib.quote(title), verify=False)
		if response.status_code == 200:
			response_data = response.json()['response']
			if response_data['status']['code'] == 200:
				if 'packs' in response_data['data']:

					names.extend([item['name'] for item in response_data['data']['packs']])
					print 'added: ', title
		# Play nice with their server
		time.sleep(2.0)
	# Dump it so we don't have to get this again
	with open('pack_data.json', 'w') as f:
		f.write(json.dumps(names))

def parse_name(name):
	"""
	Takes in name, outputs subgroup, title, episode, quality
	"""
	groups = re.match(r'\[(.*?)\](.*)-.*?(\d+).*?\[(.*?)\]', name)
	if groups:
		return groups.group(1), groups.group(2), groups.group(3), groups.group(4)
	else:
		# NEIN NEIN NEIN NEIN
		return None, None, None, None
with open('parsed_results.csv', 'wb') as csvfile:
	csvwriter = csv.writer(csvfile)
	csvwriter.writerow(['Subgroup', 'Title', 'Episode #', 'Quality', 'Name Text'])	
	

	for name in names:
		subgroup, title, episode, quality = parse_name(name)
		try:
			csvwriter.writerow([subgroup.encode('utf-8'), title.encode('utf-8'), episode.encode('utf-8'), quality.encode('utf-8'), name.encode('utf-8')])
		except AttributeError:
			csvwriter.writerow([subgroup, title, episode, quality, name])
