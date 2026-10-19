from pymongo import MongoClient
from decouple import config

_mongo_client = None

def get_mongo_client():
    """Retorna una instancia singleton de MongoClient con connection pooling."""
    global _mongo_client
    if _mongo_client is None:
        try:
            from django.conf import settings
            mongo_uri = getattr(settings, 'MONGO_URI', None) or config('MONGODB_URI', default=config('MONGO_URI', default=''))
        except Exception:
            mongo_uri = config('MONGODB_URI', default=config('MONGO_URI', default=''))

        if not mongo_uri:
            raise ValueError("MONGO_URI no está configurada en settings ni en .env")

        _mongo_client = MongoClient(
            mongo_uri,
            maxPoolSize=50,
            serverSelectionTimeoutMS=5000,
        )
    return _mongo_client

def get_mongo_db():
    """Retorna la base de datos de MongoDB configurada."""
    client = get_mongo_client()
    try:
        from django.conf import settings
        db_name = getattr(settings, 'MONGO_DB_NAME', None) or config('MONGODB_DB_NAME', default='transporte_conciertos')
    except Exception:
        db_name = config('MONGODB_DB_NAME', default='transporte_conciertos')
    return client[db_name]

