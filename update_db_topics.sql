-- Add topic_id column to conversations table
ALTER TABLE conversations ADD COLUMN topic_id BIGINT;
CREATE INDEX idx_conversations_topic ON conversations(topic_id);
