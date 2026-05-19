#!/usr/bin/env python3
"""
小马的 Hermes 工作监控面板 - 后端服务器（带密码保护）
"""

import os
import json
import glob
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, Response, render_template_string, make_response

app = Flask(__name__)

# ============================================================
# 配置
# ============================================================
# 登录密码（你可以改成自己想要的密码）
DASHBOARD_PASSWORD = "xiaoma2026"
# 会话过期时间（秒）
SESSION_TIMEOUT = 3600 * 8  # 8小时

HERMES_DIR = os.path.expanduser("~/.hermes")
SESSIONS_DIR = os.path.join(HERMES_DIR, "sessions")
CRON_DIR = os.path.join(HERMES_DIR, "cron")
PLANS_DIR = os.path.join(HERMES_DIR, "plans")
SKILLS_DIR = os.path.join(HERMES_DIR, "skills")
MEMORY_FILE = os.path.join(HERMES_DIR, "memory.json")
TODO_FILE = os.path.join(HERMES_DIR, "todo.json")

# 会话存储
active_sessions = {}

def check_auth(session_token):
    """检查会话是否有效"""
    if not session_token or session_token not in active_sessions:
        return False
    session = active_sessions[session_token]
    if datetime.now() > session["expires"]:
        del active_sessions[session_token]
        return False
    return True

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        session_token = request.cookies.get("session_token")
        if not check_auth(session_token):
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录"}), 401
            return LOGIN_PAGE
        return f(*args, **kwargs)
    return decorated


def read_json_safe(path):
    """安全读取 JSON 文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def get_system_status():
    """获取系统状态"""
    try:
        disk = subprocess.check_output(["df", "-h", "/"], text=True).split("\n")[1].split()
        mem = subprocess.check_output(["free", "-h"], text=True).split("\n")[1].split()
        uptime = subprocess.check_output(["uptime", "-p"], text=True).strip()
        
        return {
            "disk_used": disk[4],
            "disk_avail": disk[3],
            "mem_used": mem[2],
            "mem_total": mem[1],
            "uptime": uptime,
            "status": "运行中"
        }
    except Exception as e:
        return {"status": "未知", "error": str(e)}


def get_recent_sessions(limit=10):
    """获取最近的会话记录"""
    sessions = []
    session_dirs = sorted(glob.glob(os.path.join(SESSIONS_DIR, "*")), reverse=True)
    
    for session_dir in session_dirs[:limit]:
        meta_file = os.path.join(session_dir, "meta.json")
        meta = read_json_safe(meta_file)
        if meta:
            sessions.append({
                "id": os.path.basename(session_dir),
                "title": meta.get("title", "未命名会话"),
                "created": meta.get("created_at", ""),
                "updated": meta.get("updated_at", ""),
                "platform": meta.get("platform", ""),
            })
    
    return sessions


def get_cron_jobs():
    """获取定时任务"""
    jobs = []
    cron_files = glob.glob(os.path.join(CRON_DIR, "*.json"))
    
    for f in cron_files:
        job = read_json_safe(f)
        if job:
            job["_file"] = os.path.basename(f)
            jobs.append(job)
    
    return jobs


def get_skills_list():
    """获取已安装的技能列表"""
    skills = []
    skill_dirs = glob.glob(os.path.join(SKILLS_DIR, "*/SKILL.md"))
    
    for skill_file in skill_dirs:
        skill_dir = os.path.dirname(skill_file)
        skill_name = os.path.basename(skill_dir)
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read(500)
            skills.append({
                "name": skill_name,
                "path": skill_dir,
                "preview": content[:200] + "..." if len(content) > 200 else content
            })
        except:
            skills.append({"name": skill_name, "path": skill_dir})
    
    return skills


def get_recent_activity(limit=20):
    """获取最近的活动记录"""
    activities = []
    session_dirs = sorted(glob.glob(os.path.join(SESSIONS_DIR, "*")), reverse=True)
    
    for session_dir in session_dirs[:3]:
        messages_file = os.path.join(session_dir, "messages.json")
        messages = read_json_safe(messages_file)
        
        if messages and isinstance(messages, list):
            for msg in messages[-limit:]:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_parts.append(part.get("text", "")[:200])
                            elif part.get("type") == "tool_use":
                                text_parts.append(f"[调用工具: {part.get('name', '未知')}]")
                        elif isinstance(part, str):
                            text_parts.append(part[:200])
                    content = " ".join(text_parts)
                elif isinstance(content, str):
                    content = content[:300]
                else:
                    content = str(content)[:300]
                
                if content.strip():
                    activities.append({
                        "role": role,
                        "content": content,
                        "session": os.path.basename(session_dir),
                        "time": msg.get("timestamp", "")
                    })
    
    return activities[-limit:]


def get_memory_content():
    """获取记忆内容"""
    memory = read_json_safe(MEMORY_FILE)
    if not memory:
        return {"entries": [], "user_profile": ""}
    
    return {
        "entries": memory.get("memory", []),
        "user_profile": memory.get("user_profile", ""),
        "skills": memory.get("skills", [])
    }


def get_plans():
    """获取计划文件"""
    plans = []
    plan_files = glob.glob(os.path.join(PLANS_DIR, "*.md"))
    
    for f in plan_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            plans.append({
                "name": os.path.basename(f),
                "content": content[:500],
                "modified": datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M")
            })
        except:
            pass
    
    return plans


# ============================================================
# 登录页面
# ============================================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小马的 Hermes 监控面板 - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #0f1117 0%, #1a1d27 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: #1a1d27;
            border: 1px solid #2d3148;
            border-radius: 16px;
            padding: 40px;
            width: 360px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        .login-box h1 {
            text-align: center;
            color: #e4e6f0;
            font-size: 24px;
            margin-bottom: 8px;
        }
        .login-box .subtitle {
            text-align: center;
            color: #8b8fa3;
            font-size: 14px;
            margin-bottom: 32px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: #8b8fa3;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            background: #252836;
            border: 1px solid #2d3148;
            border-radius: 8px;
            color: #e4e6f0;
            font-size: 16px;
            outline: none;
            transition: border-color 0.2s;
        }
        .form-group input:focus {
            border-color: #6c5ce7;
        }
        .login-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .login-btn:hover {
            opacity: 0.9;
        }
        .error-msg {
            color: #e17055;
            font-size: 14px;
            text-align: center;
            margin-top: 16px;
            display: none;
        }
        .hint {
            text-align: center;
            color: #8b8fa3;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🐴 小马的监控面板</h1>
        <p class="subtitle">请输入密码访问</p>
        <form id="loginForm" onsubmit="handleLogin(event)">
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="password" placeholder="请输入访问密码" autofocus>
            </div>
            <button type="submit" class="login-btn">登 录</button>
            <p class="error-msg" id="errorMsg">密码错误，请重试</p>
        </form>
        <p class="hint">💡 默认密码: xiaoma2026</p>
    </div>
    <script>
        async function handleLogin(e) {
            e.preventDefault();
            const password = document.getElementById('password').value;
            try {
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password})
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = '/';
                } else {
                    document.getElementById('errorMsg').style.display = 'block';
                }
            } catch (err) {
                document.getElementById('errorMsg').style.display = 'block';
            }
        }
    </script>
</body>
</html>
"""


# ============================================================
# API 端点
# ============================================================

@app.route("/login", methods=["POST"])
def login():
    """处理登录"""
    data = request.get_json()
    password = data.get("password", "")
    
    if password == DASHBOARD_PASSWORD:
        session_token = secrets.token_hex(32)
        active_sessions[session_token] = {
            "created": datetime.now(),
            "expires": datetime.now() + timedelta(seconds=SESSION_TIMEOUT)
        }
        resp = make_response(jsonify({"success": True}))
        resp.set_cookie("session_token", session_token, httponly=True, max_age=SESSION_TIMEOUT)
        return resp
    
    return jsonify({"success": False, "error": "密码错误"})


@app.route("/logout")
def logout():
    """退出登录"""
    session_token = request.cookies.get("session_token")
    if session_token in active_sessions:
        del active_sessions[session_token]
    resp = make_response(jsonify({"success": True}))
    resp.delete_cookie("session_token")
    return resp


@app.route("/")
@require_auth
def index():
    """主页"""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/status")
@require_auth
def api_status():
    return jsonify(get_system_status())


@app.route("/api/sessions")
@require_auth
def api_sessions():
    return jsonify(get_recent_sessions(20))


@app.route("/api/cron")
@require_auth
def api_cron():
    return jsonify(get_cron_jobs())


@app.route("/api/skills")
@require_auth
def api_skills():
    return jsonify(get_skills_list())


@app.route("/api/activity")
@require_auth
def api_activity():
    return jsonify(get_recent_activity(30))


@app.route("/api/memory")
@require_auth
def api_memory():
    return jsonify(get_memory_content())


@app.route("/api/plans")
@require_auth
def api_plans():
    return jsonify(get_plans())


@app.route("/api/todos")
@require_auth
def api_todos():
    todos = read_json_safe(TODO_FILE)
    return jsonify(todos or [])


# ============================================================
# 主页面 HTML
# ============================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小马的 Hermes 监控面板</title>
    <style>
        :root {
            --bg: #0f1117;
            --surface: #1a1d27;
            --surface2: #252836;
            --border: #2d3148;
            --text: #e4e6f0;
            --text-muted: #8b8fa3;
            --accent: #6c5ce7;
            --accent-light: #a29bfe;
            --success: #00b894;
            --warning: #fdcb6e;
            --danger: #e17055;
            --info: #74b9ff;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, var(--accent) 0%, #a29bfe 100%);
            padding: 20px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(108, 92, 231, 0.3);
        }
        
        .header h1 {
            font-size: 22px;
            font-weight: 700;
            color: white;
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .status {
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            color: white;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .logout-btn {
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            transition: all 0.2s;
        }
        
        .logout-btn:hover {
            background: rgba(255,255,255,0.25);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00b894;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }
        
        .card {
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }
        
        .card-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .card-header h2 {
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .card-body {
            padding: 16px 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .card-body::-webkit-scrollbar { width: 6px; }
        .card-body::-webkit-scrollbar-track { background: var(--surface); }
        .card-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }
        
        .stat-item {
            background: var(--surface2);
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--accent-light);
        }
        
        .stat-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        
        .session-item, .activity-item, .skill-item, .plan-item {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
            background: var(--surface2);
            transition: background 0.2s;
        }
        
        .session-item:hover, .activity-item:hover { background: var(--border); }
        
        .session-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        .session-meta {
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            gap: 16px;
        }
        
        .activity-role {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 8px;
        }
        
        .role-user { background: var(--info); color: #000; }
        .role-assistant { background: var(--success); color: #000; }
        .role-system { background: var(--warning); color: #000; }
        
        .activity-content {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 6px;
            word-break: break-all;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .skill-name {
            font-weight: 600;
            color: var(--accent-light);
            font-size: 14px;
        }
        
        .skill-preview {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .plan-name {
            font-weight: 600;
            color: var(--warning);
            font-size: 14px;
        }
        
        .plan-time {
            font-size: 11px;
            color: var(--text-muted);
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-muted);
        }
        
        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 12px;
        }
        
        .badge {
            background: var(--accent);
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }
        
        .refresh-btn {
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        
        .refresh-btn:hover {
            background: var(--accent);
            border-color: var(--accent);
        }
        
        .full-width { grid-column: 1 / -1; }
        
        .memory-section { margin-bottom: 16px; }
        
        .memory-section h3 {
            font-size: 14px;
            color: var(--accent-light);
            margin-bottom: 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid var(--border);
        }
        
        .memory-entry {
            font-size: 13px;
            color: var(--text-muted);
            padding: 6px 0;
            border-bottom: 1px dashed var(--border);
        }
        
        .memory-entry:last-child { border-bottom: none; }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 12px;
        }
        
        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 12px; text-align: center; }
            .grid { grid-template-columns: 1fr; }
            .stat-grid { grid-template-columns: 1fr; }
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }
        
        .spinner {
            width: 32px;
            height: 32px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .timestamp {
            font-size: 11px;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐴 小马的 Hermes 监控面板</h1>
        <div class="header-right">
            <div class="status">
                <span class="status-dot"></span>
                <span id="system-status">连接中...</span>
            </div>
            <a href="/logout" class="logout-btn">退出登录</a>
        </div>
    </div>
    
    <div class="container">
        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <h2>📊 系统状态</h2>
                    <button class="refresh-btn" onclick="loadStatus()">刷新</button>
                </div>
                <div class="card-body">
                    <div class="stat-grid" id="status-content">
                        <div class="loading"><div class="spinner"></div></div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>⏰ 定时任务</h2>
                    <span class="badge" id="cron-count">0</span>
                </div>
                <div class="card-body" id="cron-content">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card full-width">
                <div class="card-header">
                    <h2>📝 最近活动</h2>
                    <button class="refresh-btn" onclick="loadActivity()">刷新</button>
                </div>
                <div class="card-body" id="activity-content" style="max-height: 500px;">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <h2>💬 历史会话</h2>
                    <span class="badge" id="session-count">0</span>
                </div>
                <div class="card-body" id="sessions-content">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>🛠️ 已安装技能</h2>
                    <span class="badge" id="skill-count">0</span>
                </div>
                <div class="card-body" id="skills-content">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-header">
                    <h2>🧠 记忆存储</h2>
                    <button class="refresh-btn" onclick="loadMemory()">刷新</button>
                </div>
                <div class="card-body" id="memory-content" style="max-height: 500px;">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>📋 执行计划</h2>
                    <span class="badge" id="plan-count">0</span>
                </div>
                <div class="card-body" id="plans-content">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>小马的 Hermes 监控面板 · 自动刷新间隔 30 秒</p>
    </div>
    
    <script>
        async function fetchData(url) {
            try {
                const res = await fetch(url);
                if (res.status === 401) {
                    window.location.href = '/';
                    return null;
                }
                return await res.json();
            } catch (e) {
                console.error('加载失败:', url, e);
                return null;
            }
        }
        
        async function loadStatus() {
            const data = await fetchData('/api/status');
            if (!data) return;
            
            document.getElementById('system-status').textContent = data.status || '运行中';
            
            const html = `
                <div class="stat-item">
                    <div class="stat-value">${data.mem_used || '-'}</div>
                    <div class="stat-label">内存使用</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.mem_total || '-'}</div>
                    <div class="stat-label">内存总量</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.disk_used || '-'}</div>
                    <div class="stat-label">磁盘使用</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.disk_avail || '-'}</div>
                    <div class="stat-label">磁盘可用</div>
                </div>
            `;
            document.getElementById('status-content').innerHTML = html;
        }
        
        async function loadSessions() {
            const data = await fetchData('/api/sessions');
            if (!data || !data.length) {
                document.getElementById('sessions-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">💬</div>
                        <p>暂无会话记录</p>
                    </div>
                `;
                return;
            }
            
            document.getElementById('session-count').textContent = data.length;
            
            const html = data.map(s => `
                <div class="session-item">
                    <div class="session-title">${s.title || '未命名会话'}</div>
                    <div class="session-meta">
                        <span>🕐 ${s.updated || s.created || '-'}</span>
                        <span>📱 ${s.platform || '-'}</span>
                    </div>
                </div>
            `).join('');
            
            document.getElementById('sessions-content').innerHTML = html;
        }
        
        async function loadCron() {
            const data = await fetchData('/api/cron');
            if (!data || !data.length) {
                document.getElementById('cron-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⏰</div>
                        <p>暂无定时任务</p>
                    </div>
                `;
                return;
            }
            
            document.getElementById('cron-count').textContent = data.length;
            
            const html = data.map(j => `
                <div class="session-item">
                    <div class="session-title">${j.name || j.prompt?.substring(0, 50) || '未命名任务'}</div>
                    <div class="session-meta">
                        <span>⏰ ${j.schedule || '-'}</span>
                        <span>${j.enabled === false ? '⏸️ 已暂停' : '▶️ 运行中'}</span>
                    </div>
                </div>
            `).join('');
            
            document.getElementById('cron-content').innerHTML = html;
        }
        
        async function loadSkills() {
            const data = await fetchData('/api/skills');
            if (!data || !data.length) {
                document.getElementById('skills-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">🛠️</div>
                        <p>暂无安装技能</p>
                    </div>
                `;
                return;
            }
            
            document.getElementById('skill-count').textContent = data.length;
            
            const html = data.map(s => `
                <div class="skill-item">
                    <div class="skill-name">📦 ${s.name}</div>
                    <div class="skill-preview">${s.preview || ''}</div>
                </div>
            `).join('');
            
            document.getElementById('skills-content').innerHTML = html;
        }
        
        async function loadActivity() {
            const data = await fetchData('/api/activity');
            if (!data || !data.length) {
                document.getElementById('activity-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">📝</div>
                        <p>暂无活动记录</p>
                    </div>
                `;
                return;
            }
            
            const html = data.map(a => `
                <div class="activity-item">
                    <span class="activity-role role-${a.role}">${a.role === 'user' ? '👤 用户' : a.role === 'assistant' ? '🐴 小马' : '⚙️ 系统'}</span>
                    <span class="timestamp">${a.time || ''}</span>
                    <div class="activity-content">${escapeHtml(a.content)}</div>
                </div>
            `).join('');
            
            document.getElementById('activity-content').innerHTML = html;
        }
        
        async function loadMemory() {
            const data = await fetchData('/api/memory');
            if (!data) return;
            
            let html = '';
            
            if (data.user_profile) {
                html += `
                    <div class="memory-section">
                        <h3>👤 用户档案</h3>
                        <div class="memory-entry">${escapeHtml(data.user_profile)}</div>
                    </div>
                `;
            }
            
            if (data.entries && data.entries.length) {
                html += `
                    <div class="memory-section">
                        <h3>📝 记忆条目 (${data.entries.length})</h3>
                        ${data.entries.map(e => `<div class="memory-entry">• ${escapeHtml(e)}</div>`).join('')}
                    </div>
                `;
            }
            
            if (!html) {
                html = `
                    <div class="empty-state">
                        <div class="icon">🧠</div>
                        <p>暂无记忆存储</p>
                    </div>
                `;
            }
            
            document.getElementById('memory-content').innerHTML = html;
        }
        
        async function loadPlans() {
            const data = await fetchData('/api/plans');
            if (!data || !data.length) {
                document.getElementById('plans-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">📋</div>
                        <p>暂无执行计划</p>
                    </div>
                `;
                return;
            }
            
            document.getElementById('plan-count').textContent = data.length;
            
            const html = data.map(p => `
                <div class="plan-item">
                    <div class="plan-name">📄 ${p.name}</div>
                    <div class="plan-time">🕐 ${p.modified}</div>
                    <div class="activity-content">${escapeHtml(p.content)}</div>
                </div>
            `).join('');
            
            document.getElementById('plans-content').innerHTML = html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function loadAll() {
            await Promise.all([
                loadStatus(),
                loadSessions(),
                loadCron(),
                loadSkills(),
                loadActivity(),
                loadMemory(),
                loadPlans()
            ]);
        }
        
        loadAll();
        setInterval(loadAll, 30000);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import subprocess
    
    print("=" * 50)
    print("🐴 小马的 Hermes 监控面板")
    print("=" * 50)
    print(f"🔐 登录密码: {DASHBOARD_PASSWORD}")
    print(f"🌐 访问地址: http://0.0.0.0:8080")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=8080, debug=False)
