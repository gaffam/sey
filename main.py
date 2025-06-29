from gambusia.api import app
from gambusia.config import settings
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
