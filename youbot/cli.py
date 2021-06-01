"""Command line interface for youbot."""

import typer

app = typer.Typer()


@app.command()
def hello(name: str):
    typer.echo(f"Hello {name}")


@app.command()
def bye(name: str, formal: bool = False):
    if formal:
        typer.echo(f"Goodbye Mr. {name}. Have a good day.")
    else:
        typer.echo(f"Bye {name}!")


if __name__ == "__main__":
    app()
