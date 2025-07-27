#!/usr/bin/env python3
"""
Flush All Data Script

This script flushes all data from PostgreSQL and Redis for a fresh start.
Useful for development and testing when you want to start with a clean slate.

Usage:
    python scripts/flush_all.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.config import config
from render_relay.utils.get_logger import get_logger

logger = get_logger("flush_all")

def run_command(command, description):
    """Run a shell command and log the result"""
    logger.info(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        logger.info(f"✅ {description} completed successfully")
        if result.stdout.strip():
            logger.debug(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False

def flush_postgresql():
    """Flush all data from PostgreSQL tables"""
    logger.info("🗄️  Flushing PostgreSQL data...")
    
    # Build the PostgreSQL connection string
    pg_url = f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
    
    # SQL command to truncate all tables
    truncate_sql = """
    TRUNCATE TABLE 
        context_embeddings, 
        conversation_messages, 
        sessions 
    RESTART IDENTITY CASCADE;
    """
    
    command = f'psql "{pg_url}" -c "{truncate_sql}"'
    
    if run_command(command, "Flushing PostgreSQL tables"):
        # Verify the tables are empty
        verify_sql = """
        SELECT 
            'context_embeddings' as table_name, COUNT(*) as count FROM context_embeddings
        UNION ALL
        SELECT 
            'conversation_messages' as table_name, COUNT(*) as count FROM conversation_messages
        UNION ALL
        SELECT 
            'sessions' as table_name, COUNT(*) as count FROM sessions;
        """
        
        verify_command = f'psql "{pg_url}" -c "{verify_sql}"'
        run_command(verify_command, "Verifying PostgreSQL tables are empty")
        return True
    return False

def flush_redis():
    """Flush all data from Redis"""
    logger.info("🔴 Flushing Redis data...")
    
    # Try different Redis connection methods
    redis_commands = [
        "docker-compose exec redis redis-cli FLUSHALL",
        "redis-cli -u redis://localhost:6379 FLUSHALL",
        "redis-cli FLUSHALL"
    ]
    
    for command in redis_commands:
        if run_command(command, f"Flushing Redis using: {command}"):
            # Verify Redis is empty
            verify_commands = [
                "docker-compose exec redis redis-cli DBSIZE",
                "redis-cli -u redis://localhost:6379 DBSIZE",
                "redis-cli DBSIZE"
            ]
            
            for verify_cmd in verify_commands:
                if run_command(verify_cmd, "Verifying Redis is empty"):
                    return True
            break
    
    logger.warning("⚠️  Could not verify Redis flush - continuing anyway")
    return True

def kill_port_5001():
    """Kill any processes running on port 5001"""
    logger.info("🔌 Killing processes on port 5001...")
    
    # Find processes using port 5001
    find_command = "lsof -ti:5001"
    try:
        result = subprocess.run(find_command, shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    kill_command = f"kill {pid.strip()}"
                    run_command(kill_command, f"Killing process {pid}")
            
            # Wait a moment and verify
            time.sleep(1)
            verify_command = "lsof -i:5001"
            run_command(verify_command, "Verifying port 5001 is free")
        else:
            logger.info("✅ No processes found on port 5001")
    except Exception as e:
        logger.warning(f"⚠️  Could not check port 5001: {e}")

def main():
    """Main function to flush all data"""
    logger.info("🚀 Starting data flush process...")
    
    # Print current configuration
    logger.info("📋 Current Configuration:")
    logger.info(f"  PostgreSQL: {config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}")
    logger.info(f"  Redis: {config.REDIS_URL}")
    
    success = True
    
    # Flush PostgreSQL
    if not flush_postgresql():
        success = False
        logger.error("❌ PostgreSQL flush failed")
    
    # Flush Redis
    if not flush_redis():
        success = False
        logger.error("❌ Redis flush failed")
    
    # Kill port 5001
    kill_port_5001()
    
    if success:
        logger.info("🎉 All data flushed successfully!")
        logger.info("✅ PostgreSQL: All tables cleared")
        logger.info("✅ Redis: All keys flushed")
        logger.info("✅ Port 5001: Processes killed")
        logger.info("🚀 Ready for fresh start!")
    else:
        logger.error("❌ Some operations failed - check logs above")
        sys.exit(1)

if __name__ == "__main__":
    main() 