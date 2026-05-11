import json
import os
import tempfile
import zipfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text, delete
from pydantic import BaseModel
from typing import Optional


class WebsiteInput(BaseModel):
    url: str

from app.database import engine, Base, AsyncSessionLocal, Skill, SkillArtifact, init_db
from app.database import SkillResponse, UploadResponse, QueryResponse
from app.services import PDFExtractor, LLMClient, EmbeddingService, SkillBuilder, SkillQueryService
from app.website_extractor import WebsiteExtractor


pdf_extractor = PDFExtractor()
llm_client = LLMClient()
embedding_service = EmbeddingService()
skill_builder = SkillBuilder(pdf_extractor, llm_client, embedding_service)
skill_query_service = SkillQueryService(embedding_service, llm_client)


class SkillQuery(BaseModel):
    query: str


crawl_progress = {"fetched": 0, "visited": 0, "in_progress": False}


def progress_callback(fetched: int, visited: int):
    crawl_progress["fetched"] = fetched
    crawl_progress["visited"] = visited


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="AI Skill Generator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_bytes = await file.read()
    result = await skill_builder.build_skill(file_bytes, file.filename)

    return UploadResponse(
        skill_id=result["skill_id"],
        name=result["name"],
        status=result["status"],
    )


@app.post("/upload-website", response_model=UploadResponse)
async def upload_website(request: WebsiteInput):
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL. Must start with http:// or https://")
    
    try:
        crawl_progress["in_progress"] = True
        crawl_progress["fetched"] = 0
        crawl_progress["visited"] = 0
        
        extractor = WebsiteExtractor(max_pages=None, max_chars=None)
        text, title = await extractor.crawl_async(request.url, progress_callback=progress_callback)
        
        if not text or len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract enough content from the website")
        
        # Use crawl-returned title directly — avoids a redundant HTTP refetch
        safe_title = title.replace("/", "_").replace("\\", "_") if title else "website"
        filename = f"{safe_title}.txt"

        result = await skill_builder.build_skill(text.encode('utf-8'), filename, is_text=True)

        crawl_progress["in_progress"] = False
        
        return UploadResponse(
            skill_id=result["skill_id"],
            name=result["name"],
            status=result["status"],
        )
    except ValueError as e:
        crawl_progress["in_progress"] = False
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        crawl_progress["in_progress"] = False
        raise HTTPException(status_code=500, detail=f"Failed to process website: {str(e)}")


@app.get("/crawl-progress")
async def get_crawl_progress():
    return crawl_progress


@app.get("/skills", response_model=list[SkillResponse])
async def list_skills():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Skill))
        skills = result.scalars().all()
        return [
            SkillResponse(
                id=s.id,
                name=s.name,
                skill_type=s.skill_type,
                metadata=s.skill_metadata,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in skills
        ]


@app.post("/skills/{skill_id}/query", response_model=QueryResponse)
async def query_skill(skill_id: int, request: SkillQuery):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

    result = await skill_query_service.query_skill(skill_id, request.query)
    return QueryResponse(answer=result["answer"], sources=result.get("sources"))


@app.get("/skills/{skill_id}/download")
async def download_skill(skill_id: int, background_tasks: BackgroundTasks, format: str = "skill"):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        artifacts_result = await db.execute(
            select(SkillArtifact).where(SkillArtifact.skill_id == skill_id)
        )
        artifacts = artifacts_result.scalars().all()

        all_content = [a.content.strip() for a in artifacts if a.content and a.content.strip()]

        if not all_content:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No content found for this skill. "
                    "If it is a scanned PDF it may have no selectable text. "
                    "If it is a tool/workflow skill, content chunks are not stored."
                )
            )

        suffix_map = {"skill": ".skill", "md": ".md", "json": ".json"}
        suffix = suffix_map.get(format, ".skill")

        if format == "skill":
            # Claude requires .skill to be a ZIP archive containing SKILL.md with YAML frontmatter
            description = skill.skill_metadata.get("description", "") if skill.skill_metadata else ""
            knowledge_base = "\n\n---\n\n".join(all_content)
            skill_md = f"""---
name: {skill.name}
description: {description}
---

{knowledge_base}
"""
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".skill")
            tmp.close()
            background_tasks.add_task(os.remove, tmp.name)
            with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("SKILL.md", skill_md)
            return FileResponse(tmp.name, media_type="application/zip", filename=f"{skill.name}.skill")

        elif format == "md":
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8")
            background_tasks.add_task(os.remove, tmp.name)
            tmp.write(
                f"# {skill.name}\n\nType: {skill.skill_type}\n"
                f"Created: {skill.created_at.isoformat() if skill.created_at else 'N/A'}\n\n---\n\n"
                + "\n\n---\n\n".join(all_content)
            )
            tmp.close()
            return FileResponse(tmp.name, media_type="text/plain", filename=f"{skill.name}.md")

        # JSON format
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
        background_tasks.add_task(os.remove, tmp.name)
        skill_data = {
            "id": skill.id,
            "name": skill.name,
            "skill_type": skill.skill_type,
            "metadata": skill.skill_metadata,
            "created_at": skill.created_at.isoformat() if skill.created_at else None,
            "artifacts": [
                {"chunk_index": a.chunk_index, "content": a.content, "embedding": a.embedding}
                for a in artifacts
            ],
        }
        json.dump(skill_data, tmp)
        tmp.close()
        return FileResponse(tmp.name, media_type="application/json", filename=f"{skill.name}.skill.json")


@app.delete("/skills/{skill_id}")
async def delete_skill(skill_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        await db.execute(
            delete(SkillArtifact).where(SkillArtifact.skill_id == skill_id)
        )
        
        await db.delete(skill)
        await db.commit()
        
        return {"message": f"Skill '{skill.name}' deleted successfully"}


AGENT_EXPORT_CONFIGS = {
    "opencode":  {"filename": "AGENTS.md",                 "media_type": "text/plain"},
    "codex":     {"filename": "AGENTS.md",                 "media_type": "text/plain"},
    "cursor":    {"filename": ".cursorrules",              "media_type": "text/plain"},
    "copilot":   {"filename": "copilot-instructions.md",   "media_type": "text/plain"},
    "windsurf":  {"filename": ".windsurfrules",            "media_type": "text/plain"},
    "cline":     {"filename": ".clinerules",               "media_type": "text/plain"},
    "aider":     {"filename": "CONVENTIONS.md",            "media_type": "text/plain"},
    "systemprompt": {"filename": "system-prompt.txt",      "media_type": "text/plain"},
}


@app.get("/skills/{skill_id}/export")
async def export_skill(skill_id: int, background_tasks: BackgroundTasks, agent: str = "opencode"):
    agent = agent.lower()
    if agent not in AGENT_EXPORT_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent '{agent}'. Supported: {', '.join(AGENT_EXPORT_CONFIGS)}"
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        artifacts_result = await db.execute(
            select(SkillArtifact).where(SkillArtifact.skill_id == skill_id)
        )
        artifacts = artifacts_result.scalars().all()

    all_content = [a.content.strip() for a in artifacts if a.content and a.content.strip()]
    if not all_content:
        raise HTTPException(status_code=400, detail="No content found in this skill.")

    description = (skill.skill_metadata or {}).get("description", "AI-generated knowledge base skill.")
    knowledge = "\n\n---\n\n".join(all_content)
    config = AGENT_EXPORT_CONFIGS[agent]

    if agent == "systemprompt":
        content = (
            f"You have access to the following knowledge base: {skill.name}\n\n"
            f"{description}\n\n"
            f"Use the information below to answer questions accurately.\n\n"
            f"{'=' * 60}\n\n"
            f"{knowledge}"
        )
    else:
        content = (
            f"# {skill.name}\n\n"
            f"> {description}\n\n"
            f"## Instructions\n\n"
            f"You have access to the following knowledge base. "
            f"Use it to answer questions, assist with tasks, and provide accurate information "
            f"related to this topic. Always ground your responses in this content.\n\n"
            f"## Knowledge Base\n\n"
            f"{knowledge}\n"
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8")
    background_tasks.add_task(os.remove, tmp.name)
    tmp.write(content)
    tmp.close()

    download_name = f"{skill.name}-{config['filename']}"
    return FileResponse(tmp.name, media_type=config["media_type"], filename=download_name)


@app.get("/")
async def root():
    return {"message": "AI Skill Generator API is running"}


@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}