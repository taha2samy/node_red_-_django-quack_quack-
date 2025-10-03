# 3. Getting Started

This guide provides step-by-step instructions to get a local instance of Quack Quack up and running for development and testing.

We recommend using the Docker setup as it provides a consistent, isolated environment with all dependencies included.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/products/docker-desktop/)
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

---

## Recommended Setup: Using Docker & Docker Compose

This is the fastest and most reliable way to start the project.

### Step 1: Clone the Repository

Open your terminal and clone the project from GitHub:

```sh
git clone https://github.com/taha2samy/node_red_-_django-quack_quack-.git
cd node_red_-_django-quack_quack-
```

### Step 2: Configure Environment Variables

The project uses an environment file to manage secrets and configuration.

1.  Navigate to the `docker/` directory:
    ```sh
    cd docker
    ```
2.  Rename the example environment file:
    ```sh
    mv enfile.env .env
    ```
3.  Open the `.env` file in your favorite text editor. You **must** set the following variables:
    - `SECRET_KEY`: A long, random string for Django's security. You can generate one easily [online](https://djecrety.ir/) or with Python.
    - `DEBUG`: Set to `True` for development.
    - `ALLOWED_HOSTS`: For local development, you can use `localhost, 127.0.0.1`.

### Step 3: Build and Run the Containers

From within the `docker/` directory, run the following command. This will download the necessary images, build your project's container, and start all the services (web app, database, Redis).

```sh
docker-compose up --build
```

The `--build` flag is only necessary the first time you run it or after making changes to the `Dockerfile`. On subsequent runs, you can just use `docker-compose up`.

### Step 4: Access the Application

Once the containers are running, you can access the application:

- **Web Application:** Open your browser to `http://localhost:8000`
- **Django Admin:** Navigate to `http://localhost:8000/admin/`

> **Note:** The first time you run the application, the database will be created, but you won't have a superuser. To create one, open a **new terminal window**, navigate to the `docker/` directory, and run:
> ```sh
> docker-compose exec web python manage.py createsuperuser
> ```
> Follow the prompts to create your admin account.

---

## Alternative: Manual Setup (Without Docker)

This method is for users who prefer not to use Docker and want to manage dependencies on their host machine.

### Prerequisites

- [Python](https://www.python.org/) 3.12+
- [PostgreSQL](https://www.postgresql.org/download/)
- [Redis](https://redis.io/docs/getting-started/installation/)
- [Pipenv](https://pipenv.pypa.io/en/latest/installation.html) (or `venv`)

### Step 1: Clone and Set Up Environment

```sh
git clone https://github.com/taha2samy/node_red_-_django-quack_quack-.git
cd node_red_-_django-quack_quack-

# Create a virtual environment and install dependencies
pipenv install
pipenv shell
```

### Step 2: Configure Database and Redis

1.  Make sure your PostgreSQL and Redis servers are running.
2.  Create a new PostgreSQL database and user for the project.
3.  Update the `DATABASES` and `CACHES` settings in `myproject/settings.py` with your local database and Redis connection details.

### Step 3: Run Migrations and Start the Server

1.  Apply the database migrations:
    ```sh
    python manage.py migrate
    ```
2.  Create a superuser:
    ```sh
    python manage.py createsuperuser
    ```
3.  Start the Django development server:
    ```sh
    python manage.py runserver
    ```

The application will now be running at `http://localhost:8000`.
