# 📄 PDF to Skill

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-blue?style=flat&logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-blue?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-blue?style=flat&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/PostgreSQL-14+-blue?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="License">
</p>

> 🎯 Convert PDFs into reusable AI skills with embeddings for semantic search.

## ✨ Features

- 📤 **Upload PDFs** - Drag & drop PDF files
- 🤖 **AI Extraction** - Automatic knowledge extraction with embeddings
- 💬 **Query Skills** - Ask questions using RAG
- 📥 **Download Skills** - Export in `.skill`, `.md`, or `.json` formats
- 🗑️ **Delete Skills** - Manage your skills easily
- 🐳 **Docker Ready** - One-command deployment

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/pdftoskill.git
cd pdftoskill

# Start all services
docker-compose up --build
```

Then open:
- 🌐 **Frontend**: http://localhost
- 🔌 **API**: http://localhost:8000

---

### Local Development

#### 1️⃣ Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.sample .env
# Edit .env with your database URL

# Run server
python -m uvicorn app.main:app --port 8000
```

#### 2️⃣ Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open http://localhost:5173

---

## 📁 Project Structure

```
pdftoskill/
├── 🐳 docker-compose.yml          # Docker orchestration
├── 📝 README.md                    # This file
│
├── 🐍 backend/
│   ├── 📂 app/                    # Application code
│   │   ├── database.py            # SQLAlchemy models
│   │   ├── main.py                # API endpoints
│   │   └── services.py            # PDF extraction, embeddings
│   ├── 📂 database/
│   │   └── schema.sql             # Database schema
│   ├── 🐳 Dockerfile               # Backend container
│   ├── 📄 requirements.txt
│   └── 📄 .env.sample             # Environment template
│
└── ⚛️ frontend/
    ├── 📂 src/                    # React source
    ├── 🐳 Dockerfile              # Frontend container
    ├── 📄 nginx.conf              # Nginx config
    └── 📄 package.json
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `POST` | `/upload` | 📤 Upload PDF to create skill |
| `GET` | `/skills` | 📋 List all skills |
| `GET` | `/skills/{id}` | 🔍 Get skill details |
| `POST` | `/skills/{id}/query` | 💬 Query a skill |
| `GET` | `/skills/{id}/download` | 📥 Download skill |
| `DELETE` | `/skills/{id}` | 🗑️ Delete a skill |
| `GET` | `/health` | ❤️ Health check |

---

## 📦 Skill Formats

| Format | Description | Best For |
|:------:|-------------|----------|
| `.skill` | 📝 Text + embeddings | AI agents for semantic search |
| `.md` | 📄 Plain text | Copy-paste to Claude/ChatGPT |
| `.json` | 📊 Full data | RAG systems, programmatic use |

---

## 🐳 Docker Commands

```bash
# 🚀 Start all services
docker-compose up

# 🔄 Start in background
docker-compose up -d

# 📜 View logs
docker-compose logs -f

# 🛑 Stop all services
docker-compose down

# 🔨 Rebuild containers
docker-compose up --build
```

---

## ⚙️ Environment Variables

| Variable | Description | Default |
|:---------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/pdftoskill` |
| `LLM_API_KEY` | MiniMax API key (optional) | - |
| `LLM_API_BASE` | LLM API base URL | `https://api.minimax.chat/v1` |
| `EMBED_MODEL_NAME` | Embedding model | `all-MiniLM-L6-v2` |

---

## 🤝 Contributing

1. 🍴 Fork the repository
2. 🌿 Create a feature branch
3. 📝 Make your changes
4. ✅ Run tests
5. 📤 Submit a pull request

---

## 📜 License

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Sentence Transformers](https://sbert.net/) - Embedding models
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [React](https://react.dev/) - UI library
- [Tailwind CSS](https://tailwindcss.com/) - Styling

---

<p align="center">
  Made with ❤️ for AI enthusiasts
</p>