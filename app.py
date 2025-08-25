from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_vod20170321.client import Client as VodClient
from alibabacloud_vod20170321 import models as vod_models
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import os

from models import db, Video, Comment, Admin
from config import config

app = Flask(__name__)
app.config.from_object(config[os.getenv('FLASK_ENV', 'default')])

# 初始化扩展
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = '请先登录'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# 确保上传目录存在
os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads')), exist_ok=True)

def is_allowed_image(filename: str) -> bool:
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in app.config.get('ALLOWED_IMAGE_EXTENSIONS', set())

def normalize_external_video_url(input_url: str) -> str:
    """将外部 http(s)://immedias.lchffr.com/xxx 转换为同域 HTTPS 的 /media/xxx。
    其它域名或已是 /media/ 前缀的不做处理。
    """
    if not input_url:
        return input_url
    if input_url.startswith('/media/'):
        return input_url
    try:
        parsed = urlparse(input_url)
        if parsed.netloc.lower() == 'immedias.lchffr.com':
            # 去掉前导斜杠，拼为相对同域路径
            path = parsed.path.lstrip('/')
            # 保留查询串（如有）
            if parsed.query:
                return f"/media/{path}?{parsed.query}"
            return f"/media/{path}"
    except Exception:
        pass
    return input_url

def vod_client():
    config = open_api_models.Config(
        access_key_id=os.getenv('ALIYUN_ACCESS_KEY_ID', ''),
        access_key_secret=os.getenv('ALIYUN_ACCESS_KEY_SECRET', ''),
        endpoint='vod.cn-shanghai.aliyuncs.com'
    )
    return VodClient(config)

@app.route('/api/vod/playauth/<string:video_id>')
def api_vod_playauth(video_id: str):
    try:
        client = vod_client()
        req = vod_models.GetVideoPlayAuthRequest(video_id=video_id)
        resp = client.get_video_play_auth(req)
        return jsonify({
            'videoId': video_id,
            'playAuth': resp.body.play_auth
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 前端路由
@app.route('/')
def index():
    """首页 - 视频列表"""
    page = request.args.get('page', 1, type=int)
    videos = Video.query.order_by(Video.order_index.asc(), Video.created_at.desc()).paginate(
        page=page, per_page=app.config['VIDEOS_PER_PAGE'], error_out=False
    )
    return render_template('index.html', videos=videos)

@app.route('/video/<int:video_id>')
def video_detail(video_id):
    """视频详情页"""
    video = Video.query.get_or_404(video_id)
    # 增加播放次数
    video.view_count += 1
    db.session.commit()
    
    # 获取已审核的评论
    page = request.args.get('page', 1, type=int)
    comments = Comment.query.filter_by(
        video_id=video_id, 
        is_approved=True
    ).order_by(Comment.created_at.desc()).paginate(
        page=page, per_page=app.config['COMMENTS_PER_PAGE'], error_out=False
    )
    
    return render_template('video_detail.html', video=video, comments=comments)

@app.route('/comment/<int:video_id>', methods=['POST'])
def add_comment(video_id):
    """添加评论"""
    video = Video.query.get_or_404(video_id)
    
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    content = request.form.get('content', '').strip()
    
    if not all([name, phone, content]):
        flash('请填写完整信息', 'error')
        return redirect(url_for('video_detail', video_id=video_id))
    
    # 简单的手机号验证
    if len(phone) != 11 or not phone.isdigit():
        flash('请输入正确的手机号码', 'error')
        return redirect(url_for('video_detail', video_id=video_id))
    
    comment = Comment(
        video_id=video_id,
        name=name,
        phone=phone,
        content=content
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('评论提交成功，待管理员审核后显示', 'success')
    return redirect(url_for('video_detail', video_id=video_id))

# 管理后台路由
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    """管理员登出"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    """管理后台首页"""
    video_count = Video.query.count()
    comment_count = Comment.query.count()
    pending_comment_count = Comment.query.filter_by(is_approved=False).count()
    
    return render_template('admin/dashboard.html', 
                         video_count=video_count,
                         comment_count=comment_count,
                         pending_comment_count=pending_comment_count)

@app.route('/admin/videos')
@login_required
def admin_videos():
    """视频管理"""
    page = request.args.get('page', 1, type=int)
    videos = Video.query.order_by(Video.order_index.asc(), Video.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/videos.html', videos=videos)

@app.route('/admin/video/add', methods=['POST'])
@login_required
def admin_add_video():
    """添加视频"""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    video_url = request.form.get('video_url', '').strip()
    thumbnail_url = request.form.get('thumbnail_url', '').strip()
    thumbnail_file = request.files.get('thumbnail_file')
    # 自动分配序号：取当前最大 order_index + 1
    max_order = db.session.query(db.func.max(Video.order_index)).scalar() or 0
    order_index = request.form.get('order_index', max_order + 1, type=int)
    
    if not title or not video_url:
        flash('标题和视频URL不能为空', 'error')
        return redirect(url_for('admin_videos'))
    
    # 若上传了本地文件，优先保存本地并覆盖 thumbnail_url
    if thumbnail_file and thumbnail_file.filename:
        if not is_allowed_image(thumbnail_file.filename):
            flash('封面格式不被支持', 'error')
            return redirect(url_for('admin_videos'))
        filename = secure_filename(thumbnail_file.filename)
        save_dir = app.config.get('UPLOAD_FOLDER')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        thumbnail_file.save(save_path)
        # 构造可访问URL
        rel_path = os.path.relpath(save_path, app.root_path)
        thumbnail_url = url_for('static', filename=rel_path.replace('static'+os.sep, '').replace('static/', ''), _external=False)

    # 规范化视频地址（将 immedias.lchffr.com 转为 /media/ 前缀，避免混合内容）
    video_url = normalize_external_video_url(video_url)

    vod_video_id = request.form.get('vod_video_id', '').strip()

    video = Video(
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        vod_video_id=vod_video_id,
        order_index=order_index
    )
    db.session.add(video)
    db.session.commit()
    
    flash('视频添加成功', 'success')
    return redirect(url_for('admin_videos'))

@app.route('/admin/video/<int:video_id>/edit', methods=['POST'])
@login_required
def admin_edit_video(video_id):
    """编辑视频"""
    video = Video.query.get_or_404(video_id)
    
    video.title = request.form.get('title', video.title).strip()
    video.description = request.form.get('description', video.description).strip()
    new_video_url = request.form.get('video_url', video.video_url).strip()
    video.video_url = normalize_external_video_url(new_video_url)
    new_thumbnail_url = request.form.get('thumbnail_url', video.thumbnail_url).strip()
    thumbnail_file = request.files.get('thumbnail_file')
    if thumbnail_file and thumbnail_file.filename:
        if not is_allowed_image(thumbnail_file.filename):
            flash('封面格式不被支持', 'error')
            return redirect(url_for('admin_videos'))
        filename = secure_filename(thumbnail_file.filename)
        save_dir = app.config.get('UPLOAD_FOLDER')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        thumbnail_file.save(save_path)
        rel_path = os.path.relpath(save_path, app.root_path)
        new_thumbnail_url = url_for('static', filename=rel_path.replace('static'+os.sep, '').replace('static/', ''), _external=False)
    video.thumbnail_url = new_thumbnail_url
    video.order_index = request.form.get('order_index', video.order_index, type=int)
    video.vod_video_id = request.form.get('vod_video_id', video.vod_video_id).strip()
    
    # 处理播放量修改
    view_count = request.form.get('view_count', type=int)
    if view_count is not None and view_count >= 0:
        video.view_count = view_count
    
    db.session.commit()
    flash('视频更新成功', 'success')
    return redirect(url_for('admin_videos'))

@app.route('/admin/video/<int:video_id>/delete', methods=['POST'])
@login_required
def admin_delete_video(video_id):
    """删除视频"""
    video = Video.query.get_or_404(video_id)
    db.session.delete(video)
    db.session.commit()
    flash('视频删除成功', 'success')
    return redirect(url_for('admin_videos'))

@app.route('/admin/video/<int:video_id>/update-view-count', methods=['POST'])
@login_required
def admin_update_view_count(video_id):
    """快速更新播放量（API）"""
    video = Video.query.get_or_404(video_id)
    
    view_count = request.form.get('view_count', type=int)
    if view_count is not None and view_count >= 0:
        video.view_count = view_count
        db.session.commit()
        return jsonify({'success': True, 'message': '播放量更新成功'})
    
    return jsonify({'success': False, 'message': '无效的播放量'}), 400

@app.route('/admin/comments')
@login_required
def admin_comments():
    """评论管理"""
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'pending')
    
    query = Comment.query
    if filter_type == 'pending':
        query = query.filter_by(is_approved=False)
    elif filter_type == 'approved':
        query = query.filter_by(is_approved=True)
    
    comments = query.order_by(Comment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/comments.html', comments=comments, filter_type=filter_type)

@app.route('/admin/comment/<int:comment_id>/approve', methods=['POST'])
@login_required
def admin_approve_comment(comment_id):
    """审核通过评论"""
    comment = Comment.query.get_or_404(comment_id)
    comment.is_approved = True
    db.session.commit()
    flash('评论审核通过', 'success')
    return redirect(request.referrer or url_for('admin_comments'))

@app.route('/admin/comment/<int:comment_id>/reject', methods=['POST'])
@login_required
def admin_reject_comment(comment_id):
    """拒绝评论"""
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash('评论已拒绝并删除', 'success')
    return redirect(request.referrer or url_for('admin_comments'))

@app.route('/admin/video/<int:video_id>/reorder', methods=['POST'])
@login_required
def admin_reorder_video(video_id):
    """上移/下移视频排序"""
    direction = request.form.get('direction', 'up')
    current = Video.query.get_or_404(video_id)
    if direction == 'up':
        neighbor = Video.query.filter(Video.order_index < current.order_index).order_by(Video.order_index.desc()).first()
    else:
        neighbor = Video.query.filter(Video.order_index > current.order_index).order_by(Video.order_index.asc()).first()
    if neighbor:
        current.order_index, neighbor.order_index = neighbor.order_index, current.order_index
        db.session.commit()
        flash('排序已更新', 'success')
    else:
        flash('已到边界，无法继续移动', 'warning')
    return redirect(url_for('admin_videos'))

@app.route('/admin/videos/normalize', methods=['POST'])
@login_required
def admin_normalize_orders():
    """一键规范化：按当前顺序重排为 1..N"""
    videos = Video.query.order_by(Video.order_index.asc(), Video.created_at.desc()).all()
    for idx, v in enumerate(videos, start=1):
        v.order_index = idx
    db.session.commit()
    flash('已规范化排序', 'success')
    return redirect(url_for('admin_videos'))

@app.cli.command()
def init_db():
    """初始化数据库"""
    db.create_all()
    
    # 创建默认管理员账号
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(
            username='admin',
            email='admin@example.com'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('数据库初始化成功！')
        print('默认管理员账号：admin')
        print('默认管理员密码：admin123')
    else:
        print('数据库已存在')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # 根据环境变量决定是否启用调试模式
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    app.run(debug=debug_mode, host=host, port=port, use_reloader=debug_mode)
