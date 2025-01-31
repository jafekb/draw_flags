FROM python:3.8.10

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
RUN poetry install 

COPY . .

ENV PROJECT_DIR="/app"
ENV PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

EXPOSE 8000

CMD ["poetry", "run", "python", "backend/main.py"]
