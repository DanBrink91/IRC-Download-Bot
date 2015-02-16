import requests
import myanimelist.session
import settings

# Populate file with current 'watching' list on MAL

def main():
	
	# get watching list and episodes
	session = myanimelist.session.Session(username=settings.username, password=settings.password)
	session.login()
	test = myanimelist.anime_list.AnimeList(session, settings.user)
	print test.list
	watching = {}
	for key, value in test.list.items():
		if value['status'] == "Watching":
			watching[key.title] = value['episodes_watched']
	print watching

	# populate file
	# 'w' will truncate existing file
	# 'a' will not
	filename = "watching_list.txt"
	line = ""
	try: 
		file_content = open(filename, 'w')
		for anime, episode in watching.items():
			# encode because of titles like Tokyo Ghoul square root A
			line = str(anime.encode('utf8')) + " - " + str(episode) + '\n' 
			file_content.write(line)
		print file_content
		file_content.close()
	except:
		print "Error writing to txt file"


if __name__ == "__main__":
	main()