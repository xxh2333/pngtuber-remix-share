"""Django Ninja API 主实例"""
from ninja import NinjaAPI

from accounts.api import router as accounts_router
from works.api import router as works_router

api = NinjaAPI(title="PNGTuber Remix Share API", version="1.0.0")

api.add_router("/auth", accounts_router)
api.add_router("/works", works_router)
