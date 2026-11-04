
import sqlite3

conn = sqlite3.connect("miniplm.db")
cursor = conn.cursor()

print("\n--- DOCUMENTS TABLE ---")

cursor.execute("SELECT * FROM documents")
documents = cursor.fetchall()

for document in documents:
    print(document)

print("\n--- PART_DOCUMENTS TABLE ---")

cursor.execute("SELECT * FROM part_documents")
relationships = cursor.fetchall()

for relationship in relationships:
    print(relationship)

print("\n--- JOIN VERIFICATION ---")

cursor.execute("""
    SELECT
        parts.id,
        parts.name,
        documents.id,
        documents.filename
    FROM part_documents
    JOIN parts ON parts.id = part_documents.part_id
    JOIN documents ON documents.id = part_documents.document_id
""")

for row in cursor.fetchall():
    print(row)

conn.close()
