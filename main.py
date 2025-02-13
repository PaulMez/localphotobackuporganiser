import os
import sqlite3
import hashlib
from pathlib import Path
#from PIL import Image
import filetype
from datetime import datetime
import logging
from exif import Image  # Add this for image metadata

# Configure logging
def setup_logging(log_level=logging.INFO):
    # Create logger
    logger = logging.getLogger('photo_scanner')
    logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatters and add them to the handlers
    format_str = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(format_str, date_format)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    return logger

# Initialize logger
logger = setup_logging()

db_path = "photo_metadata_all.db"
# WSL path to Windows D: drive
STARTING_FOLDER = "/mnt/d/picsbackup"
ACCEPTED_MIMES = ['image/', 'video/']  # Only process files starting with these MIME types

def create_db(clear_existing=True):
    """Create or recreate the database."""
    logger.info("Creating/connecting to database...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    if clear_existing:
        logger.info("Clearing existing database...")
        c.execute('DROP TABLE IF EXISTS files')
    
    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    size INTEGER,
                    path TEXT UNIQUE,
                    hash TEXT,
                    mime TEXT,
                    added_timestamp TEXT,
                    file_created_date TEXT,
                    file_modified_date TEXT,
                    photo_taken_date TEXT
                )''')
    conn.commit()
    conn.close()
    logger.info("Database setup complete.")

def get_file_hash(file_path):
    """Returns the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing {file_path}: {e}")
        return None

def get_file_mime(file_path):
    """Returns the MIME type of a file."""
    kind = filetype.guess(file_path)
    return kind.mime if kind else "unknown"

def is_media_file(mime_type):
    """Check if the file is an image or video based on MIME type."""
    return any(mime_type.startswith(accepted) for accepted in ACCEPTED_MIMES)

def get_file_dates(file_path):
    """Get file creation and modification dates."""
    stats = os.stat(file_path)
    created = datetime.fromtimestamp(stats.st_ctime).isoformat()
    modified = datetime.fromtimestamp(stats.st_mtime).isoformat()
    return created, modified

def get_photo_taken_date(file_path, mime_type):
    """Attempt to get the date the photo was taken."""
    try:
        if mime_type.startswith('image/'):
            with open(file_path, 'rb') as image_file:
                image = Image(image_file)
                if hasattr(image, 'datetime_original'):
                    return image.datetime_original
    except Exception as e:
        logger.debug(f"Could not extract photo taken date from {file_path}: {e}")
    return None

def scan_directory(directory, file_limit=0, clear_db=True):
    logger.info(f"\nStarting directory scan of: {directory}")
    logger.info(f"File limit set to: {file_limit if file_limit else 'No limit'}")
    
    create_db(clear_existing=clear_db)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Statistics tracking
    stats = {
        'total_files_found': 0,
        'files_processed': 0,
        'media_files_added': 0,
        'files_skipped': 0,
        'errors': 0
    }
    
    for root, dirs, files in os.walk(directory):
        if file_limit and stats['media_files_added'] >= file_limit:
            logger.info(f"\nReached media file limit of {file_limit}")
            break
            
        logger.info(f"Progress: Scanning directory: {root}")
        logger.debug(f"Found {len(files)} files in current directory")
        stats['total_files_found'] += len(files)
        
        for file in files:
            if file_limit and stats['media_files_added'] >= file_limit:
                break
                
            file_path = os.path.join(root, file)
            logger.debug(f"Processing: {file}")
            
            try:
                # Check MIME type first
                mime = get_file_mime(file_path)
                if not is_media_file(mime):
                    logger.debug(f"Skipping non-media file: {file} (MIME: {mime})")
                    stats['files_skipped'] += 1
                    continue
                
                logger.debug(f"Processing media file {stats['media_files_added'] + 1}: {file}")
                size = os.path.getsize(file_path)
                file_hash = get_file_hash(file_path)
                
                # Get various dates
                created_date, modified_date = get_file_dates(file_path)
                taken_date = get_photo_taken_date(file_path, mime)
                timestamp = datetime.now().isoformat()
                
                c.execute("""
                    INSERT OR REPLACE INTO files 
                    (name, size, path, hash, mime, added_timestamp, 
                     file_created_date, file_modified_date, photo_taken_date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (file, size, file_path, file_hash, mime, timestamp,
                     created_date, modified_date, taken_date))
                
                stats['media_files_added'] += 1
                stats['files_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats['errors'] += 1
                continue
    
    conn.commit()
    conn.close()
    
    # Print summary (using print to avoid duplicate logging)
    print("\n=== Scan Summary ===")
    print(f"Total files found: {stats['total_files_found']}")
    print(f"Media files added to database: {stats['media_files_added']}")
    print(f"Files skipped (non-media): {stats['files_skipped']}")
    print(f"Errors encountered: {stats['errors']}")
    
    return stats

def find_duplicates():
    logger.info("\n=== Duplicates Summary ===")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Check duplicate file names
    c.execute("SELECT COUNT(DISTINCT name) FROM (SELECT name FROM files GROUP BY name HAVING COUNT(*) > 1)")
    duplicate_names_count = c.fetchone()[0]
    logger.info(f"Files with duplicate names: {duplicate_names_count}")
    
    # Check files with same name and size
    c.execute("SELECT COUNT(DISTINCT name) FROM (SELECT name FROM files GROUP BY name, size HAVING COUNT(*) > 1)")
    duplicate_name_size_count = c.fetchone()[0]
    logger.info(f"Files with same name and size: {duplicate_name_size_count}")
    
    # Check exact duplicates
    c.execute("SELECT COUNT(DISTINCT hash) FROM (SELECT hash FROM files WHERE hash IS NOT NULL GROUP BY hash HAVING COUNT(*) > 1)")
    exact_duplicates_count = c.fetchone()[0]
    logger.info(f"Files with exact duplicates (same hash): {exact_duplicates_count}")
    
    conn.close()

def find_near_duplicates():
    logger.info("\n=== Near Duplicates Summary ===")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("""
        SELECT COUNT(DISTINCT hash) 
        FROM (
            SELECT hash 
            FROM files 
            WHERE (mime LIKE 'image/%' OR mime LIKE 'video/%') 
            AND hash IS NOT NULL 
            GROUP BY hash 
            HAVING COUNT(*) > 1
        )
    """)
    near_duplicates_count = c.fetchone()[0]
    logger.info(f"Media files with potential duplicates: {near_duplicates_count}")
    
    conn.close()

if __name__ == "__main__":
    # Set logging level
    # logging.DEBUG - Show all messages
    # logging.INFO - Show info and above (progress, etc)
    # logging.WARNING - Show only warnings and errors
    logger = setup_logging(logging.INFO)
    
    logger.info("=== Photo Metadata Scanner ===")
    logger.info("Script starting...")
    base_directory = Path(STARTING_FOLDER)
    logger.info(f"Using directory: {base_directory}")
    
    if not base_directory.exists():
        logger.error(f"ERROR: Directory does not exist: {base_directory}")
        exit(1)
    if not base_directory.is_dir():
        logger.error(f"ERROR: Path exists but is not a directory: {base_directory}")
        exit(1)
    
    # Run scan and get statistics
    scan_directory(base_directory, file_limit=0, clear_db=True)
    find_duplicates()
    find_near_duplicates()
    
    logger.info("\nProcess complete!")
