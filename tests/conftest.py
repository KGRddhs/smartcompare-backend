"""Shared test configuration — loads .env before any test modules import."""
from dotenv import load_dotenv

load_dotenv(override=True)
