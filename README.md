# AI Skill Generator

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-blue?style=flat&logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-blue?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-blue?style=flat&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/PostgreSQL-14+-blue?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="License">
</p>

> 🎯 Convert documents and web content into reusable AI skills with embeddings for semantic search.

**Note:** This project does not require opencode to run. It's a standalone web application.

## ✨ Features

- 📤 **Upload PDFs** - Drag & drop PDF files
- 🌐 **Crawl Websites** - Extract content from web pages to create skills (bulk or single page)
- 🤖 **AI Extraction** - Automatic knowledge extraction with embeddings (local or API-based)
- 💬 **Query Skills** - Ask questions using RAG
- 📥 **Download Skills** - Export in `.skill`, `.md`, or `.json` formats
- 🗑️ **Delete Skills** - Manage your skills easily
- 🐳 **Docker Ready** - One-command deployment
- ⚡ **CLI Tool** - Generate skills from PDF files or URLs without running the server

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-skill-generator.git
cd ai-skill-generator

# Copy environment template
cp .env.sample .env
# Edit .env with your settings (optional - defaults work out of the box)

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

## ⚡ CLI Tool

Standalone CLI to generate skills from PDFs or URLs without running the web server.

### Download

Get pre-built binaries from [GitHub Releases](https://github.com/YOUR_USERNAME/ai-skill-generator/releases/latest):
- `ai-skill-generator-windows-x64.exe` - Windows
- `ai-skill-generator-linux-x64` - Linux

### Usage

```bash
# Generate skill from PDF
ai-skill-generator sample.pdf

# Generate skill from URL (crawls entire website)
ai-skill-generator https://docs.example.com

# Custom output directory
ai-skill-generator sample.pdf -o my_output

# Limit crawling pages
ai-skill-generator https://example.com -m 50
```

### Output

Generates `output/<name>_skills/` directory with:
- `name.md` - Plain text markdown
- `name.json` - Full data with embeddings
- `name.skill` - Text + vector embeddings for AI agents

### Build from Source

```bash
cd backend

# Windows
build_cli.bat

# Linux/Mac
chmod +x build_cli.sh && ./build_cli.sh
```

---

## 📁 Project Structure

```
ai-skill-generator/
├── .github/
│   └── workflows/
│       └── build-cli.yml          # GitHub Actions for CLI builds
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
│   ├── 📄 cli.py                   # CLI tool source
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
| `POST` | `/crawl` | 🌐 Crawl website to create skill |
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

Copy the template before running:

```bash
cp .env.sample .env
```

| Variable | Description | Default |
|:---------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@db:5432/ai_skill_generator` |
| `LLM_API_KEY` | MiniMax API key (optional — required only for `/query` endpoint) | - |
| `LLM_API_BASE` | LLM API base URL | `https://api.minimax.chat/v1` |
| `EMBED_MODEL_NAME` | Embedding model (local: `all-MiniLM-L6-v2`, or API: `text-embedding-3-small`) | `all-MiniLM-L6-v2` |
| `EMBED_API_KEY` | API key for external embedding provider (e.g., OpenAI) | - |
| `EMBED_API_BASE` | API base URL for external embeddings (leave empty for local model) | - |

**Note:** If using an API-based embedding model, `EMBED_API_KEY` and `EMBED_API_BASE` are required. If using the local default model, no additional setup is needed — the model downloads automatically on first use.

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