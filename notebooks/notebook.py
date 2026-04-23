import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # A marimo notebook

    You can import your library code.
    """)
    return


@app.cell
def _():
    from utils import add

    return (add,)


@app.cell
def _(add):
    add(1, 3)
    return


if __name__ == "__main__":
    app.run()
