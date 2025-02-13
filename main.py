import os
import sqlite3
import hashlib
from pathlib import Path
#from PIL import Image
import filetype

db_path = "photo_metadata.db"
# WSL path to Windows D: drive
STARTING_FOLDER = "/mnt/d/picsbackup"

def create_db():
    print("Creating/connecting to database...")
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
    print("Database setup complete.")

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
    print(f"\nStarting directory scan of: {directory}")
    print(f"File limit set to: {file_limit if file_limit else 'No limit'}")
    print("Beginning directory walk...")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    files_processed = 0
    for root, dirs, files in os.walk(directory):
        print(f"Scanning directory: {root}")
        print(f"Found {len(files)} files in this directory")
        
        for file in files:
            file_path = os.path.join(root, file)
            print(f"\nProcessing file {files_processed + 1}: {file}")
            
            try:
                size = os.path.getsize(file_path)
                print(f"File size: {size} bytes")
                
                print("Calculating file hash...")
                file_hash = get_file_hash(file_path)
                
                print("Detecting MIME type...")
                mime = get_file_mime(file_path)
                print(f"MIME type: {mime}")
                
                c.execute("INSERT OR IGNORE INTO files (name, size, path, hash, mime) VALUES (?, ?, ?, ?, ?)",
                          (file, size, file_path, file_hash, mime))
                files_processed += 1
                if file_limit and files_processed >= file_limit:
                    print(f"\nReached file limit of {file_limit}")
                    conn.commit()
                    conn.close()
                    return
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
    
    conn.commit()
    conn.close()
    print(f"\nScan complete. Processed {files_processed} files.")

def find_duplicates():
    print("\n=== Searching for Duplicates ===")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("\nChecking for duplicate file names...")
    c.execute("SELECT name, COUNT(*) FROM files GROUP BY name HAVING COUNT(*) > 1")
    results = c.fetchall()
    if results:
        print("Found duplicate file names:")
        for row in results:
            print(f"- {row[0]} (appears {row[1]} times)")
    else:
        print("No duplicate file names found.")
    
    print("\nChecking for files with same name and size...")
    c.execute("SELECT name, size, COUNT(*) FROM files GROUP BY name, size HAVING COUNT(*) > 1")
    results = c.fetchall()
    if results:
        print("Found files with same name and size:")
        for row in results:
            print(f"- {row[0]} (size: {row[1]} bytes, appears {row[2]} times)")
    else:
        print("No files with same name and size found.")
    
    print("\nChecking for exact duplicates (same hash)...")
    c.execute("SELECT hash, COUNT(*) FROM files WHERE hash IS NOT NULL GROUP BY hash HAVING COUNT(*) > 1")
    results = c.fetchall()
    if results:
        print("Found exact duplicates:")
        for row in results:
            print(f"- Hash: {row[0]} (appears {row[1]} times)")
    else:
        print("No exact duplicates found.")
    
    conn.close()

def find_near_duplicates():
    print("\n=== Searching for Near Duplicates ===")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("Checking for media files with same content but different metadata...")
    c.execute("SELECT name, size, mime, hash, COUNT(*) FROM files WHERE mime LIKE 'image/%' OR mime LIKE 'video/%' GROUP BY hash HAVING COUNT(*) > 1")
    results = c.fetchall()
    if results:
        print("Found potential near duplicates:")
        for row in results:
            print(f"- {row[0]} ({row[2]}, size: {row[1]} bytes, appears {row[4]} times)")
    else:
        print("No near duplicates found.")
    
    conn.close()

if __name__ == "__main__":
    print("=== Photo Metadata Scanner ===")
    print("Script starting...")
    base_directory = Path(STARTING_FOLDER)
    print(f"Using directory: {base_directory}")
    
    if not base_directory.exists():
        print(f"ERROR: Directory does not exist: {base_directory}")
        exit(1)
    if not base_directory.is_dir():
        print(f"ERROR: Path exists but is not a directory: {base_directory}")
        exit(1)
        
    create_db()
    scan_directory(base_directory, file_limit=10)
    find_duplicates()
    find_near_duplicates()
    
    print("\nProcess complete!")
