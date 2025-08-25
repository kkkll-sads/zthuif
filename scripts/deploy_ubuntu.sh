#!/usr/bin/env bash
set -euo pipefail

# =============================
# Pypo 双实例一键部署脚本 (Ubuntu)
# 实例1: jt.zztzbhf.cc  → 127.0.0.1:8001
# 实例2: zjs.zztzbhf.cc → 127.0.0.1:8002
# 使用: sudo bash scripts/deploy_ubuntu.sh
# =============================

# 配置区(可按需修改)
DOMAIN_1="jt.zztzbhf.cc"
DOMAIN_2="zjs.zztzbhf.cc"
PORT_1=8001
PORT_2=8002
PYTHON_BIN="python3"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # 仓库根目录
VENV_DIR="${PROJECT_DIR}/venv"
SERVICE_1="pypo-jt"
SERVICE_2="pypo-zjs"
USER_NAME="${SUDO_USER:-$(whoami)}"
GROUP_NAME="${SUDO_USER:-$(whoami)}"
DB_DIR="${PROJECT_DIR}/instance"
DB_1_PATH="${DB_DIR}/video_app_jt.db"
DB_2_PATH="${DB_DIR}/video_app_zjs.db"
SECRET_1="$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32 || true)"
SECRET_2="$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32 || true)"

# 颜色输出
info(){ echo -e "\033[1;34m[INFO]\033[0m $*"; }
ok(){ echo -e "\033[1;32m[OK]\033[0m $*"; }
warn(){ echo -e "\033[1;33m[WARN]\033[0m $*"; }
err(){ echo -e "\033[1;31m[ERR]\033[0m $*"; }

require_root(){
  if [ "$(id -u)" -ne 0 ]; then
    err "请使用 root 权限执行: sudo bash scripts/deploy_ubuntu.sh"
    exit 1
  fi
}

install_packages(){
  info "更新系统并安装依赖..."
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ${PYTHON_BIN} ${PYTHON_BIN}-venv ${PYTHON_BIN}-pip \
    nginx curl
}

setup_venv(){
  info "创建并安装 Python 虚拟环境依赖..."
  if [ ! -d "${VENV_DIR}" ]; then
    ${PYTHON_BIN} -m venv "${VENV_DIR}"
  fi
  source "${VENV_DIR}/bin/activate"
  pip install --upgrade pip
  # 优先使用项目 requirements，如无 gunicorn 则单独安装
  if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
    pip install -r "${PROJECT_DIR}/requirements.txt"
  fi
  pip install gunicorn
  ok "虚拟环境准备完成"
}

prepare_dirs(){
  info "准备实例数据库目录与日志目录..."
  mkdir -p "${DB_DIR}" "/var/log/${SERVICE_1}" "/var/log/${SERVICE_2}"
  chown -R "${USER_NAME}:${GROUP_NAME}" "${PROJECT_DIR}" "/var/log/${SERVICE_1}" "/var/log/${SERVICE_2}"
  ok "目录已就绪"
}

create_init_script(){
  info "创建数据库初始化脚本..."
  mkdir -p "${PROJECT_DIR}/scripts"
  cat >"${PROJECT_DIR}/scripts/init_db.py" <<'PY'
import os
from app import app
from models import db, Admin

def ensure_tables_and_admin():
    with app.app_context():
        # 确保数据表存在
        db.create_all()

        # 可选：根据环境变量创建默认管理员
        username = os.getenv('ADMIN_USERNAME')
        password = os.getenv('ADMIN_PASSWORD')
        if username and password:
            admin = Admin.query.filter_by(username=username).first()
            if not admin:
                admin = Admin(username=username, email=f"{username}@example.com")
                admin.set_password(password)
                db.session.add(admin)
                db.session.commit()
                print(f"[init_db] admin created: {username}")
            else:
                print(f"[init_db] admin exists: {username}")
        else:
            print("[init_db] ADMIN_USERNAME/ADMIN_PASSWORD not set; skip admin creation")

if __name__ == '__main__':
    ensure_tables_and_admin()
PY
  chown "${USER_NAME}:${GROUP_NAME}" "${PROJECT_DIR}/scripts/init_db.py"
  ok "初始化脚本已创建: scripts/init_db.py"
}

create_systemd_services(){
  info "创建 systemd 服务文件..."

  cat >/etc/systemd/system/${SERVICE_1}.service <<EOF
[Unit]
Description=Pypo JT (Gunicorn)
After=network.target

[Service]
User=${USER_NAME}
Group=${GROUP_NAME}
WorkingDirectory=${PROJECT_DIR}
Environment=FLASK_ENV=production
Environment=FLASK_DEBUG=false
Environment=FLASK_HOST=127.0.0.1
Environment=FLASK_PORT=${PORT_1}
Environment=SECRET_KEY=${SECRET_1}
Environment=DATABASE_URL=sqlite:///${DB_1_PATH}
Environment=ADMIN_USERNAME=admin
Environment=ADMIN_PASSWORD=UB8uGkrHTKdbeV#
ExecStartPre=${VENV_DIR}/bin/python ${PROJECT_DIR}/scripts/init_db.py
ExecStart=${VENV_DIR}/bin/gunicorn -w 3 --threads 2 --timeout 120 \
  --bind 127.0.0.1:${PORT_1} app:app \
  --log-file /var/log/${SERVICE_1}/gunicorn.log --access-logfile /var/log/${SERVICE_1}/access.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

  cat >/etc/systemd/system/${SERVICE_2}.service <<EOF
[Unit]
Description=Pypo ZJS (Gunicorn)
After=network.target

[Service]
User=${USER_NAME}
Group=${GROUP_NAME}
WorkingDirectory=${PROJECT_DIR}
Environment=FLASK_ENV=production
Environment=FLASK_DEBUG=false
Environment=FLASK_HOST=127.0.0.1
Environment=FLASK_PORT=${PORT_2}
Environment=SECRET_KEY=${SECRET_2}
Environment=DATABASE_URL=sqlite:///${DB_2_PATH}
Environment=ADMIN_USERNAME=admin
Environment=ADMIN_PASSWORD=UB8uGkrHTKdbeV#
ExecStartPre=${VENV_DIR}/bin/python ${PROJECT_DIR}/scripts/init_db.py
ExecStart=${VENV_DIR}/bin/gunicorn -w 3 --threads 2 --timeout 120 \
  --bind 127.0.0.1:${PORT_2} app:app \
  --log-file /var/log/${SERVICE_2}/gunicorn.log --access-logfile /var/log/${SERVICE_2}/access.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable ${SERVICE_1} ${SERVICE_2}
  ok "systemd 服务已创建并启用"
}

start_services(){
  info "启动两个实例..."
  systemctl restart ${SERVICE_1}
  systemctl restart ${SERVICE_2}
  sleep 2
  systemctl --no-pager --full status ${SERVICE_1} | sed -n '1,12p' || true
  systemctl --no-pager --full status ${SERVICE_2} | sed -n '1,12p' || true
  ok "实例已启动"
}

create_nginx_sites(){
  info "创建 Nginx 站点配置..."

  cat >/etc/nginx/sites-available/${DOMAIN_1} <<EOF
server {
    listen 80;
    server_name ${DOMAIN_1};

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:${PORT_1};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 180;
    }
}
EOF

  cat >/etc/nginx/sites-available/${DOMAIN_2} <<EOF
server {
    listen 80;
    server_name ${DOMAIN_2};

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:${PORT_2};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 180;
    }
}
EOF

  ln -sf "/etc/nginx/sites-available/${DOMAIN_1}" "/etc/nginx/sites-enabled/${DOMAIN_1}"
  ln -sf "/etc/nginx/sites-available/${DOMAIN_2}" "/etc/nginx/sites-enabled/${DOMAIN_2}"

  # 关闭默认站点（如存在）
  if [ -e "/etc/nginx/sites-enabled/default" ]; then
    rm -f "/etc/nginx/sites-enabled/default"
  fi

  nginx -t
  systemctl reload nginx
  ok "Nginx 配置完成并重载"
}

post_tips(){
  cat <<TIPS
==============================================
部署完成!

- 实例1: http://${DOMAIN_1} → 127.0.0.1:${PORT_1}
- 实例2: http://${DOMAIN_2} → 127.0.0.1:${PORT_2}

如需启用 HTTPS:
  apt-get install -y certbot python3-certbot-nginx
  certbot --nginx -d ${DOMAIN_1} -d ${DOMAIN_2}

常用命令:
  systemctl status ${SERVICE_1} ${SERVICE_2}
  journalctl -u ${SERVICE_1} -f
  journalctl -u ${SERVICE_2} -f

日志位置:
  /var/log/${SERVICE_1}/
  /var/log/${SERVICE_2}/

如需调整端口/域名，请编辑 scripts/deploy_ubuntu.sh 顶部配置区后重新运行。
==============================================
TIPS
}

main(){
  require_root
  info "项目目录: ${PROJECT_DIR}"
  install_packages
  setup_venv
  prepare_dirs
  create_systemd_services
  start_services
  create_nginx_sites
  post_tips
}

main "$@"
