import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="PDF to Skill API", lifespan=lifespan)

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
        website_extractor = WebsiteExtractor()
        text = website_extractor.extract_text(request.url)
        
        if not text or len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract enough content from the website")
        
        title = website_extractor.get_title(request.url) or "website_skill"
        filename = f"{title}.txt"
        
        result = await skill_builder.build_skill(text.encode('utf-8'), filename, is_text=True)
        
        return UploadResponse(
            skill_id=result["skill_id"],
            name=result["name"],
            status=result["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process website: {str(e)}")


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
async def download_skill(skill_id: int, format: str = "skill"):
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
                detail="This PDF has no extractable text. It may be a scanned image. Please use a PDF with selectable text."
            )
        
        if format == "skill":
            skill_content = f"""SKILL METADATA
================
name: {skill.name}
type: {skill.skill_type}
created: {skill.created_at.isoformat() if skill.created_at else 'N/A'}
id: {skill.id}

SKILL DESCRIPTION
================
{json.dumps(skill.skill_metadata, indent=2)}

KNOWLEDGE BASE (with embeddings)
=============
"""
            for i, a in enumerate(artifacts):
                if a.content and a.content.strip():
                    emb_str = json.dumps(a.embedding) if a.embedding else "[]"
                    skill_content += f"""
---
CHUNK #{i+1}
EMBEDDING: {emb_str}
---
{a.content}
"""
            
            skill_content += """

===========================================
END OF SKILL
===========================================
This skill contains text chunks and their vector embeddings.
Use embeddings for semantic similarity search.
"""
            
            file_path = f"skill_{skill_id}.skill"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(skill_content)
            
            return FileResponse(
                file_path,
                media_type="text/plain",
                filename=f"{skill.name}.skill"
            )
        
        elif format == "md":
            md_content = f"# {skill.name}\n\nType: {skill.skill_type}\nCreated: {skill.created_at.isoformat() if skill.created_at else 'N/A'}\n\n---\n\n" + "\n\n---\n\n".join(all_content)
            
            file_path = f"skill_{skill_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            return FileResponse(
                file_path,
                media_type="text/plain",
                filename=f"{skill.name}.md"
            )
        
        # JSON format
        skill_data = {
            "id": skill.id,
            "name": skill.name,
            "skill_type": skill.skill_type,
            "metadata": skill.skill_metadata,
            "created_at": skill.created_at.isoformat() if skill.created_at else None,
            "artifacts": [
                {"chunk_index": a.chunk_index, "content": a.content, "embedding": a.embedding}
                for a in artifacts
            ]
        }
        
        file_path = f"skill_{skill_id}.json"
        with open(file_path, "w") as f:
            json.dump(skill_data, f, indent=2)
        
        return FileResponse(
            file_path,
            media_type="application/json",
            filename=f"{skill.name}.skill.json"
        )


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


@app.get("/")
async def root():
    return {"message": "PDF to Skill API is running"}


@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}