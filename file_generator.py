import requests
import myanimelist.session
import mal_settings
import json
#PECKLE
import jsonpickle

# Populate file with current 'watching' list on MAL

class Entry:
	def __init__(self, titles, episode):
		self.titles = titles
		self.episode = episode

def main():
	
	# get watching list and episodes
	session = myanimelist.session.Session(username=mal_settings.username, password=mal_settings.password)
	session.login()
	user_list = myanimelist.anime_list.AnimeList(session, mal_settings.user)

	watching = {}
	for key, value in user_list.list.items():

		if value['status'] == "Watching":

			titles = []
			titles.append(key.title)
			# Get the alternative titles and add them
			for alt_title, val in key.alternative_titles.iteritems():

				if alt_title == "English" or alt_title == "Synonyms":

					# Sometimes it is a list of alternative titles..
					if type(val) is list:
						for title in val:
							titles.append(title)
					else:
						titles.append(val)
						
			watching[key] = Entry(titles, value['episodes_watched'])


	# populate file
	# 'w' will truncate existing file
	# 'a' will not

	filename = "watching_list.json"

	try:
		file_content = open(filename, 'w')
		json_list = jsonpickle.encode(watching)
		file_content.write(json_list)
		file_content.close()
	except:
		"Error writing json file"


if __name__ == "__main__":
	main()