# 🐴 Hermes Agent 监控面板

一个轻量级的 Web 监控面板，用于远程查看 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的工作状态。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 功能特性

- 📊 **系统状态监控** — 实时查看内存、磁盘使用情况
- 📝 **活动记录** — 查看 Agent 最近执行的任务
- 💬 **历史会话** — 浏览过去的对话记录
- 🛠️ **技能列表** — 查看已安装的 Agent 技能
- 🧠 **记忆存储** — 查看 Agent 的长期记忆内容
- 📋 **执行计划** — 查看待执行的任务计划
- ⏰ **定时任务** — 查看已设置的定时任务
- 🔐 **密码保护** — 支持登录认证，保护隐私数据
- 📱 **响应式设计** — 支持手机和电脑访问

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/hermes-dashboard.git
cd hermes-dashboard
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
python server.py
```

### 4. 访问面板

打开浏览器访问：`http://localhost:8080`

默认密码：`xiaoma2026`

## ⚙️ 配置

编辑 `server.py` 文件顶部的配置项：

```python
# 登录密码（建议修改）
DASHBOARD_PASSWORD = "xiaoma2026"

# 会话过期时间（秒）
SESSION_TIMEOUT = 3600 * 8  # 8小时
```

## 🌐 远程访问

如果需要从外网访问，需要：

1. 开放服务器的 8080 端口
2. 在防火墙/安全组中添加入站规则：
   - 端口：`8080`
   - 协议：`TCP`
   - 来源：`0.0.0.0/0`

## 📁 项目结构

```
hermes-dashboard/
├── server.py           # 主程序（Flask 后端 + 前端页面）
├── requirements.txt    # Python 依赖
├── start.sh           # 启动脚本
├── .gitignore         # Git 忽略文件
├── LICENSE            # MIT 开源许可证
└── README.md          # 项目说明
```

## 🔒 安全说明

- ✅ 支持密码登录认证
- ✅ 会话自动过期（默认 8 小时）
- ✅ Cookie 设置 HttpOnly
- ⚠️ 建议修改默认密码
- ⚠️ 生产环境建议使用 HTTPS

## 🛠️ 技术栈

- **后端**: Python + Flask
- **前端**: 原生 HTML/CSS/JavaScript
- **数据源**: Hermes Agent 的 ~/.hermes/ 目录

## 📝 更新日志

### v1.0.0 (2026-05-19)
- ✨ 初始版本发布
- 📊 系统状态监控
- 📝 活动记录查看
- 🔐 密码登录保护

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

## 🙏 致谢

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — 强大的 AI Agent 框架
- [Flask](https://flask.palletsprojects.com/) — 轻量级 Web 框架

---

**作者**: 小马的 AI 助手  
**联系方式**: 通过 GitHub Issues 联系
