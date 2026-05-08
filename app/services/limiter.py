from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

""" Rate limit setup (Track by ip addresss)"""
limiter = Limiter(key_func=get_remote_address)