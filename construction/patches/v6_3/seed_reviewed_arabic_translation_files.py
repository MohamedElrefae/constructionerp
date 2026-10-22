"""Seed all reviewed Arabic translation CSV files during deploy."""

from construction.insert_translations import execute as seed_translations


def execute():
    seed_translations()
