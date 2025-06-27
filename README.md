# 🕰️ Time Capsule Bot - Nothing Wall

A magical Telegram bot that lets your messages travel through time, reappearing at an unknown moment in the future.

## ✨ Features

- 📮 **Time Capsules**: Send any message and it will be returned to you at a random time (30 days-3 years)
- 🌍 **Anonymous Sharing**: Choose to share your opened time capsules anonymously on the public wisdom wall
- 🎨 **Beautiful Web Display**: Built-in "Nothing Wall" webpage showcasing all shared time capsules
- 🔄 **Auto-Restart**: Automatically restarts on network errors to ensure stable service
- 🐳 **Docker Support**: Complete Docker deployment solution
- 🌐 **Built-in Web Server**: Hosts static pages with CORS support

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token
- Docker (optional)

### Local Development

1. **Clone the project**
```bash
git clone git@github.com:kkter/TimeCapsule-NothingWall.git
cd TimeCapsule-NothingWall
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set environment variables**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export ADMIN_CHAT_ID="your_chat_id_here"  # Optional
```

4. **Run the bot**
```bash
python time_capsule.py
```

### Docker Deployment

1. **Create .env file**
```bash
echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
echo "ADMIN_CHAT_ID=your_chat_id_here" >> .env
```

2. **Run deployment script**
```bash
chmod +x deploy.sh
./deploy.sh
```

Or manually:
```bash
docker-compose up -d --build
```

## 🎯 Usage

### Bot Commands

- **Send any message** - Create a time capsule
- `/status` - Check your time capsule statistics
- `/wall` - Get the public wisdom wall link
- `/help` - Show help information

### Web Access

After startup, visit:
- Local: `http://localhost:9000`
- Production: `https://your-domain.com`

## 📂 Project Structure

```
TimeCapsule-部署/
├── time_capsule.py           # Main application file
├── index.html               # Nothing Wall webpage
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── deploy.sh              # Deployment script
├── auto_backup_timecapsule.sh  # Auto backup script
├── README.md              # Project documentation
├── sitemap.xml           # SEO sitemap
├── robots.txt           # SEO robots file
├── favicon.ico          # Website favicon
├── favicon-32x32.png    # Website favicon
├── apple-touch-icon.png # Apple touch icon
└── data/               # Data directory (created at runtime)
    └── time_capsules.json  # Time capsule data
```

## 🔧 Configuration

### Environment Variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token (required)
- `ADMIN_CHAT_ID`: Admin user ID (optional, enables quick test mode)

### Time Configuration

The system automatically selects mode based on user identity:

```python
# Admin mode: 1-3 minutes (for quick testing and content generation)
if user_id == ADMIN_CHAT_ID:
    delay_minutes = random.randint(1, 3)

# User mode: 30 days to 3 years
else:
    delay_days = random.randint(30, 1095)
```

### Getting Your Chat ID

Send `/start` to [@userinfobot](https://t.me/userinfobot) to get your Chat ID.

### Web Server Port

Default port is 9000, can be modified in the code:
```python
WEB_PORT = 9000
```

## 📊 Data Storage

The project uses JSON files for data storage:

- **time_capsules.json**: Stores all time capsules with metadata

Data structure example:
```json
{
  "user_id": 123456789,
  "message": "Hello, future me!",
  "created_at": "2025-01-15T10:30:00",
  "send_at": "2025-01-15T10:33:00",
  "sent": false,
  "shared": false
}
```

## 🎨 Nothing Wall Features

- 🌌 **Cosmic Theme**: Starry background with beautiful gradient effects
- 💫 **Dynamic Bubbles**: 4 different floating animations
- 🎯 **Interactive Elements**: Click bubbles to pause for 3 seconds
- 📱 **Responsive Design**: Supports both mobile and desktop
- 🌈 **Random Colors**: 8 gradient color schemes randomly assigned

## 🚀 Deployment Guide

### Prerequisites for Production

1. **Create Docker network** (if not exists):
```bash
docker network create app_network
```

2. **Set up environment variables**:
```bash
# Create .env file with your tokens
TELEGRAM_BOT_TOKEN=your_actual_bot_token
ADMIN_CHAT_ID=your_actual_chat_id
```

### Regular Updates

**Recommended deployment process:**

```bash
# Fetch latest changes
git fetch origin main
git reset --hard origin/main

# Deploy
./deploy.sh
```

**Alternative step-by-step:**

```bash
# Stop containers
docker-compose down

# Rebuild and start
docker-compose up -d --build

# Check logs
docker-compose logs -f
```

## 🔄 Auto Backup

The project includes an automatic backup system for data files.

### Setup Cron Jobs

```bash
# Edit crontab
crontab -e

# Commit changes every hour
0 * * * * cd /path/to/TimeCapsule && ./auto_backup_timecapsule.sh >> logs/cron_commit_job.log 2>&1

# Push to GitHub daily at 23:05
5 23 * * * cd /path/to/TimeCapsule && ./auto_backup_timecapsule.sh push >> logs/cron_push_job.log 2>&1
```

## 🛠️ Version History

- **v2.4.7**: Modified Docker network configuration to join existing app_network
- **v2.4.6**: Fixed Git workflow and improved auto backup script
- **v2.4.5**: Added favicon and SEO files to Docker build
- **v2.4.4**: Simplified favicon paths
- **v2.4.3**: Added SEO optimization and semantic HTML
- **v2.4.2**: Fixed version display consistency
- **v2.4.1**: Added analytics tracking
- **v2.4.0**: Removed redundant shared_messages.json logic
- **v2.2.2**: Built-in web server with CORS support
- **v2.2.1**: Network error handling and auto-restart
- **v2.2.0**: Improved user experience and message formatting
- **v2.1.0**: Added sharing functionality and wisdom wall
- **v2.0.0**: User management and command support
- **v1.0.0**: Basic time capsule functionality

## 🔧 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if `TELEGRAM_BOT_TOKEN` is correctly set
   - Review console log output

2. **Web page inaccessible**
   - Confirm port 9000 is not occupied
   - Check firewall settings

3. **Docker deployment failure**
   - Ensure Docker and Docker Compose are installed
   - Check if `.env` file exists
   - Verify `app_network` exists: `docker network ls`

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f

# Direct execution logs
# Check console output
```

## 🌍 Live Demo

Visit the live Nothing Wall: [https://nothingwall.com](https://nothingwall.com)

Try the Telegram bot: [@MoonTimeCapsuleBot](https://t.me/MoonTimeCapsuleBot)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit Issues and Pull Requests.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License

## 🙏 Acknowledgments

Thanks to all the users and contributors who make this project possible! Let's leave beautiful footprints in the river of time together.

---

*"Time never speaks, but answers all questions." - From a Time Capsule*

---

## 📬 Contact

For questions or support, please open an issue on GitHub or contact the project maintainer.

---

**Made with ❤️ for time travelers around the world**