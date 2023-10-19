import os
import sys

from dotenv import load_dotenv

from astrapy.base import AstraDbClient
from astrapy.collections import AstraDb, AstraDbCollection
from astrapy.ops import AstraDbOps

sys.path.append("../")

load_dotenv()

# First, we work with devops
token = os.getenv("ASTRA_DB_APPLICATION_TOKEN", None)
astra_ops = AstraDbOps(token)

# Define a database to create
database_definition = {
    "name": "vector_test",
    "tier": "serverless",
    "cloudProvider": "GCP",
    "keyspace": os.getenv("ASTRA_DB_KEYSPACE", "default_namespace"),
    "region": os.getenv("ASTRA_DB_REGION", None),
    "capacityUnits": 1,
    "user": "token",
    "password": token,
    "dbType": "vector",
}

# Create the database
create_result = astra_ops.create_database(database_definition=database_definition)

# Grab the new information from the database
db_id = create_result["id"]

# Initialize our AstraClient
astra_client = AstraDbClient(db_id=db_id, token=token)

# Possible Initializations
astra_client_vectordb1 = astra_client.vector_database()
astra_client_vectordb2 = AstraDb(db_id=db_id, token=token)

# Possible Operations
astra_client_vectordb1.create_collection(name="collection_test", size=5)
astra_client_vectordb1.delete_collection(name="collection_test")
astra_client_vectordb2.create_collection(name="collection_test", size=5)

# Collections
astra_db_collection = AstraDbCollection(
    collection="collection_test",
    astra_db=astra_client_vectordb1
)
# Or...
astra_db_collection = AstraDbCollection(
    collection="collection_test",
    db_id=db_id,
    token=token
)

result = astra_db_collection.insert_one(
    {
        "_id": "5",
        "name": "Coded Cleats Copy",
        "description": "ChatGPT integrated sneakers that talk to you",
        "$vector": [0.25, 0.25, 0.25, 0.25, 0.25],
    }
)
