from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Video(db.Model):
    """视频模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(500), nullable=False)  # 阿里云OSS视频URL
    thumbnail_url = db.Column(db.String(500))  # 缩略图URL
    vod_video_id = db.Column(db.String(128))  # 阿里云VOD视频ID（有则优先使用）
    view_count = db.Column(db.Integer, default=0)  # 播放次数
    order_index = db.Column(db.Integer, default=0)  # 排序索引
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    comments = db.relationship('Comment', backref='video', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Video {self.title}>'

class Comment(db.Model):
    """评论模型"""
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 用户姓名
    phone = db.Column(db.String(20), nullable=False)  # 手机号码
    content = db.Column(db.Text, nullable=False)  # 评论内容
    is_approved = db.Column(db.Boolean, default=False)  # 是否审核通过
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Comment by {self.name}>'

class Admin(db.Model, UserMixin):
    """管理员模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'
