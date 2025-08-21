-- Test database initialization script
-- Create extensions and initial schema for testing

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for password hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create test schema
CREATE SCHEMA IF NOT EXISTS test_schema;

-- Grant permissions
GRANT ALL ON SCHEMA test_schema TO testuser;
GRANT ALL ON SCHEMA public TO testuser;

-- Create initial test tables if needed
-- These will be overridden by SQLAlchemy migrations during tests
-- but provide a baseline structure

-- Test organization table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Test user table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Test categories table
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Test knowledge items table
CREATE TABLE IF NOT EXISTS knowledge_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    is_published BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better test performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_category ON knowledge_items(category_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_author ON knowledge_items(author_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_tags ON knowledge_items USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_metadata ON knowledge_items USING GIN(metadata);

-- Insert test data
INSERT INTO organizations (id, name, description) VALUES 
    ('00000000-0000-0000-0000-000000000001', 'Test Organization', 'Organization for testing')
ON CONFLICT DO NOTHING;

INSERT INTO users (id, email, username, password_hash, is_active, is_superuser, organization_id) VALUES 
    ('00000000-0000-0000-0000-000000000002', 'test@example.com', 'testuser', crypt('testpass123', gen_salt('bf')), true, false, '00000000-0000-0000-0000-000000000001'),
    ('00000000-0000-0000-0000-000000000003', 'admin@example.com', 'adminuser', crypt('adminpass123', gen_salt('bf')), true, true, '00000000-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;