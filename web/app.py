import sqlite3
from flask import Flask, g, render_template, send_from_directory, request
import os

DATABASE = "../mal_db.db"
app = Flask(__name__, static_url_path='/home/dan/Videos')

def make_dicts(cursor, row):
	"""
	Lets us get a dictionary from sqlite instead of a tuple
	"""
	return dict((cursor.description[idx][0], value)
	                for idx, value in enumerate(row))
def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DATABASE)
		db.row_factory = make_dicts
	return db

@app.teardown_appcontext
def close_connection(exception):
	db = getattr(g, '_database', None)
	if db is not None:
		db.close()

def query_db(query, args=(), one=False):
	"""
	helper function for db queries
	"""
	cur = get_db().execute(query, args)
	rv = cur.fetchall()
	cur.close()
	return (rv[0] if rv else None) if one else rv
# =====================================================
# Views
# =====================================================

@app.route('/')
def index():
	ongoing_anime = query_db("""SELECT  animes.id, animes.title,  MIN(episodes.number) AS current_episode, episodes.id AS episode_id FROM animes
JOIN episodes ON episodes.series = animes.id
WHERE animes.max_ep > (SELECT IFNULL(MAX(episodes.number), animes.current_ep)  FROM episodes 
WHERE  episodes.series=animes.id AND episodes.status = 1)
AND episodes.status = 0
GROUP BY animes.id""")
	
	completed_anime = query_db("""SELECT  animes.id, animes.title,  MIN(episodes.number) AS current_episode, episodes.id AS episode_id FROM animes
JOIN episodes ON episodes.series = animes.id
WHERE animes.max_ep = (SELECT IFNULL(MAX(episodes.number), animes.current_ep)  FROM episodes 
WHERE  episodes.series=animes.id AND episodes.status = 1)
AND episodes.status = 0
GROUP BY animes.id""")
	
	return render_template('index.html', ongoing=ongoing_anime, completed=completed_anime)

@app.route('/anime/<int:anime_id>', methods=['GET', 'POST'])
def anime(anime_id):
	anime_info = query_db("SELECT * FROM animes WHERE id=?", (anime_id, ), True)
	titles = [anime_info['title']] + anime_info['alternative_titles'].split('&&')
	if request.method == 'POST':
		title = request.form['title']
		if title in titles:
			return "Title already existed"
		new_titles = '&&'.join(anime_info['alternative_titles'].split('&&') + [title])

		db = get_db()
		cur = db.execute('UPDATE animes SET alternative_titles=? WHERE id=?', (new_titles, anime_id, ))
		db.commit()
		cur.close()
		return "updated"

	else:
		episodes = query_db("SELECT * FROM episodes WHERE series=?", (anime_id, ))  
		return render_template('anime.html', info=anime_info, episodes=episodes, titles=titles)

@app.route('/episode/<int:episode_id>')
def episode(episode_id):
	episode_info = query_db("SELECT * FROM episodes WHERE id=?", (episode_id, ), True)
	anime_info = query_db("SELECT * FROM animes WHERE id=?", (episode_info['series'], ), True)
	episode_path = os.path.join(anime_info['title'], episode_info['filename']) 
	return render_template('episode.html', episode=episode_info, anime=anime_info, episode_path=episode_path)

@app.route('/video/<path:filename>')
def video(filename):
	return send_from_directory('/home/dan/Videos/', filename)
if __name__ == '__main__':
	app.debug = True
	app.run()