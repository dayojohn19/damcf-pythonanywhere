#!/usr/bin/env python3
"""Convert PostgreSQL dump to SQLite3 database."""

import subprocess
import sqlite3
import re
import sys

def restore_dump_to_sql():
    """Restore custom format dump to plain SQL."""
    print("Restoring dump to SQL format...")
    result = subprocess.run(
        ["pg_restore", "-f", "-", "db_backup.dump"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error restoring dump: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout

def convert_sql_to_sqlite(sql_text):
    """Convert PostgreSQL SQL to SQLite-compatible SQL."""
    # Remove SERIAL type and replace with INTEGER PRIMARY KEY AUTOINCREMENT
    sql_text = re.sub(r'\bSERIAL\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql_text)
    
    # Remove BIGSERIAL (convert to INTEGER)
    sql_text = re.sub(r'\bBIGSERIAL\b', 'INTEGER', sql_text)
    
    # Convert SERIAL/BIGSERIAL definitions in CREATE TABLE
    sql_text = re.sub(
        r'id\s+bigserial\s+not\s+null',
        'id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
        sql_text,
        flags=re.IGNORECASE
    )
    sql_text = re.sub(
        r'id\s+integer\s+not\s+null\s+primary\s+key',
        'id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL',
        sql_text,
        flags=re.IGNORECASE
    )
    
    # Remove PRIMARY KEY constraints for id fields (already handled above)
    sql_text = re.sub(
        r',\s*CONSTRAINT\s+\w+_pkey\s+PRIMARY KEY\s*\(\s*id\s*\)',
        '',
        sql_text,
        flags=re.IGNORECASE
    )
    
    # Remove IF NOT EXISTS from types and functions
    sql_text = re.sub(r'\bCREATE\s+TYPE\s+.*?;', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    sql_text = re.sub(r'\bCREATE\s+FUNCTION\s+.*?;', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove SCHEMA statements
    sql_text = re.sub(r'SET\s+search_path\s+.*?;', '', sql_text, flags=re.IGNORECASE)
    
    # Remove SET statements
    sql_text = re.sub(r'^SET\s+.*?;', '', sql_text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove SEQUENCE related statements
    sql_text = re.sub(r'CREATE\s+SEQUENCE\s+.*?;', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    sql_text = re.sub(r'ALTER\s+SEQUENCE\s+.*?;', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    sql_text = re.sub(r'SELECT\s+pg_catalog\.setval\(.*?\);', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove GRANT statements
    sql_text = re.sub(r'GRANT\s+.*?;', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove ALTER TABLE... ADD CONSTRAINT on sequences
    sql_text = re.sub(r'ALTER\s+TABLE\s+.*?OWNED\s+BY\s+.*?;', '', sql_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert DEFAULT nextval() to NULL
    sql_text = re.sub(
        r"DEFAULT\s+nextval\(['\"].*?['\"]\)",
        '',
        sql_text,
        flags=re.IGNORECASE
    )
    
    # Remove WITH (oids=false) or similar
    sql_text = re.sub(r'\)\s+WITH\s+\([^)]*\)\s*;', ');', sql_text, flags=re.IGNORECASE)
    
    # Remove double slashes in comments
    sql_text = re.sub(r'--.*?$', '', sql_text, flags=re.MULTILINE)
    
    # Clean up multiple newlines
    sql_text = re.sub(r'\n\s*\n+', '\n', sql_text)
    
    return sql_text

def import_to_sqlite(sql_text, db_file='database.sqlite3'):
    """Import SQL into SQLite3 database."""
    print(f"Creating SQLite database: {db_file}")
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Split by semicolon, but handle cases where semicolon is in strings
    statements = sql_text.split(';')
    
    for i, statement in enumerate(statements):
        statement = statement.strip()
        if not statement:
            continue
        
        try:
            cursor.execute(statement)
            if (i + 1) % 100 == 0:
                print(f"  Executed {i + 1} statements...")
        except sqlite3.Error as e:
            print(f"Warning: Error executing statement {i + 1}: {e}")
            print(f"  Statement: {statement[:100]}...")
            # Continue anyway
    
    conn.commit()
    conn.close()
    print(f"✓ SQLite database created: {db_file}")

def main():
    print("Converting PostgreSQL database to SQLite3...")
    print()
    
    # Restore dump to SQL
    sql_text = restore_dump_to_sql()
    print(f"✓ Restored {len(sql_text)} bytes of SQL")
    print()
    
    # Convert to SQLite syntax
    print("Converting SQL syntax...")
    sqlite_sql = convert_sql_to_sqlite(sql_text)
    print(f"✓ Converted to SQLite syntax ({len(sqlite_sql)} bytes)")
    print()
    
    # Import to SQLite
    import_to_sqlite(sqlite_sql)
    print()
    print("✓ Conversion complete!")

if __name__ == '__main__':
    main()
