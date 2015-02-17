import requests
import urllib
import json

def main():

	# read in file
	url = "https://news.kae.re/api/0.1/search/"

	try:
		anime_list = open('watching_list.json', 'r')
		anime_list = json.load(anime_list)
		for anime_id, anime_pack in anime_list.items():
			# print anime_pack['titles']
			# will move stuff up here
			pass

	except:
		print "Error reading watching_list.json"

	#test title
	# command line will have the user choose bot name and resolution pattern
	anime_title = "Death Parade - 01 1080p"
	anime_title = urllib.quote(anime_title)
	url = url + anime_title + ".json"
	packlist = requests.get(url, verify = False)
	msg = []

	if packlist.status_code == 200:

		response = json.loads(packlist.text)
		for response, pack_list in response.iteritems():

			for pack in pack_list['data']['packs']:

				print pack
				if not 'IPV6' in pack['botname'].upper():
					bot_name = pack['botname']
				else:
					continue
				# pack_name = pack['name']
				pack_id = pack['id']
				msg.append("/MSG " + str(bot_name) + " XDCC SEND " + str(pack_id))
				print msg

if __name__ == "__main__":
	main()