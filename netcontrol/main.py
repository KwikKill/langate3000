from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from .nft import Nft
from .arp import Arp

logger = logging.getLogger('uvicorn.error')
# for some reason, default loggers are not working with FastAPI

logger.info("Checking that nftables is working...")
nft = Nft(logger)
arp = Arp(logger)
nft.check_nftables()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that "wraps" around the FastAPI app's lifespan :
    The part before the yield is executed before the app starts;
    The part after the yield is executed after the app stops.
    """
    
    nft.setup_portail()
    
    yield
    
    nft.remove_portail()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return "netcontrol is running"
 
@app.post("/connect_user")
def connect_user(mac: str, mark: int, name: str) -> None:
    nft.connect_user(mac, mark, name)

@app.delete("/disconnect_user")
def delete_user(mac: str) -> None:
    nft.delete_user(mac)

@app.put("/set_mark")
def set_mark(mac: str, mark: int) -> None:
    nft.set_mark(mac, mark)

@app.get("/get_mac")
def get_mac(ip: str):
    return arp.get_mac(ip)

@app.get("/get_ip")
def get_ip(mac: str):
    return arp.get_ip(mac)