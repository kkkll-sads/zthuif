# 视频播放应用

一个基于Python Flask的视频播放应用，支持阿里云OSS视频播放、用户评论和后台管理功能。

## 功能特点

### 前端功能
- 📺 视频列表展示（首页）
- 🎬 视频播放详情页
- 💬 用户评论功能（需填写姓名和手机号）
- 📱 响应式设计，支持移动端访问

### 后台管理功能
- 👤 管理员登录系统
- 📊 仪表盘统计概览
- 🎥 视频管理（添加、编辑、删除、排序）
- 💭 评论审核（评论需审核后才能显示）
- 👁️ 播放次数统计

## 技术栈

- **后端**: Flask 3.0
- **数据库**: SQLite (开发环境) / 可配置其他数据库
- **前端**: HTML5 + CSS3 + JavaScript
- **视频存储**: 阿里云OSS
- **开发工具**: 
  - 热重载支持（watchdog）
  - 环境变量管理（python-dotenv）

## 安装部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd pypo
```

### 2. 创建虚拟环境
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
创建 `.env` 文件并配置以下内容：
```env
# Flask配置
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# 阿里云OSS配置（如果需要上传功能）
ALIYUN_ACCESS_KEY_ID=your-access-key-id
ALIYUN_ACCESS_KEY_SECRET=your-access-key-secret
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET=your-bucket-name
```

### 5. 初始化数据库
```bash
flask init-db
```
这将创建数据库并生成默认管理员账号：
- 用户名：admin
- 密码：admin123

**⚠️ 重要：请在生产环境中立即修改默认密码！**

### 6. 运行应用

#### 开发模式（带热重载）
```bash
# Windows
run_dev.bat

# 或直接运行Python脚本
python run_dev.py
```
- 启用热重载，代码修改后自动重启
- 调试模式开启，显示详细错误信息
- 访问地址：http://localhost:5000

#### 生产模式
```bash
python run_prod.py

# 或使用环境变量
python app.py
```
- 禁用调试模式和热重载
- 监听所有网络接口（0.0.0.0）
- 适合部署使用

## 使用说明

### 添加视频
1. 登录管理后台：http://localhost:5000/admin/login
2. 进入"视频管理"页面
3. 点击"添加新视频"
4. 填写视频信息：
   - **视频标题**：视频的显示名称
   - **视频URL**：阿里云OSS上的视频直链地址
   - **缩略图URL**：视频封面图片地址（可选）
   - **视频描述**：视频简介（可选）
   - **排序索引**：数字越小排序越靠前

### 阿里云OSS视频URL格式
视频URL应该是可以直接访问的OSS地址，例如：
```
https://your-bucket.oss-cn-hangzhou.aliyuncs.com/videos/example.mp4
```

确保视频文件的访问权限设置为公共读取。

### 评论管理
1. 用户在视频详情页提交的评论默认不显示
2. 管理员需要在后台"评论管理"中审核
3. 审核通过的评论才会在前端显示
4. 可以查看评论者的姓名和手机号（手机号已部分隐藏）

## 项目结构
```
pypo/
├── app.py              # Flask主应用
├── models.py           # 数据模型
├── config.py           # 配置文件
├── requirements.txt    # 项目依赖
├── README.md          # 项目说明
├── templates/         # HTML模板
│   ├── base.html     # 基础模板
│   ├── index.html    # 首页
│   ├── video_detail.html  # 视频详情页
│   └── admin/        # 管理后台模板
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── videos.html
│       └── comments.html
└── static/           # 静态文件
    └── css/
        └── style.css # 样式文件
```

## 生产环境部署建议

1. **使用生产级数据库**：将SQLite替换为MySQL或PostgreSQL
2. **配置环境变量**：使用环境变量管理敏感信息
3. **使用WSGI服务器**：如Gunicorn或uWSGI
4. **配置反向代理**：使用Nginx作为反向代理
5. **启用HTTPS**：确保数据传输安全
6. **定期备份**：备份数据库和上传的文件

## 开发指南

### 热重载功能
本项目支持热重载，在开发模式下修改代码后会自动重启服务器：

1. **启动开发服务器**
   ```bash
   # Windows用户
   run_dev.bat
   
   # 或使用Python脚本
   python run_dev.py
   ```

2. **热重载工作原理**
   - 监控所有Python文件的修改
   - 文件保存后自动重启Flask服务器
   - 无需手动重启即可看到代码更改效果

3. **注意事项**
   - 仅在开发环境使用热重载
   - 生产环境请使用 `run_prod.py`
   - 如遇到端口占用，请先停止之前的服务器

## 开发计划

- [ ] 视频分类功能
- [ ] 用户注册和登录系统
- [ ] 视频搜索功能
- [ ] 视频上传到OSS功能
- [ ] 评论点赞功能
- [ ] 视频收藏功能

## 许可证

MIT License
