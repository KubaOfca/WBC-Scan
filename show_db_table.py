from sqlalchemy import create_engine, Table, select, MetaData
from sqlalchemy.orm import sessionmaker

# Replace these values with your actual database connection details
DATABASE_TYPE = 'postgresql'  # or 'mysql', 'sqlite', etc.
USER = 'wbcadmin'
PASSWORD = '8MtoFLZgJ^Vz5EfirZxd!3mWHPVK8i'
HOST = 'wbc-database.cxi2kc080ax0.us-east-1.rds.amazonaws.com'
PORT = '5432'  # Default port for PostgreSQL; change if needed
DATABASE = 'wbc_db'
TABLE_NAME = 'batch'  # Replace with your chosen table name

# Create a database URL
DATABASE_URL = f'{DATABASE_TYPE}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}'

# Create an engine
engine = create_engine(DATABASE_URL)

# Create a metadata object
metadata = MetaData()

# Define the table
table = Table(TABLE_NAME, metadata, autoload_with=engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Print the contents of the table
print(f"Contents of table: {TABLE_NAME}")
stmt = select(table)
results = session.execute(stmt).fetchall()
for row in results:
    print(row)

# Close the session
session.close()
