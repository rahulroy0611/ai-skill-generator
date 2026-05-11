-- PDF to Skill Database Schema

-- Create database first
-- CREATE DATABASE pdftoskill;

-- Skills table
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    skill_type VARCHAR(50) NOT NULL,
    skill_metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skill artifacts table (chunks with embeddings)
CREATE TABLE IF NOT EXISTS skill_artifacts (
    id SERIAL PRIMARY KEY,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding DOUBLE PRECISION[]
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_artifacts_skill_id ON skill_artifacts(skill_id);

-- Enable vector extension (optional for pgvector)
-- CREATE EXTENSION IF NOT EXISTS vector;