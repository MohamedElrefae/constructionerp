"""Seed reviewed Arabic UI translations during deploy.

The local site can have Translation records that are not present on Frappe
Cloud. Running this as a patch makes the database seed part of deploy instead
of relying only on local state or compiled message files.
"""

from construction.insert_translations import execute as seed_translations


def execute():
    seed_translations()
