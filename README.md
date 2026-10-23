# CineLocal

Aplicación web MVC para buscar películas en OMDb, guardarlas en SQLite, puntuarlas con una escala de 1 a 5 y publicar comentarios. La interfaz usa Bootstrap 5 y JavaScript nativo; la API está implementada con FastAPI.

## Arquitectura

```text
APP_WEB_FINAL_PROJECT/
|-- config/
|   `-- database.py          Motor SQLite, Base, SessionLocal y dependencia de sesión
|-- controllers/
|   `-- movie_controller.py  Endpoints REST y comunicación asíncrona con OMDb
|-- models/
|   |-- db_models.py         Entidades SQLAlchemy y relaciones
|   `-- schemas.py           Validación y contratos Pydantic v2
|-- views/
|   `-- index.html           Interfaz web responsiva y cliente Fetch
|-- main.py                  Aplicación FastAPI y montaje de rutas/estáticos
|-- requirements.txt
`-- .env                     Clave de OMDb (local, no se versiona)
```

La capa de controladores maneja las solicitudes HTTP, consulta OMDb y persiste los datos a través de SQLAlchemy. Los modelos representan películas, valoraciones y comentarios. Las relaciones son uno-a-muchos desde `Movie` hacia `Rating` y `Comment`. Los esquemas Pydantic validan entradas y estructuran las respuestas. La vista consume la API sin recargar la página.

Las películas se identifican localmente por su `imdb_id`; la búsqueda OMDb registra resultados válidos si aún no existen. La puntuación promedio y su cantidad se calculan en SQL. Las valoraciones son registros individuales, no se reemplazan entre usuarios.

## Requisitos

- Python 3.10 o superior.
- Una clave gratuita de OMDb API: <https://www.omdbapi.com/apikey.aspx>.

## Instalación y ejecución local

En PowerShell, desde la raíz del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz con la clave asignada por OMDb:

```dotenv
OMDB_API_KEY=tu_clave_de_omdb
```

Arranca el servidor de desarrollo:

```powershell
uvicorn main:app --reload
```

Abre <http://127.0.0.1:8000>. La documentación interactiva de la API está disponible en <http://127.0.0.1:8000/docs>.

## Base de datos

Al importar `main.py` durante el arranque, `Base.metadata.create_all(bind=engine)` crea las tablas automáticamente si no existen. La conexión predeterminada es `sqlite:///./movies.db`, así que el archivo se crea en el directorio de trabajo desde el que se ejecuta Uvicorn. SQLite se mantiene enteramente local; `movies.db` está excluido de Git.

La base de datos incluye estas tablas:

- `movies`: identificador OMDb, título, año, póster y sinopsis.
- `ratings`: puntuación entera entre 1 y 5, vinculada a una película.
- `comments`: texto y fecha de creación, vinculados a una película.

## API

- `GET /api/movies?q={titulo}`: busca en OMDb, valida el año y registra localmente películas no existentes.
- `GET /api/movies/{movie_id}`: devuelve la ficha local, con la sinopsis completa de OMDb cuando la clave está configurada, el promedio y comentarios.
- `POST /api/movies/{movie_id}/rate`: recibe `{"score": 1}` hasta `{"score": 5}`.
- `POST /api/movies/{movie_id}/comment`: recibe `{"text": "Comentario"}`.

Los endpoints de detalle, valoración y comentario operan sobre películas ya guardadas mediante una búsqueda. Sin `OMDB_API_KEY`, el servidor puede arrancar y atender recursos locales, pero las búsquedas responden con `503 Service Unavailable`.

## Despliegue

Para ejecutar en un servidor, instala las dependencias en el entorno virtual, proporciona `OMDB_API_KEY` como variable de entorno (o mediante un `.env` protegido), y ejecuta Uvicorn con un gestor de procesos adecuado. En producción, configura HTTPS y conserva o respalda `movies.db`; para varios procesos o mayor concurrencia, migra a una base de datos servidor y utiliza migraciones como Alembic en lugar de depender de `create_all`.
