from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta

db = SQLAlchemy()
bcrypt = Bcrypt()

TZ_TR = timezone(timedelta(hours=3))  # UTC+3 Türkiye

def now_tr():
    return datetime.now(TZ_TR).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=now_tr)

    snapshots = db.relationship("Snapshot", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Snapshot(db.Model):
    __tablename__ = "snapshots"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_instagram = db.Column(db.String(100), nullable=False)
    scrape_type = db.Column(db.String(20), nullable=False, default="following")
    taken_at = db.Column(db.DateTime, default=now_tr)

    followers = db.relationship("Follower", backref="snapshot", lazy=True, cascade="all, delete-orphan")

    def follower_count(self):
        return len(self.followers)

    def follower_set(self):
        return {f.instagram_username for f in self.followers}

    def type_label(self):
        return "Takip Ettikleri" if self.scrape_type == "following" else "Takipçiler"

    def type_emoji(self):
        return "➡️" if self.scrape_type == "following" else "⬅️"


class Follower(db.Model):
    __tablename__ = "followers"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.Integer, db.ForeignKey("snapshots.id"), nullable=False)
    instagram_username = db.Column(db.String(100), nullable=False)