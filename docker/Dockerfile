FROM python:3.12.11-alpine AS build
WORKDIR /code
RUN apk add --no-cache gcc musl-dev python3-dev linux-headers
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade pip
RUN pip install -r requirements.txt
COPY . /code/
RUN python manage.py collectstatic --noinput

FROM python:3.12.11-alpine AS production
WORKDIR /code
COPY --from=build /usr/local /usr/local
COPY --from=build /code /code
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "myproject.asgi:application"]
