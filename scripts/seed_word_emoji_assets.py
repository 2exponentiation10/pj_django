#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BUDparty.settings")


def main():
    _bootstrap()
    import django

    django.setup()

    from django.contrib.auth import get_user_model

    from api.learning_visuals import seed_practice_visuals

    username = os.environ.get("SATOORI_VISUAL_OWNER", "master")
    owner = get_user_model().objects.get(username=username)
    result = seed_practice_visuals(owner=owner)
    print(result)


if __name__ == "__main__":
    main()
