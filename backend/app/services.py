import os
import re
import json
import tempfile
from typing import Any, Optional

import pdfplumber
import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

from app.database import AsyncSessionLocal, Skill, SkillArtifact, engine, Base


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_skill_generator")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.minimax.chat/v1")
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")


class PDFExtractor:
    @staticmethod
    def extract_text(file_bytes: bytes) -> str:
        text = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        return text

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks


class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or LLM_API_KEY
        self.base_url = LLM_API_BASE

    def analyze_pdf(self, text: str) -> dict[str, Any]:
        prompt = f"""Analyze the following PDF content and create a skill blueprint.
Determine if this is a RAG skill (knowledge base), a TOOL skill (API/function), or WORKFLOW skill.
Output a JSON with:
- skill_type: "rag" | "tool" | "workflow"
- skill_name: a short descriptive name
- description: what the skill does
- metadata: any additional info

PDF Content (first 3000 chars):
{text[:3000]}

Output ONLY valid JSON, no other text:"""

        if not self.api_key:
            return {
                "skill_type": "rag",
                "skill_name": "uploaded_knowledge",
                "description": "Knowledge base extracted from PDF",
                "metadata": {"source": "pdf_upload"},
            }

        try:
            response = httpx.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "abab6.5s-chat",
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return {
                "skill_type": "rag",
                "skill_name": "uploaded_knowledge",
                "description": "Knowledge base extracted from PDF",
                "metadata": {"source": "pdf_upload"},
            }

    def generate_answer(self, context: str, query: str) -> str:
        if not self.api_key:
            return f"Based on the context: {context[:200]}..."

        prompt = f"""Based on the following context, answer the user's question.

Context:
{context}

Question: {query}

Answer:"""

        try:
            response = httpx.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "abab6.5s-chat",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30,
            )
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            return f"Based on the context: {context[:200]}..."
        except Exception as e:
            return f"Based on the context: {context[:200]}..."


class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(EMBED_MODEL_NAME)

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


class SkillBuilder:
    def __init__(
        self,
        pdf_extractor: PDFExtractor,
        llm_client: LLMClient,
        embedding_service: EmbeddingService,
    ):
        self.pdf_extractor = pdf_extractor
        self.llm_client = llm_client
        self.embedding_service = embedding_service

    async def build_skill(self, file_bytes: bytes, filename: str, is_text: bool = False) -> dict[str, Any]:
        if is_text:
            text = file_bytes.decode('utf-8', errors='ignore')
        else:
            text = self.pdf_extractor.extract_text(file_bytes)
        
        blueprint = self.llm_client.analyze_pdf(text)

        async with AsyncSessionLocal() as db:
            skill = Skill(
                name=filename.replace(".pdf", "") or blueprint.get("skill_name", "skill"),
                skill_type=blueprint.get("skill_type", "rag"),
                skill_metadata={
                    "description": blueprint.get("description", ""),
                    **blueprint.get("metadata", {}),
                },
            )
            db.add(skill)
            await db.commit()
            await db.refresh(skill)

            if blueprint.get("skill_type") == "rag":
                chunks = self.pdf_extractor.chunk_text(text)
                embeddings = self.embedding_service.get_embeddings(chunks)

                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    artifact = SkillArtifact(
                        skill_id=skill.id,
                        chunk_index=i,
                        content=chunk,
                        embedding=embedding,
                    )
                    db.add(artifact)
                await db.commit()

            return {"skill_id": skill.id, "name": skill.name, "status": "completed"}


class SkillQueryService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        llm_client: LLMClient,
    ):
        self.embedding_service = embedding_service
        self.llm_client = llm_client

    async def query_skill(self, skill_id: int, query: str) -> dict[str, Any]:
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(select(SkillArtifact).where(SkillArtifact.skill_id == skill_id))
                artifacts = result.scalars().all()

                if not artifacts:
                    return {"answer": "No content found in this skill.", "sources": []}

                query_embedding = self.embedding_service.get_embeddings([query])[0]

                similarities = []
                for artifact in artifacts:
                    emb = artifact.embedding
                    if emb:
                        emb_arr = np.array(emb, dtype=np.float64)
                        sim = float(np.dot(query_embedding, emb_arr))
                        similarities.append((sim, artifact.content))

                if not similarities:
                    return {"answer": "No embeddings found in this skill.", "sources": []}

                similarities.sort(key=lambda x: x[0], reverse=True)
                
                top_chunks = [s[1] for s in similarities[:5] if s[1] and len(s[1].strip()) > 0]
                context = "\n\n".join(top_chunks)
                
                if not context:
                    return {"answer": "This skill has no readable content. The PDF may have only images or be password protected.", "sources": []}

                answer = self.llm_client.generate_answer(context, query)
                return {"answer": answer, "sources": top_chunks[:3]}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"answer": f"Error querying skill: {str(e)}", "sources": []}
        except Exception as e:
            return {"answer": f"Error querying skill: {str(e)}", "sources": []}