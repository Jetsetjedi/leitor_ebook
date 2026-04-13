"""Entry point for the Leitor Ebook desktop application."""

from leitor_ebook.app import App


def main() -> None:
    """Launch the ebook reader."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
