# Langate 3000 infrastructure

This repository is here to hold the langate infrastructure. It is composed of
the frontend, the backend and netcontrol servers, alongside the configuration for tools to make it work (Caddy and a database).

## Documentation

Technical documentation is available [here](docs/manuel/src/SUMMARY.md) (in french).

## Contributing

Please read carefully [the CONTRIBUTING.md file](CONTRIBUTING.md) before any
contribution.

## Installing and running the langate locally

- Installation:
```sh
git clone git@github.com:InsaLan/langate-3000.git
cp .env.dist .env
# edit your .env with your local settings, then:
chmod 0600 .env
```
- To start the containers:
```sh
docker compose -f docker-compose-beta.yml up --build
```
You can also pass the `-d` argument to "detach" the container from the terminal, or run it in the background.

- Then to stop the containers:
```sh
docker compose -f docker-compose-beta.yml down
```

The "beta" environment is available at `beta.WEBSITE_HOST` and it's own API at `api.beta.WEBSITE_HOST`.

There is hotreload for the front (with vite) and the back (with django runserver).

## Running the prod environment

- Put 0 in the .env file for the `DEV` and `MOCK_NETCONTROL` variables.

- Build the images:
```sh
docker compose build
```
- Run the following command :
```sh
docker compose up
```
- To stop the prod environment :
```sh
docker compose down
```

The frontend is available at `WEBSITE_HOST` and its API at `api.WEBSITE_HOST`.

## Cleanup DB

Between two events, the database needs to be cleaned. This will remove all users and devices.
```sh
rm -rf volumes
```
The only persistent elements (marks and whitelisted devices) are stored in `backend/assets/misc`.

## Cleanup containers

Docker can take a lot of disk space with all the images.
You have a few options to clean it up:

- To remove all the containers and images:
```sh
docker compose -f docker-compose.yml down --rmi all && docker compose -f docker-compose-beta.yml down --rmi all
```
- To remove all the custom images (the ones we build and not the ones we pull from docker hub):
```sh
docker compose -f docker-compose.yml down --rmi local && docker compose -f docker-compose-beta.yml down --rmi local
```
