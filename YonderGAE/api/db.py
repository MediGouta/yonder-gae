import MySQLdb
from datetime import datetime
from datetime import timedelta
import logging

adminkey = "897d1e5hb8u47u56jh6"

class YonderDb(object):

	def __init__(self):
		self.cur, self.conn = None, None

	def connect(self):
		self.conn = MySQLdb.connect(unix_socket="/cloudsql/subtle-analyzer-90706:yonder", user="root", db="yonderdb", charset="utf8")
		self.cur = self.conn.cursor()
		self.cur.execute("SET NAMES 'utf8mb4'")

	def execute(self, query):
		self.connect()
		logging.debug("Executing %s" % query)
		self.cur.execute(query)
		self.conn.commit()

	def add_video(self, video_id, caption, user_id, channel_id):
		rating = 0
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		caption = caption.replace("'", "\\'")
		query = "insert into videos values ('%s', '%s', '%s', 1, '%s', %d, 0, %s)" % (video_id, user_id, ts, caption, rating, channel_id)
		self.execute(query)
		#self.update_score(video_id, True, "10")

	def add_comment(self, nickname, comment_id, comment, video_id, user_id):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		comment = comment.replace("'", "\\'")
		query = "insert into comments values ('%s', '%s', '%s', '%s', 0, 1, '%s')" % (comment_id, comment, video_id, user_id, ts)
		self.execute(query)
		query = "select caption from videos where video_id = '%s'" % video_id
		self.execute(query)
		row = self.cur.fetchone()
		caption = row[0]
		return caption

	def add_channel(self, channel, user_id):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		channel = MySQLdb.escape_string(channel)
		query = "insert into channels (name, user_id, ts) values ('%s', '%s', '%s')" % (channel, user_id, ts)
		self.execute(query)

	def get_videos(self, user_id, channel):
		query = "select video_id from videos where channel_id = '%s' and visible = 1 order by rating DESC"
		query = query % (channel)
		self.execute(query)
		ids = [row[0] for row in self.cur.fetchall()]
		logging.info("Videos found: " + str(ids))
		return ids

	def get_video_info(self, video_ids, user_id):
		info = []
		query = "select caption, rating, boost from videos where video_id = '%s'"
		comments_total_query = "select count(*) from comments where video_id = '%s' and visible = 1"
		for id in video_ids:
			rated = self.get_rated('video', id, user_id)
			self.execute(query % id)
			row = self.cur.fetchone()
			if row[2] is None:
				boost = 0
			else:
				boost = row[2]
			stats = {"id": id, "caption": row[0], "rating": row[1] + boost, "rated": rated}
			self.execute(comments_total_query % id)
			row = self.cur.fetchone()
			stats["comments_total"] = row[0]
			info.append(stats)
		logging.debug(str(info))
		return info

	def get_comments(self, video_id, user_id):
		comment_list = []
		query = "select comment_id, comment, rating, 'x' from comments where video_id = '%s' and visible = 1 order by ts" % video_id
		self.execute(query)
		for row in self.cur.fetchall():
			rated = self.get_rated('comment', row[0], user_id)
			comment = {"id": row[0].decode(encoding='UTF-8',errors='strict'), "content": row[1], "rating":row[2], "nickname":row[3], "rated":rated}
			comment_list.append(comment)
		return comment_list

	def get_channels(self, user_id, sort):
		channel_list = []
		if sort == "new":
			query = "select channel_id, name, rating from channels where visible = 1 order by ts DESC"
		elif sort == "top":
			query = "select channel_id, name, rating from channels where visible = 1 order by rating DESC"
		else:
			query = "select channel_id, name, rating from channels where visible = 1 order by hot_score DESC"
		self.execute(query)
		for row in self.cur.fetchall():
			rated = self.get_rated('channel', row[0], user_id)
			unseen = self.get_unseen(row[0], user_id)
			channel = {"id": row[0], "name": row[1], "rating": row[2], "rated": rated, "unseen":unseen}
			channel_list.append(channel)
		return channel_list

	def rate_comment(self,comment_id, rating, user_id):
		# if user_id == adminkey:
		# 	if rating == "1":
		# 		rating = 3
		# 	elif rating == "-1":
		# 		rating = -3
		row_count = self.add_vote(user_id, 'comment', comment_id, rating)
		if row_count != 1: # Previously voted on this
			if rating == "1":
				rating = 2
			elif rating == "-1":
				rating = -2
		self.update_score(comment_id, 2, rating)
		query = "update comments set rating=rating+(%s) where comment_id = '%s'" % (rating,comment_id)
		self.execute(query)

	def rate_channel(self,channel_id, rating, user_id):
		# if user_id == adminkey:
		# 	if rating == "1":
		# 		rating = 3
		# 	elif rating == "-1":
		# 		rating = -3
		row_count = self.add_vote(user_id, 'channel', channel_id, rating)
		if row_count != 1: # Previously voted on this
			if rating == "1":
				rating = 2
			elif rating == "-1":
				rating = -2
		self.update_score(channel_id, 0, rating)
		query = "update channels set rating=rating+(%s) where channel_id = '%s'" % (rating,channel_id)
		self.execute(query)

	def rate_video(self,video_id, rating, user_id):
		# if user_id == adminkey:
		# 	if rating == 1:
		# 		rating = 3
		# 	elif rating == -1:
		# 		rating = -3
		row_count = self.add_vote(user_id, 'video', video_id, rating)
		if row_count != 1: # Previously voted on this
			if rating == 1:
				rating = 2
			elif rating == -1:
				rating = -2
		self.update_score(video_id, 1, rating)
		query = "update videos set rating=rating+(%s) where video_id = '%s'" % (rating,video_id)
		self.execute(query)

	def add_vote(self, user_id, item, item_id, rating):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		query = "insert into votes values ('%s','%s', '%s', %s, '%s') ON DUPLICATE KEY UPDATE vote = %s, ts = '%s'" % (user_id, item, item_id, rating, ts, rating, ts)
		self.execute(query)
		return self.cur.rowcount

	def get_rated(self, item, item_id, user_id):
		query = "select vote from votes where item = '%s' and item_id = '%s' and user_id = '%s'" % (item, item_id, user_id)
		self.execute(query)
		vote = self.cur.fetchone()
		if vote is None:
			rated = 0
		else:
			rated = vote[0]
		return rated

	def add_seen(self, user_id, video_ids):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		for id in video_ids:
			query = "insert into seen values ('%s','%s', '%s') ON DUPLICATE KEY UPDATE ts = '%s'" % (user_id, id, ts, ts)
			self.execute(query)

	def update_score(self, id, item, points): # no local commit
		if item == 0:
			user_id_query = "select user_id from channels where channel_id = '%s'" % (id)
		elif item == 1:
			user_id_query = "select user_id from videos where video_id = '%s'" % (id)
		elif item == 2:
			user_id_query = "select user_id from comments where comment_id = '%s'" % (id)

		self.execute(user_id_query)
		row = self.cur.fetchone()
		if row is not None:
			user_id = row[0]
			query = "update users set score=score+(%s) where user_id = '%s'" % (points,user_id)
			self.execute(query)
		else:
			logging.error("Cannot update user score")

	def get_score(self, user_id):
		query = "select score from users where user_id = '%s'" % user_id
		self.execute(query)
		row = self.cur.fetchone()
		score = 0
		if row is not None:
			score = row[0]
		else:
			logging.error("Cannot find user score")
		return score

	def get_unseen(self,channel_id, user_id):
		query = "select count(*) from videos V left join (select * from yonderdb.seen where user_id = '%s' ) AS S on V.video_id = S.video_id " \
				"where S.user_id is NULL and channel_id = '%s' and visible = 1 order by rating DESC" % (user_id, channel_id)
		self.execute(query)
		row = self.cur.fetchone()
		return row[0]

	def get_hot_score(self, date, rating):
		from math import log
		epoch = datetime(1970, 1, 1)
		td = date - epoch
		epoch_seconds = td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000)
		seconds = epoch_seconds - 1134028003
		order = log(max(abs(rating), 1), 10)
		sign = 1 if rating > 0 else -1 if rating < 0 else 0
		return round(sign * order + seconds / 45000, 7)

	def get_user_info(self, user_id, upgrade):
		query = "select warn, ban from users where user_id = '%s'" % user_id
		self.execute(query)
		row = self.cur.fetchone()
		if row is not None:
			info = {"warn": row[0], "ban": row[1], "upgrade": upgrade}
		else:
			logging.error("Cannot find user info")
		return info

	def user_warned(self, user_id):
		query = "update users set warn=0 where user_id = '%s'" % user_id
		self.execute(query)

	def update_last_request(self, user_id, version):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		query = "insert into users values ('%s', NULL, '%s', NULL, NULL, 0, '%s', NULL) on duplicate key update last_request = values(last_request)" % (user_id, ts, ts)
		self.execute(query)
		if self.cur.rowcount == 1:
			from util import User
			email_body = "User %s" % (user_id)
			User.email("New User", email_body)
		query = "update users set version=%s where user_id = '%s'" % (version, user_id)
		self.execute(query)

	def update_last_ping(self, user_id):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		query = "insert into users values ('%s', '%s', NULL, NULL, NULL, 0, '%s', NULL) on duplicate key update last_ping = values(last_ping)" % (user_id, ts, ts)
		self.execute(query)

	### Notifications

	def get_video_votes(self, user_id, ts):
		video_vote_list = []
		query = "SELECT count(*) as count, caption, video_id FROM votes join videos on video_id = item_id " \
				"where item = 'video' and videos.user_id = '%s' and votes.ts > '%s' group by item_id;" % (user_id, ts)
		self.execute(query)
		for row in self.cur.fetchall():
			query = "select channels.name from videos join channels on videos.channel_id = channels.channel_id where video_id = '%s'" % (row[2])
			self.execute(query)
			info = self.cur.fetchone()
			video_vote_list.append({"count": row[0], "caption": row[1], "channel": info[0], "video_id":row[2]})
		return video_vote_list

	def get_comment_votes(self, user_id, ts):
		comment_vote_list = []
		query = "SELECT count(*) as count, comment, video_id FROM votes join comments on comment_id = item_id " \
				"where item = 'comment' and comments.user_id = '%s' and votes.ts > '%s' group by item_id;" % (user_id, ts)
		self.execute(query)
		for row in self.cur.fetchall():
			query = "select caption, channels.name from videos join channels on videos.channel_id = channels.channel_id where video_id = '%s'" % (row[2])
			self.execute(query)
			info = self.cur.fetchone()
			comment_vote_list.append({"count": row[0], "comment": row[1],"caption": info[0], "channel": info[1], "video_id":row[2]})

		return comment_vote_list

	def get_channel_votes(self, user_id, ts):
		channel_vote_list = []
		query = "SELECT count(*) as count, name FROM votes join channels on channel_id = item_id " \
				"where item = 'channel' and channels.user_id = '%s' and votes.ts > '%s' group by item_id;" % (user_id, ts)
		self.execute(query)
		for row in self.cur.fetchall():
			channel_vote_list.append({"count": row[0], "name": row[1]})
		return channel_vote_list

	def get_channel_removed(self, user_id, ts):
		list = []
		query = "SELECT name FROM channels where channels.user_id = '%s' and visible < 1 and removed_ts > '%s'" % (user_id, ts)
		self.execute(query)
		for row in self.cur.fetchall():
			list.append({"name": row[0]})
		return list

	def get_new_videos_owned_channel(self, user_id, ts):
		notification_list = []
		query = "SELECT count(*) as count, C.name FROM videos V join channels C on V.channel_id = C.channel_id " \
				"where C.user_id == '%s' and V.user_id != '%s' and V.ts > '%s' group by C.channel_id" % (user_id, user_id, ts)
		self.execute(query)
		for row in self.cur.fetchall():
			notification_list.append({"count": row[0], "name": row[1]})
		return notification_list

	def get_new_videos_replied_channel(self, user_id, ts):
		notification_list = []
		query = "SELECT count(*) as count, C.name FROM videos V join channels C on V.channel_id = C.channel_id " \
				"where C.user_id == '%s' and V.user_id != '%s' and V.ts > '%s' group by C.channel_id" % (user_id, user_id, ts)
		self.execute(query)
		for row in self.cur.fetchall():
			notification_list.append({"count": row[0], "name": row[1]})
		return notification_list

	### Cron

	def cleanup(self):
		oldest = datetime.utcnow() - timedelta(hours = 24)
		ts = oldest.strftime("%Y-%m-%d %H:%M:%S")

		query = "select video_id from videos V where V.removed_ts < '%s' and visible < 1" % ts
		self.execute(query)
		ids = []
		for row in self.cur.fetchall():
			ids.append(row[0])

		query = "select video_id from videos V join channels C on V.channel_id = C.channel_id where C.removed_ts < '%s' and C.visible < 1" % ts
		self.execute(query)
		for row in self.cur.fetchall():
			ids.append(row[0])
		query = "Delete V FROM channels C join votes V on V.item_id = C.channel_id where C.removed_ts < '%s' and C.visible < 1" % ts
		self.execute(query)
		query = "Delete C from channels C where C.removed_ts < '%s' and C.visible < 1" % ts
		self.execute(query)

		if len(ids) > 0: # if you are deleting videos cause video or channel is invisible
			query = "Delete C FROM videos V join comments C on V.video_id = C.video_id where V.removed_ts < '%s' and V.visible < 1" % ts
			self.execute(query)
			query = "Delete S FROM videos V join seen S on V.video_id = S.video_id where V.removed_ts < '%s' and V.visible < 1" % ts
			self.execute(query)
			query = "Delete T FROM videos V join votes T on V.video_id = T.item_id where V.removed_ts < '%s' and V.visible < 1" % ts
			self.execute(query)
			query = "Delete V from videos V where V.removed_ts < '%s' and V.visible < 1" % ts
			self.execute(query)

		query = "Delete V FROM comments C join votes V on C.comment_id = V.item_id where C.removed_ts < '%s' and C.visible < 1" % ts
		self.execute(query)
		query = "Delete C from comments C where C.removed_ts < '%s' and C.visible < 1" % ts
		self.execute(query)

		return ids

	def cron_set_invisible(self):
		ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		query = "update videos set visible=-1, removed_ts = '%s' where rating < -4" % ts
		self.execute(query)
		query = "update comments set visible=-1, removed_ts = '%s' where rating < -4" % ts
		self.execute(query)
		query = "update channels set visible=-1, removed_ts = '%s' where rating < -4" % ts
		self.execute(query)

	def fake_rating(self):
		query = "select video_id from videos where boost = 0 and user_id = '%s'" % adminkey
		self.execute(query)
		from random import randint
		for row in self.cur.fetchall():
			points = randint(10,30)
			query = "update videos set boost = boost +(%s) where video_id = '%s'" % (points, row[0])
			self.execute(query)
			self.update_score(row[0], True, points)

	def set_hot_score(self):
		query = "select channel_id, rating, ts from channels where visible = 1"
		self.execute(query)
		for row in self.cur.fetchall():
			hot_score = self.get_hot_score(row[2], row[1])
			query = "update channels set hot_score = %s where channel_id = '%s'" % (hot_score, row[0])
			self.execute(query)




















