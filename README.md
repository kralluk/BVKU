- Python3 
- Venv
- Docker - you have to have rights to use docker without sudo <!--  https://docs.docker.com/engine/install/linux-postinstall -->
```
sudo groupadd docker            # Create docker group - some linux distributions already have
sudo usermod -aG docker $USER   # Add your user to the docker group 
newgrp docker                   # Activate the group changes
```
- Docker Compose


## Installation
- Get this repository
```
cd BVKU/
python3 -m venv ./venv
. venv/bin/activate
```
- Install necessary packages
```
python3 -m pip install -r requirements.txt
```
- Start the app
```
python3 cli.py
```
## Some notes

- IF you want to use Mongo-Express, default login is **admin** and **pass**.
