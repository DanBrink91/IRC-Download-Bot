from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
from models import Anime, Episode, Base
from flask import Flask, g, render_template, send_from_directory, request
import os


engine = create_engine("sqlite:///../mal_db.db")
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__, static_url_path='/home/dan/Videos')
# =====================================================
# Views
# =====================================================

# TODO less bad
@app.route('/')
def index():
	ongoing_anime = session.query(Anime, func.min(Episode.number).label('current_episode')).join(Episode).group_by(Episode.series).filter(Episode.status == 0).all()
	completed_anime = []

	return render_template('index.html', ongoing=ongoing_anime, completed=completed_anime)

@app.route('/anime/<int:anime_id>', methods=['GET', 'POST'])
def anime(anime_id):
	anime_info = session.query(Anime).filter(Anime.id==anime_id).one()
	titles = [anime_info.title] + anime_info.alternative_titles.split('&&')
	if request.method == 'POST':
		title = request.form['title']
		if title in titles:
			return "Title already existed"
		new_titles = '&&'.join(anime_info.alternative_titles.split('&&') + [title])

		session.execute(update(Anime).where(Anime.id==anime_id).values(alternative_titles=new_titles))
		session.commit()
		return "updated"

	else:
		episodes = session.query(Episode).filter(Episode.series==anime_id).all()
		return render_template('anime.html', info=anime_info, episodes=episodes, titles=titles)

@app.route('/episode/<int:episode_id>')
def episode(episode_id):
	episode_info = session.query(Episode).filter(Episode.id == episode_id).one()
	anime_info = session.query(Anime).filter(Anime.id == episode_info.series).one()
	all_episodes = session.query(Episode).filter(Episode.series == episode_info.series).all()
	episode_path = os.path.join(anime_info.title, episode_info.filename) 
	return render_template('episode.html', episode=episode_info, anime=anime_info, episode_path=episode_path, all_episodes=all_episodes)

@app.route('/episode/<int:episode_id>/completed', methods=['POST'])
def episode_complete(episode_id):
	session.execute(update(Episode).where(Episode.id==episode_id).values(status=2))
	session.commit()

	episode_info = session.query(Episode).filter(Episode.id == episode_id).one()
	anime_info = session.query(Anime).filter(Anime.id == episode_info.series).one()
	next_episode = session.query(Episode).filter(Episode.series == episode_info.series, Episode.number == episode_info.number + 1).one()

	episode_path = os.path.join(anime_info.title, next_episode.filename) 
	return episode_path 

@app.route('/video/<path:filename>')
def video(filename):
	return send_from_directory('/home/dan/Videos/', filename)

if __name__ == '__main__':
	app.debug = True
	app.run()