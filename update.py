import typer
from fileidentification.conf.update_signatures import update_signatures


if __name__ == "__main__":
    typer.run(update_signatures)
