from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
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
    order_index = request.form.get('order_index', 0, type=int)
    
    if not title or not video_url:
        flash('标题和视频URL不能为空', 'error')
        return redirect(url_for('admin_videos'))
    
    video = Video(
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
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
    video.video_url = request.form.get('video_url', video.video_url).strip()
    video.thumbnail_url = request.form.get('thumbnail_url', video.thumbnail_url).strip()
    video.order_index = request.form.get('order_index', video.order_index, type=int)
    
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
