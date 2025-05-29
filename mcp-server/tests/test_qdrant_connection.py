from utils.qdrant_utils import get_qdrant_client


def test_qdrant_connection():
    client = get_qdrant_client()
    # List collections to verify connection
    collections = client.get_collections()
    print("Qdrant collections:", collections)


if __name__ == "__main__":
    test_qdrant_connection()
