<div align="center">

# ⚡ AI Skill Generator

**Turn any PDF or website into an AI skill file in seconds.**

Upload a document or paste a URL → get ready-to-use skill files for Claude, Cursor, Copilot, OpenCode, Windsurf, Cline, Aider and more.

[![Release](https://img.shields.io/github/v/release/rahulroy0611/ai-skill-generator?style=flat-square&color=6366f1)](../../releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/rahulroy0611/ai-skill-generator/build-cli.yml?style=flat-square&label=CLI%20build)](../../actions/workflows/build-cli.yml)
[![License](https://img.shields.io/github/license/rahulroy0611/ai-skill-generator?style=flat-square&color=10b981)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)

<br/>

[**Download CLI**](../../releases/latest) · [**Quick Start**](#-quick-start) · [**API Docs**](#-api-reference) · [**Export Formats**](#-export-formats)

</div>

---

## ✨ What it does

```
PDF / Website URL
       │
       ▼
┌─────────────────────────────────────────────┐
│         AI Skill Generator                  │
│                                             │
│  1. Extract text  →  chunk  →  embed        │
│  2. Store in PostgreSQL + pgvector          │
│  3. Export to any AI tool format            │
└─────────────────────────────────────────────┘
       │
       ▼
 .skill  │  AGENTS.md  │  .cursorrules  │  .json  │  …
```

| | Feature |
|---|---|
| 📄 | **PDF → Skill** — extract, chunk and embed any PDF |
| 🌐 | **Website → Skill** — full-site crawler with sitemap discovery |
| 🔍 | **RAG queries** — ask questions, get answers grounded in your docs |
| 📦 | **10 export formats** — one click for every major AI coding tool |
| 🖥️ | **CLI binary** — single executable, no Python install needed |
| 🔌 | **REST API** — plug into any pipeline or agent |

---

## 📦 Export formats

> One skill, every tool. Export once, use anywhere.

| Format | Works with | Output file |
|:---|:---|:---|
| 🟣 `.skill` | **Claude.ai** | `name.skill` — ZIP + SKILL.md |
| 🟢 `AGENTS.md` | **OpenCode · Codex** | `name-AGENTS.md` |
| 🔵 `.cursorrules` | **Cursor** | `name-.cursorrules` |
| ⚫ `copilot-instructions.md` | **GitHub Copilot** | `name-copilot-instructions.md` |
| 🌊 `.windsurfrules` | **Windsurf** | `name-.windsurfrules` |
| 🔴 `.clinerules` | **Cline** | `name-.clinerules` |
| 🟡 `CONVENTIONS.md` | **Aider** | `name-CONVENTIONS.md` |
| ⚪ `system-prompt.txt` | **Any LLM API** | `name-system-prompt.txt` |
| 📝 `.md` | **Universal** | `name.md` |
| 🗄️ `.json` | **Raw + embeddings** | `name.json` |

---

## 🚀 Quick start

### Option A — Docker (recommended)

```bash
git clone https://github.com/rahulroy0611/ai-skill-generator.git
cd ai-skill-generator
cp backend/.env.sample .env
# edit .env — add your DB password and LLM API key
docker compose up -d
```

Open **http://localhost** in your browser. Done.

> **Note:** The `.env` file must be at the project root (next to `docker-compose.yml`), not inside `backend/`.

### Option B — Manual

> **Requirements:** Python 3.11+ · Node.js 18+ · PostgreSQL 16+ with pgvector

```bash
# 1. Database — create and apply schema
psql -U postgres -c "CREATE DATABASE ai_skill_generator;"
psql -U postgres -d ai_skill_generator -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -d ai_skill_generator -f backend/database/schema.sql

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.sample .env                                # fill in your values
uvicorn app.main:app --reload --port 8000

# 3. Frontend  (new terminal)
cd frontend
npm install && npm run dev
```

---

## 🗄️ Database setup

> Docker handles this automatically. These steps are only needed for **manual installs**.

### Schema

The schema lives in [backend/database/schema.sql](backend/database/schema.sql). It creates two tables:

| Table | Purpose |
|:---|:---|
| `skills` | One row per skill — name, type, metadata, created_at |
| `skill_artifacts` | Chunked text + embedding vector per skill |

### Create the database manually

```bash
# Connect to PostgreSQL
psql -U postgres

# Inside psql:
CREATE DATABASE ai_skill_generator;
\c ai_skill_generator
CREATE EXTENSION IF NOT EXISTS vector;
\q

# Apply schema
psql -U postgres -d ai_skill_generator -f backend/database/schema.sql
```

### Windows (psql not in PATH)

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE ai_skill_generator;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d ai_skill_generator -c "CREATE EXTENSION IF NOT EXISTS vector;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d ai_skill_generator -f backend/database/schema.sql
```

> **Note:** pgvector must be installed on your PostgreSQL instance. With Docker (`pgvector/pgvector:pg16`) it is pre-installed.

---

## ⚙️ Configuration

Copy the sample and fill in your values:

```bash
cp backend/.env.sample .env
```

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/ai_skill_generator

# LLM — used for RAG answers (optional, get key at platform.minimax.ai)
LLM_API_KEY=
LLM_API_BASE=https://api.minimax.chat/v1

# Embedding model (default is fine for most use cases)
EMBED_MODEL_NAME=all-MiniLM-L6-v2
```

> **Docker vs manual:** When running via Docker the `DATABASE_URL` host is automatically overridden to use the `db` service name — you don't need to change it in `.env`.

> Without `LLM_API_KEY` the app still generates all skill files and embeddings. Only RAG query answers fall back to a stub.

### Docker with a custom password

```bash
# Pass POSTGRES_PASSWORD inline
POSTGRES_PASSWORD=mysecret docker compose up -d

# Or on PowerShell
$env:POSTGRES_PASSWORD="mysecret"; docker compose up -d
```

### Useful Docker commands

```bash
docker compose up -d          # start in background
docker compose logs -f        # stream logs
docker compose down           # stop
docker compose down -v        # stop + wipe database
```

---

## 🖥️ CLI tool

### Download

Grab the latest binary from [**GitHub Releases**](../../releases/latest) — no Python needed.

| Platform | Download |
|:---|:---|
| 🪟 Windows | `ai-skill-generator-windows-x64.exe` |
| 🐧 Linux | `ai-skill-generator-linux-x64` |

```bash
# Linux — one-time setup
chmod +x ai-skill-generator-linux-x64
mv ai-skill-generator-linux-x64 /usr/local/bin/ai-skill-generator
```

### Usage

```bash
# Convert a PDF
ai-skill-generator resume.pdf

# Crawl a full documentation site
ai-skill-generator https://docs.example.com/en/

# Custom output folder + description
ai-skill-generator report.pdf -o ./skills -d "Q4 security audit report"

# Limit crawl to 200 pages
ai-skill-generator https://hacktricks.wiki/en/ --max-pages 200
```

### Flags

| Flag | Description | Default |
|:---|:---|:---|
| `input` | PDF path or URL | required |
| `-o, --output` | Output directory | `./output` |
| `-d, --description` | Skill description | auto |
| `-m, --max-pages` | Max pages to crawl | unlimited |
| `-c, --max-chars` | Max characters | unlimited |

### Output structure

```
output/
├── 📦 MySkill.skill                       ← Claude.ai (ZIP + SKILL.md)
├── 📝 MySkill.md                          ← Universal markdown
├── 🗄️  MySkill.json                       ← Full data + embeddings
└── agent-exports/
    ├── MySkill-AGENTS.md                  ← OpenCode / Codex
    ├── MySkill-.cursorrules               ← Cursor
    ├── MySkill-copilot-instructions.md    ← GitHub Copilot
    ├── MySkill-.windsurfrules             ← Windsurf
    ├── MySkill-.clinerules                ← Cline
    ├── MySkill-CONVENTIONS.md             ← Aider
    └── MySkill-system-prompt.txt          ← Any LLM API
```

### Build from source

```bash
cd backend
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install pyinstaller pdfplumber sentence-transformers beautifulsoup4 lxml httpx numpy

# Linux
pyinstaller --onefile --console --strip --name ai-skill-generator cli.py

# Windows
pyinstaller --onefile --console --name ai-skill-generator cli.py
```

---

## 🤖 Using your skill files

<details>
<summary><b>Claude.ai</b></summary>

1. Go to **claude.ai → Skills → Upload skill**
2. Upload the `.skill` file

The `.skill` file is a ZIP archive containing `SKILL.md` with YAML frontmatter — the format Claude requires.

</details>

<details>
<summary><b>OpenCode / Codex</b></summary>

```bash
# Project-level
cp "MySkill-AGENTS.md" your-project/AGENTS.md

# Global (applies to all projects)
cp "MySkill-AGENTS.md" ~/.config/opencode/AGENTS.md
```

</details>

<details>
<summary><b>Cursor</b></summary>

```bash
cp "MySkill-.cursorrules" your-project/.cursorrules
```

</details>

<details>
<summary><b>GitHub Copilot</b></summary>

```bash
mkdir -p .github
cp "MySkill-copilot-instructions.md" .github/copilot-instructions.md
```

</details>

<details>
<summary><b>Windsurf</b></summary>

```bash
cp "MySkill-.windsurfrules" your-project/.windsurfrules
```

</details>

<details>
<summary><b>Cline</b></summary>

```bash
cp "MySkill-.clinerules" your-project/.clinerules
```

</details>

<details>
<summary><b>Aider</b></summary>

```bash
aider --read MySkill-CONVENTIONS.md
```

</details>

<details>
<summary><b>Any LLM API</b></summary>

Pass `system-prompt.txt` contents as your system prompt.

```python
with open("MySkill-system-prompt.txt") as f:
    system_prompt = f.read()
```

</details>

---

## 🔌 API reference

> Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/upload` | Upload a PDF |
| `POST` | `/upload-website` | Crawl a URL |
| `GET` | `/skills` | List all skills |
| `POST` | `/skills/{id}/query` | RAG query |
| `GET` | `/skills/{id}/download` | Download `.skill` / `.md` / `.json` |
| `GET` | `/skills/{id}/export?agent=` | Export for AI agent |
| `DELETE` | `/skills/{id}` | Delete a skill |
| `GET` | `/crawl-progress` | Live crawl status |
| `GET` | `/health` | Health check |

**Agent values:** `opencode` · `codex` · `cursor` · `copilot` · `windsurf` · `cline` · `aider` · `systemprompt`

#### Query example

```bash
curl -X POST http://localhost:8000/skills/1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main security controls?"}'
```

#### Export example

```bash
curl "http://localhost:8000/skills/1/export?agent=cursor" -o .cursorrules
```

---

## 🏗️ Tech stack

<div align="center">

| Layer | Tech |
|:---|:---|
| Backend | FastAPI · Python 3.11 · Uvicorn |
| Database | PostgreSQL 16 · pgvector |
| Embeddings | sentence-transformers · all-MiniLM-L6-v2 |
| LLM | MiniMax API (swappable via env) |
| Crawler | httpx · BeautifulSoup · sitemap.xml |
| Frontend | React 18 · Vite · Tailwind CSS |
| CLI | PyInstaller standalone binary |
| CI/CD | GitHub Actions |
| Infra | Docker · Docker Compose |

</div>

---

## 📬 Releases

Binaries are built and attached to every GitHub Release automatically via [GitHub Actions](.github/workflows/build-cli.yml).

```bash
git tag v1.0.0
git push origin v1.0.0
# Create a Release on GitHub → binaries attach automatically
```

---

<div align="center">

Made with ❤️ by [Rahul Roy](https://github.com/rahulroy0611)

</div>
