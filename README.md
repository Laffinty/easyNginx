# easyNginx

> 🚧 **Under Active Development** - This project is currently in development and not yet ready for production use.

Nginx management tool with GUI.

## ✨ 核心功能

### 自动配置同步
**软件启动时自动读取 nginx.conf 并同步站点配置**，无需手动导入：

- ✅ 自动检测 Nginx 安装和配置文件
- ✅ 解析所有 `server` 块并识别站点类型（静态/PHP/反向代理）
- ✅ 支持 `include` 指令，读取分散的配置文件
- ✅ 去重处理，避免重复站点
- ✅ 完整保留原有配置，安全接管现有环境

### 支持的站点类型
- **静态站点** - HTML/CSS/JS 网站
- **PHP 站点** - 支持 PHP-FPM（Unix Socket 和 TCP）
- **反向代理** - 反向代理和 WebSocket 支持
- **HTTPS/SSL** - 完整 SSL 证书管理

### 生产级特性
- ⚡ 性能优化基线（F5/CIS 最佳实践）
- 🔒 安全加固配置
- 💾 自动备份和恢复
- 🎯 配置语法测试
- 📊 实时监控 Nginx 状态

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Nginx for Windows
- Windows 10/11 或 Windows Server

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd easyNginx
```

2. **创建虚拟环境**（推荐）
```bash
python -m venv venv
venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

### 首次运行

```bash
python main.py
```

程序启动后会自动：
1. 检测系统中的 Nginx 安装
2. 弹出接管对话框（首次使用）
3. 读取 nginx.conf 同步现有站点
4. 显示站点列表和管理界面

## 📚 详细文档

- [配置同步功能详解](CONFIG_SYNC_README.md) - 了解如何同步现有 Nginx 配置
- API 文档 - 开发文档（即将推出）
- 用户手册 - 完整使用指南（即将推出）

## 🛠️ 开发

### 项目结构
```
easyNginx/
├── main.py                      # 应用程序入口
├── models/                      # 数据模型
│   ├── site_config.py          # 站点配置模型
│   └── nginx_status.py         # Nginx 状态模型
├── services/                    # 业务服务
│   ├── nginx_service.py        # Nginx 进程管理
│   ├── config_parser.py        # 配置解析器（核心）
│   └── config_generator.py     # 配置生成器
├── viewmodels/                  # 视图模型（MVVM）
│   └── main_viewmodel.py       # 主视图模型
├── views/                       # UI 视图
│   ├── main_window.py          # 主窗口
│   └── takeover_dialog.py      # Nginx 接管对话框
├── templates/                   # Nginx 配置模板
│   ├── static_site.conf.j2
│   ├── php_site.conf.j2
│   └── proxy_site.conf.j2
├── utils/                       # 工具类
│   ├── logger.py               # 日志管理
│   ├── theme_manager.py        # 主题管理
│   ├── config_registry.py      # 注册表配置
│   └── language_manager.py     # 语言管理
├── logs/                        # 日志文件
├── temp/                        # 临时文件
└── translations/                # 多语言资源
```

### 配置解析流程

```
启动应用
    ↓
检测 Nginx 路径
    ↓
读取 nginx.conf
    ↓
解析 server 块
    ↓
识别站点类型
    ↓
处理 include 指令
    ↓
去重和验证
    ↓
显示站点列表
```

## 🧪 测试

### 测试配置同步功能

```bash
# 使用示例配置测试
python test_config_sync.py

# 或指定自定义配置
python test_config_sync.py --config /path/to/nginx.conf
```

### 查看日志

```bash
# 实时监控日志
type logs\app.log

# 或执行实时查看
Get-Content logs\app.log -Wait
```

## 📝 更新日志

### v1.0 (开发中)
- ✅ 自动配置同步（从 nginx.conf 读取站点）
- ✅ 支持静态/PHP/反向代理站点
- ✅ Include 指令支持
- ✅ 配置备份和恢复
- ✅ Nginx 进程管理
- ✅ 实时状态监控

## 🤝 贡献

欢迎贡献代码、提出问题或建议！

## ⚖️ 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⚠️ 免责声明

本项目正在积极开发中，尚未达到生产就绪状态。在用于生产环境前，请充分测试并备份重要配置。

## 🙏 致谢

- Nginx - 卓越的 Web 服务器
- PySide6 - Qt for Python
- Loguru - 优雅的日志库
- Jinja2 - 强大的模板引擎

