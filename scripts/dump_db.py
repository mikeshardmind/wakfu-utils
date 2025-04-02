import sqlite3
import os

def dump_database(db_path, output_path):
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        
        # Open the output file
        with open(output_path, 'w', encoding='utf-8') as f:
            # Iterate through all tables in the database
            for table_name in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
                table_name = table_name[0]
                
                # Dump table schema
                schema = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';").fetchone()[0]
                f.write(schema + ';\n')
                
                # Dump table data
                for row in conn.execute(f"SELECT * FROM {table_name};"):
                    # Convert row to SQL INSERT statement
                    placeholders = ','.join(['?'] * len(row))
                    insert_stmt = f"INSERT INTO {table_name} VALUES ({placeholders});\n"
                    f.write(insert_stmt.replace('?', '"{}"').format(*row) + '\n')
        
        conn.close()
        print(f"Database dump completed: {output_path}")
    except Exception as e:
        print(f"Error dumping database: {e}")

if __name__ == "__main__":
    dump_database(
        r"c:\Users\pevalcar\Proyects\wakfu-utils\wakautosolver\data\items.db", 
        r"c:\Users\pevalcar\Proyects\wakfu-utils\wakautosolver\data\items.sql"
    )
