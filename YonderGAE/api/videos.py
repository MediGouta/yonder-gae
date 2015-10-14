import cloudstorage as gcs
import logging
import math
from db import YonderDb
from random import randint

my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)
gcs.set_default_retry_params(my_default_retry_params)

class Upload(object):

	def add_video(self, video, caption, user_id, longitude, latitude):
		file_name = "/yander/" + video.filename
		logging.info("Adding new video %s" % video.filename[:-4])
		logging.debug("Caption '%s' User %s Longitude %s Latitude %s" % (caption, user_id, longitude, latitude))
		write_retry_params = gcs.RetryParams(backoff_factor=1.1)
		gcs_file = gcs.open(file_name,
		                    "w",
		                    content_type="video/mp4",
		                    options={"x-goog-acl": "public-read"},
		                    retry_params=write_retry_params)
		file_content = video.file.read()
		gcs_file.write(file_content)
		gcs_file.close()
		yonderdb = YonderDb()
		yonderdb.add_video(video.filename[:-4], caption, user_id, longitude, latitude)
		from util import User
		if user_id != "897d1e5hb8u47u56jh6":
			email_body = "Caption '%s' User %s" % (caption, user_id)
			User.email("New Video", email_body)


class Feed(object):

	def get_videos(self, user_id, longitude, latitude, count = False):
		radius = float(5000)
		longitude = float(longitude)
		latitude = float(latitude)
		rlon1 = longitude - (radius / abs(math.cos(math.radians(latitude)) * 69))
		rlon2 = longitude + (radius / abs(math.cos(math.radians(latitude)) * 69))
		rlat1 = latitude - (radius / 69)
		rlat2 = latitude + (radius / 69)
		limit = randint(3,5)
		video_ids = []

		yonderdb = YonderDb()
		seen_count = yonderdb.recently_seen(user_id, 3)
		logging.info("Seen count past 3 hours %s" % seen_count)
		if seen_count >= 8:
			return video_ids
		seen_count = yonderdb.recently_seen(user_id, 24)
		logging.info("Seen count past 24 hours %s" % seen_count)
		if seen_count == 0:
			limit = randint(5,7)
		seen_count = yonderdb.recently_seen(user_id, 70)
		logging.info("Seen count past 70 hours %s" % seen_count)
		if seen_count == 0:
			limit = randint(7,9)

		video_ids = yonderdb.get_videos(user_id, longitude, latitude, rlon1, rlon2, rlat1, rlat2, limit)
		if len(video_ids) == 0 and not count:
			from util import User
			email_body = "User %s" % (user_id)
			User.email("No content", email_body)
		if not count:
			yonderdb.add_seen(user_id, video_ids)
		return video_ids

	def get_my_videos(self, user_id, uploaded, commented):
		yonderdb = YonderDb()
		video_ids = yonderdb.get_my_videos(user_id, uploaded, commented)
		return video_ids

	def get_videos_info(self, video_ids):
		yonderdb = YonderDb()
		videos_info = []
		if len(video_ids) > 0:
			videos_info = yonderdb.get_video_info(video_ids)
		return videos_info


class Video(object):
	def add_flag(self, video_id, user_id):
		yonderdb = YonderDb()
		yonderdb.flag_video(video_id, user_id)

	def add_rating(self, video_id, rating, user_id):
		yonderdb = YonderDb()
		yonderdb.rate_video(video_id, int(rating), user_id)
