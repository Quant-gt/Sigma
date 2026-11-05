# apps/api/app/seeds/whitebox_blueprints.py
# Re-exporting whitebox blueprints for both seeds and services namespaces
from apps.api.app.services.whitebox_blueprints import build_10_proven_whitebox_blueprints

__all__ = ["build_10_proven_whitebox_blueprints"]
