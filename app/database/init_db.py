from app.database.base import Base
from app.database.postgres import engine

# Importar modelos
from app.models.user import User


def init_db():

    Base.metadata.create_all(bind=engine)