"""
Database migration management script
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main migration function"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <command>")
        print("Commands:")
        print("  init     - Initialize Alembic")
        print("  create   - Create a new migration")
        print("  upgrade  - Apply all pending migrations")
        print("  downgrade - Rollback last migration")
        print("  current  - Show current migration")
        print("  history  - Show migration history")
        return
    
    command = sys.argv[1]
    
    if command == "init":
        run_command("alembic init migrations", "Initializing Alembic")
        
    elif command == "create":
        if len(sys.argv) < 3:
            print("Usage: python scripts/migrate.py create <migration_name>")
            return
        migration_name = sys.argv[2]
        run_command(f"alembic revision --autogenerate -m '{migration_name}'", f"Creating migration: {migration_name}")
        
    elif command == "upgrade":
        run_command("alembic upgrade head", "Applying migrations")
        
    elif command == "downgrade":
        run_command("alembic downgrade -1", "Rolling back last migration")
        
    elif command == "current":
        run_command("alembic current", "Showing current migration")
        
    elif command == "history":
        run_command("alembic history", "Showing migration history")
        
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main() 