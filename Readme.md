# 🤖 Multi-Agent Email Management System

An intelligent email management system built with LangGraph, LangChain, and Streamlit that automates email operations using Google's Gemini AI.

## ✨ Features

- 📧 **Email Operations**: Send, read, search, and manage emails
- 🔍 **Smart Search**: AI-powered email search with natural language
- 💾 **Persistent Memory**: Session history stored in MongoDB
- 🧠 **Conversational AI**: Natural language interface powered by Gemini
- 🔄 **Multi-turn Conversations**: Maintains context across interactions
- 📊 **Session Management**: Track and save conversation history
- 🛠️ **Tool Integration**: 19+ Gmail operations available

## 🏗️ Architecture

```
┌─────────────┐
│  Streamlit  │ ← User Interface
└──────┬──────┘
       │
┌──────▼───────┐
│  LangGraph   │ ← Orchestration Layer
│   (Agent)    │
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
┌──▼──┐  ┌─▼────┐
│ LLM │  │Tools │ ← Gmail API Operations
│Node │  │Node  │
└─────┘  └──────┘
   │
┌──▼────────┐
│  MongoDB  │ ← Session Storage
└───────────┘
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd email-agent-system
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Environment Variables
Create `.env` file:
```env
MONGODB_URI=mongodb://localhost:27017
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download as `credentials.json`
5. Place in project root

### 5. First-time Authentication
```bash
python Operations/email_operations.py
```
This creates `token.pickle` for future use.

### 6. Run Application
```bash
streamlit run ground.py
```

Visit `http://localhost:8501`

## 📋 Available Email Operations

### Reading Emails
- Get recent emails
- Get unread emails
- Search emails with queries
- Get emails from specific sender
- Get emails by date range
- Get email body content
- Get emails with attachments
- Get starred emails

### Email Actions
- Send new email
- Reply to email
- Mark as read/unread
- Delete email (move to trash)
- Add labels

### Statistics
- Get inbox stats
- Count emails by query
- Count emails from sender
- Count emails in date range

## 💬 Usage Examples

```
User: "Show me my last 5 emails"
User: "Search for emails from john@example.com"
User: "Send an email to jane@example.com about the meeting"
User: "How many unread emails do I have?"
User: "Get all emails from last week"
```

## 🗂️ Project Structure

```
email-agent-system/
├── ground.py                 # Main Streamlit application
├── system_prompt.py          # AI system prompt configuration
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── credentials.json          # Gmail OAuth (create this)
├── token.pickle             # Generated after auth
├── README.md                # This file
├── .gitignore               # Git ignore rules
└── Operations/
    ├── __init__.py
    └── email_operations.py  # Gmail API tools
```

## 🔧 Configuration

### MongoDB
- **Local**: `mongodb://localhost:27017`
- **Atlas**: `mongodb+srv://user:pass@cluster.mongodb.net/`

### Gemini API
Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Gmail API Scopes
```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]
```

## 🔒 Security

⚠️ **Important**: Never commit these files:
- `.env` - Contains API keys
- `credentials.json` - Gmail OAuth credentials
- `token.pickle` - Authentication token

Always use environment variables for sensitive data.

## 🐛 Troubleshooting

### Gmail Authentication Error
```bash
# Delete and recreate token
rm token.pickle
python Operations/email_operations.py
```

### MongoDB Connection Error
- Ensure MongoDB is running: `mongod`
- Check connection string in `.env`
- For Atlas, verify IP whitelist

### Module Import Errors
```bash
pip install -r requirements.txt --upgrade
```

## 📊 Session Management

Sessions are automatically saved to MongoDB with:
- Session ID
- Start/End timestamps
- Full conversation history
- User inputs
- Tool calls and responses

Access via sidebar's "Clear Chat & Save Session" button.

## 🚀 Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in dashboard
4. Deploy

### Docker
```bash
docker build -t email-agent .
docker run -p 8501:8501 email-agent
```

### Heroku
```bash
heroku create your-app
git push heroku main
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **AI Framework**: LangChain, LangGraph
- **LLM**: Google Gemini 2.0 Flash
- **Email API**: Gmail API
- **Database**: MongoDB
- **Language**: Python 3.9+

## 📈 Performance

- Average response time: < 3 seconds
- Gmail API rate limit: 250 quota units per user per second
- MongoDB connection pooling enabled
- Efficient token usage with context management

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- LangChain & LangGraph teams
- Google Gemini AI
- Streamlit community
- MongoDB team

## 📞 Support

For issues or questions:
1. Check [Troubleshooting](#-troubleshooting)
2. Review [Deployment Guide](DEPLOYMENT.md)
3. Open an issue on GitHub

---

**Made with ❤️ using LangGraph and Streamlit**

**Version**: 1.0.0  
**Last Updated**: January 2026