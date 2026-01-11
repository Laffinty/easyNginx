# easyNginx

A professional Windows GUI tool for Nginx configuration management.

> ⚠️ **Under Active Development** - Not yet ready for production use.

## Features

- **Visual Configuration Management**: Intuitive GUI for managing Nginx sites
- **Auto-Discovery**: Automatic detection of local and system Nginx installations
- **Multi-Language Support**: Built-in internationalization system
- **Dark/Light Themes**: Customizable UI themes
- **Backup & Restore**: Safe configuration management with backup capabilities
- **Process Control**: Start, stop, and monitor Nginx processes
- **MVVM Architecture**: Clean separation of concerns with ViewModels

## System Requirements

- Windows 10/11
- Python 3.8+
- Nginx for Windows
- PySide6

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run from Source

```bash
python main.py
```

Run as administrator for full functionality.

### Build Executable

```bash
pyinstaller main.spec
```

## Project Structure

```
easyNginx/
├── main.py              # Entry point
├── models/              # Data models
├── views/               # UI components
├── viewmodels/          # Business logic
├── services/            # Core services
├── utils/               # Utilities
├── templates/           # Nginx config templates
└── logs/                # Application logs
```

## License

[MIT License](LICENSE)
