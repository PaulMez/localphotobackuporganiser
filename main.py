import os
import sqlite3
import hashlib
from pathlib import Path
from PIL import Image
import filetype

db_path = "file_metadata.db"

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

def scan_directory(directory):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            size = os.path.getsize(file_path)
            file_hash = get_file_hash(file_path)
            mime = get_file_mime(file_path)
            
            try:
                c.execute("INSERT OR IGNORE INTO files (name, size, path, hash, mime) VALUES (?, ?, ?, ?, ?)",
                          (file, size, file_path, file_hash, mime))
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
    base_directory = input("Enter the directory to scan: ")
    base_directory = Path(base_directory).resolve()
    create_db()
    scan_directory(base_directory)
    find_duplicates()
    find_near_duplicates()
