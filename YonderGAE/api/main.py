import logging
import webapp2
import json
from videos import Upload
from videos import Feed
from channels import Channels
from notifications import Notifications
from comments import Comment
from videos import Video
from util import User
from cron import Cron

class Videos(webapp2.RequestHandler):

	def post(self):
		self.response.headers["Content-Type"] = "application/json"
		try:
			video = self.request.POST.multi["uploadedfile"]
			caption = self.request.get("caption")
			user_id = self.request.get("user")
			longitude = self.request.get("long")
			latitude = self.request.get("lat")
			upload = Upload()
			upload.add_video(video, caption, user_id, longitude, latitude)
		except Exception:
			logging.exception("Failed uploading the video")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Video uploaded successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

	def get(self):
		self.response.headers["Content-Type"] = "application/json"
		try:
			longitude = self.request.GET["long"]
			latitude = self.request.GET["lat"]
			user_id = self.request.GET["user"]
			search_type = self.request.GET["search"]
			feed = Feed()
			if search_type == "near":
				video_ids = feed.get_videos(user_id, longitude, latitude)
			elif search_type == "mine":
				video_ids = feed.get_my_videos(user_id, True, True)
			elif search_type == "count":
				video_ids = feed.get_videos(user_id, longitude, latitude, True)
				video_ids = len(video_ids)
		except Exception:
			logging.exception("Failed looking for videos")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Video Ids retrieved successfully")
			out = {"success": 1, "videos": video_ids}
			self.response.write(json.dumps(out))

class VideosInfo(webapp2.RequestHandler):

	def get(self):
		self.response.headers["Content-Type"] = "application/json"
		try:
			ids = self.request.GET["ids"] # could reach a limit?
			video_ids = ids.split("xxx")
			feed = Feed()
			videos_info = feed.get_videos_info(video_ids)
		except Exception:
			logging.exception("Failed looking for videos")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Video Ids retrieved successfully")
			out = {"success": 1, "videos": videos_info}
			self.response.write(json.dumps(out))

class Comments(webapp2.RequestHandler):

	def post(self, video_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user_id = self.request.POST["user"]
			nickname = self.request.POST["nickname"]
			text = self.request.POST["comment"]
			comment_id = self.request.POST["id"]
			comment = Comment()
			comment.add_comment(nickname, comment_id, text, video_id, user_id)
		except Exception:
			logging.exception("Failed to add a comment")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Comment added successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

	def get(self, video_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			comment = Comment()
			comment_list = comment.get_comments(video_id)
		except Exception:
			logging.exception("Failed getting comments")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Comments retrieved successfully")
			out = {"success": 1, "comments": comment_list}
			self.response.write(json.dumps(out))

class ReportVideo(webapp2.RequestHandler):

	def post(self, video_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user_id = self.request.POST["user"]
			report = Video()
			report.add_flag(video_id, user_id)
		except Exception:
			logging.exception("Failed to report video %s" % video_id)
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Video reported successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

class ReportComment(webapp2.RequestHandler):

	def post(self, comment_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user_id = self.request.POST["user"]
			comment = Comment()
			comment.add_flag(comment_id, user_id)
		except Exception:
			logging.exception("Failed to report comment %s" % comment_id)
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Comment reported successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

class RateComment(webapp2.RequestHandler):

	def post(self, comment_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			rating = self.request.POST["rating"]
			user_id = self.request.POST["user"]
			comment = Comment()
			comment.rate_comment(comment_id, rating, user_id)
		except Exception:
			logging.exception("Failed to rate comment %s" % comment_id)
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Comment rated successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

class VideoRating(webapp2.RequestHandler):

	def post(self, video_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			rating = self.request.POST["rating"]
			user_id = self.request.POST["user"]
			video = Video()
			video.add_rating(video_id, rating, user_id)
		except Exception:
			logging.exception("Failed to add video rating")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Video rating added successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

class Verify(webapp2.RequestHandler):

	def get(self, user_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user = User()
			version = self.request.get("version")
			user_info = user.verify(user_id, version)
		except Exception:
			logging.exception("Failed verifying user %s" % user_id)
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("User info retrieved successfully")
			out = {"success": 1, "user": user_info}
			self.response.write(json.dumps(out))

class Ping(webapp2.RequestHandler):

	def get(self, user_id):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user = User()
			version = self.request.get("version")
			user.ping(user_id)
		except Exception:
			logging.exception("Failed ping user %s" % user_id)
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("User pinged successfully")
			out = {"success": 1}
			self.response.write(json.dumps(out))

class MyVideosInfo(webapp2.RequestHandler):

	def get(self):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user_id = self.request.GET["user"]
			feed = Feed()
			ids = feed.get_my_videos(user_id, True, False)
			videos_info = feed.get_videos_info(ids)
			user = User()
			score = user.get_score(user_id)
		except Exception:
			logging.exception("Failed looking for videos")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Video Ids retrieved successfully")
			out = {"success": 1, "videos": videos_info, "score": score}
			self.response.write(json.dumps(out))

class Channel(webapp2.RequestHandler):

	def get(self):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user_id = self.request.GET["user"]
			sort = self.request.GET["sort"]
			channels = Channels()
			channels_list = channels.get_channels(user_id, sort)
		except Exception:
			logging.exception("Failed looking for channels")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Channels retrieved successfully")
			out = {"success": 1, "channels": channels_list}
			self.response.write(json.dumps(out))


class Notification(webapp2.RequestHandler):

	def get(self):
		self.response.headers["Content-Type"] = "application/json"
		try:
			user_id = self.request.GET["user"]
			seen = self.request.GET["seen"]
			notifications = Notifications()
			notifications_list = notifications.get_notifications(user_id, seen)
		except Exception:
			logging.exception("Failed looking for notifications")
			out = {"success": 0}
			self.response.write(json.dumps(out))
		else:
			logging.info("Notifications retrieved successfully")
			out = {"success": 1, "notifications": notifications_list}
			self.response.write(json.dumps(out))

class CronJob(webapp2.RequestHandler):

	def get(self):
		cron = Cron()
		cron.cleanup()

# Every request associated to user id
app = webapp2.WSGIApplication([(r"/cron", CronJob),
							   (r"/videos", Videos),
							   (r"/channels", Channel),
							   (r"/notifications", Notification),
                               (r"/videos/info", VideosInfo),
                               (r"/myvideos/info", MyVideosInfo),
                               (r"/videos/(\d+)/comments", Comments),
                               (r"/videos/(\d+)/flag", ReportVideo),
                               (r"/comments/(\d+)/flag", ReportComment),
							   (r"/comments/(\d+)/rating", RateComment),
                               (r"/videos/(\d+)/rating", VideoRating),
                               (r"/users/(\w+)/ping", Ping),
                               (r"/users/(\w+)/verify", Verify)], debug=True)