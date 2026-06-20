from app.database.base import Base
from app.database.postgres import engine

# Importar modelos
from app.models.user import User
from app.models.farm import Farm
from app.models.plot import Plot
from app.models.sensor import Sensor


def init_db():

    Base.metadata.create_all(bind=engine)