import os
import sqlite3
import hashlib
from pathlib import Path
from PIL import Image
import filetype

db_path = "photo_metadata.db"
STARTING_FOLDER = "D:/picsbackup/"  # Set your default folder here

def create_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    size INTEGER,
                    path TEXT UNIQUE,
                    hash TEXT,
                    mime TEXT
                )''')
    conn.commit()
    conn.close()

def get_file_hash(file_path):
    """Returns the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None

def get_file_mime(file_path):
    """Returns the MIME type of a file."""
    kind = filetype.guess(file_path)
    return kind.mime if kind else "unknown"

def scan_directory(directory, file_limit=0):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    files_processed = 0
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            size = os.path.getsize(file_path)
            file_hash = get_file_hash(file_path)
            mime = get_file_mime(file_path)
            
            try:
                c.execute("INSERT OR IGNORE INTO files (name, size, path, hash, mime) VALUES (?, ?, ?, ?, ?)",
                          (file, size, file_path, file_hash, mime))
                files_processed += 1
                if file_limit and files_processed >= file_limit:
                    print(f"Reached file limit of {file_limit}")
                    conn.commit()
                    conn.close()
                    return
            except Exception as e:
                print(f"DB Error: {e}")
    
    conn.commit()
    conn.close()

def find_duplicates():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("\nDuplicate File Names:")
    c.execute("SELECT name, COUNT(*) FROM files GROUP BY name HAVING COUNT(*) > 1")
    for row in c.fetchall():
        print(row)
    
    print("\nDuplicate File Names with Same Size:")
    c.execute("SELECT name, size, COUNT(*) FROM files GROUP BY name, size HAVING COUNT(*) > 1")
    for row in c.fetchall():
        print(row)
    
    print("\nDuplicate File Hashes (Exact Duplicates):")
    c.execute("SELECT hash, COUNT(*) FROM files WHERE hash IS NOT NULL GROUP BY hash HAVING COUNT(*) > 1")
    for row in c.fetchall():
        print(row)
    
    conn.close()

def find_near_duplicates():
    """Finds images and videos with the same content but different metadata."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("\nPotential Near Duplicates (Same Content, Different Metadata):")
    c.execute("SELECT name, size, mime, hash, COUNT(*) FROM files WHERE mime LIKE 'image/%' OR mime LIKE 'video/%' GROUP BY hash HAVING COUNT(*) > 1")
    for row in c.fetchall():
        print(row)
    
    conn.close()

if __name__ == "__main__":
    user_input = input(f"Enter the directory to scan (Press Enter to use default: {STARTING_FOLDER}): ")
    base_directory = Path(user_input.strip() or STARTING_FOLDER).resolve()
    create_db()
    scan_directory(base_directory, file_limit=10)  # Set to 10 for testing
    find_duplicates()
    find_near_duplicates()
