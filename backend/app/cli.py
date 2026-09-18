from __future__ import annotations

import argparse
import getpass

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.models import User
from app.db.session import get_session


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user")
    create.add_argument("username")
    args = parser.parse_args()
    if args.command == "create-user":
        password = getpass.getpass("Password: ")
        if len(password) < 12:
            parser.error("Password must contain at least 12 characters")
        with get_session() as session:
            if session.scalar(select(User).where(User.username == args.username)):
                parser.error("User already exists")
            session.add(User(username=args.username, password_hash=hash_password(password)))
            session.commit()
        print(f"Created user {args.username}")


if __name__ == "__main__":
    main()

