"""Main application window for Leitor Ebook."""

import os
import tkinter as tk
from tkinter import filedialog, font, messagebox, simpledialog, ttk
from typing import Optional, Union

from leitor_ebook.bookmarks import (
    Bookmark,
    add_bookmark,
    add_recent_file,
    get_bookmarks,
    get_recent_files,
    remove_bookmark,
)
from leitor_ebook.epub_reader import EpubBook, load_epub
from leitor_ebook.pdf_reader import PdfBook, load_pdf


class App(tk.Tk):
    """Main window for the desktop ebook reader."""

    _MIN_FONT_SIZE = 8
    _MAX_FONT_SIZE = 36
    _DEFAULT_FONT_SIZE = 12
    _FONT_FAMILY = "Georgia"

    def __init__(self) -> None:
        super().__init__()
        self.title("Leitor Ebook")
        self.geometry("1000x700")
        self.minsize(600, 400)

        self._book: Optional[Union[EpubBook, PdfBook]] = None
        self._file_path: str = ""
        self._current_position: int = 0  # chapter (EPUB) or page index (PDF)
        self._font_size: int = self._DEFAULT_FONT_SIZE

        self._setup_menu()
        self._setup_toolbar()
        self._setup_main_area()
        self._setup_status_bar()
        self._show_welcome()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="Abrir… (Ctrl+O)", command=self._open_file, accelerator="Ctrl+O"
        )
        self._recent_menu = tk.Menu(file_menu, tearoff=False)
        file_menu.add_cascade(label="Arquivos recentes", menu=self._recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.quit)
        menubar.add_cascade(label="Arquivo", menu=file_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(
            label="Aumentar fonte (Ctrl++)",
            command=self._increase_font,
            accelerator="Ctrl++",
        )
        view_menu.add_command(
            label="Diminuir fonte (Ctrl+-)",
            command=self._decrease_font,
            accelerator="Ctrl+-",
        )
        view_menu.add_command(
            label="Tamanho padrão (Ctrl+0)",
            command=self._reset_font,
            accelerator="Ctrl+0",
        )
        menubar.add_cascade(label="Visualizar", menu=view_menu)

        # Bookmarks menu
        bm_menu = tk.Menu(menubar, tearoff=False)
        bm_menu.add_command(
            label="Adicionar marcador (Ctrl+B)",
            command=self._add_bookmark,
            accelerator="Ctrl+B",
        )
        bm_menu.add_command(
            label="Ver marcadores…", command=self._show_bookmarks
        )
        menubar.add_cascade(label="Marcadores", menu=bm_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Sobre…", command=self._show_about)
        menubar.add_cascade(label="Ajuda", menu=help_menu)

        self.config(menu=menubar)

        # Keyboard shortcuts
        self.bind("<Control-o>", lambda _: self._open_file())
        self.bind("<Control-equal>", lambda _: self._increase_font())
        self.bind("<Control-plus>", lambda _: self._increase_font())
        self.bind("<Control-minus>", lambda _: self._decrease_font())
        self.bind("<Control-0>", lambda _: self._reset_font())
        self.bind("<Control-b>", lambda _: self._add_bookmark())
        self.bind("<Left>", lambda _: self._go_prev())
        self.bind("<Right>", lambda _: self._go_next())

    def _setup_toolbar(self) -> None:
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_style = {"relief": tk.FLAT, "padx": 6, "pady": 3}

        tk.Button(toolbar, text="📂 Abrir", command=self._open_file, **btn_style).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4, pady=2
        )
        tk.Button(
            toolbar, text="◀ Anterior", command=self._go_prev, **btn_style
        ).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(
            toolbar, text="▶ Próximo", command=self._go_next, **btn_style
        ).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4, pady=2
        )
        tk.Button(
            toolbar, text="A-", command=self._decrease_font, **btn_style
        ).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(
            toolbar, text="A+", command=self._increase_font, **btn_style
        ).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4, pady=2
        )
        tk.Button(
            toolbar, text="🔖 Marcador", command=self._add_bookmark, **btn_style
        ).pack(side=tk.LEFT, padx=2, pady=2)

        # Search
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=4, pady=2
        )
        self._search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self._search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=2, pady=2)
        search_entry.bind("<Return>", lambda _: self._search())
        tk.Button(
            toolbar, text="🔍 Buscar", command=self._search, **btn_style
        ).pack(side=tk.LEFT, padx=2, pady=2)

    def _setup_main_area(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # TOC panel (left)
        toc_frame = ttk.LabelFrame(paned, text="Índice", width=220)
        toc_frame.pack_propagate(False)
        self._toc_list = tk.Listbox(
            toc_frame,
            activestyle="dotbox",
            selectmode=tk.SINGLE,
            exportselection=False,
        )
        toc_scroll = ttk.Scrollbar(
            toc_frame, orient=tk.VERTICAL, command=self._toc_list.yview
        )
        self._toc_list.config(yscrollcommand=toc_scroll.set)
        toc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._toc_list.pack(fill=tk.BOTH, expand=True)
        self._toc_list.bind("<<ListboxSelect>>", self._on_toc_select)
        paned.add(toc_frame, weight=0)

        # Reading area (right)
        read_frame = ttk.Frame(paned)
        self._text = tk.Text(
            read_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            padx=20,
            pady=15,
            spacing1=4,
            spacing3=4,
        )
        v_scroll = ttk.Scrollbar(
            read_frame, orient=tk.VERTICAL, command=self._text.yview
        )
        self._text.config(yscrollcommand=v_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(fill=tk.BOTH, expand=True)
        paned.add(read_frame, weight=1)

        self._apply_font()

    def _setup_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Nenhum arquivo aberto.")
        status_bar = tk.Label(
            self,
            textvariable=self._status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padx=6,
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Abrir ebook",
            filetypes=[
                ("Ebooks", "*.epub *.pdf"),
                ("EPUB", "*.epub"),
                ("PDF", "*.pdf"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".epub":
                book = load_epub(path)
            elif ext == ".pdf":
                book = load_pdf(path)
            else:
                messagebox.showerror(
                    "Formato não suportado",
                    f"O formato '{ext}' não é suportado.\n"
                    "Use arquivos .epub ou .pdf.",
                )
                return
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Erro ao abrir arquivo", str(exc))
            return

        self._book = book
        self._file_path = path
        self._current_position = 0
        self.title(f"Leitor Ebook — {book.title}")
        add_recent_file(path)
        self._rebuild_toc()
        self._update_recent_menu()
        self._render_current()

    def _rebuild_toc(self) -> None:
        self._toc_list.delete(0, tk.END)
        if isinstance(self._book, EpubBook):
            for i, ch in enumerate(self._book.chapters):
                self._toc_list.insert(tk.END, f"{i + 1}. {ch.title}")
        elif isinstance(self._book, PdfBook):
            for page in self._book.pages:
                self._toc_list.insert(tk.END, f"Página {page.number}")

    def _update_recent_menu(self) -> None:
        self._recent_menu.delete(0, tk.END)
        for path in get_recent_files():
            label = os.path.basename(path)
            self._recent_menu.add_command(
                label=label,
                command=lambda p=path: self._load_file(p),
            )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _go_next(self) -> None:
        if self._book is None:
            return
        limit = (
            len(self._book.chapters) - 1
            if isinstance(self._book, EpubBook)
            else self._book.total_pages - 1
        )
        if self._current_position < limit:
            self._current_position += 1
            self._render_current()

    def _go_prev(self) -> None:
        if self._book is None:
            return
        if self._current_position > 0:
            self._current_position -= 1
            self._render_current()

    def _on_toc_select(self, _event: tk.Event) -> None:
        selection = self._toc_list.curselection()
        if selection:
            self._current_position = selection[0]
            self._render_current(update_toc=False)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_current(self, update_toc: bool = True) -> None:
        if self._book is None:
            return

        if isinstance(self._book, EpubBook):
            chapters = self._book.chapters
            if not chapters:
                self._set_text("Este ebook não tem capítulos legíveis.")
                return
            pos = min(self._current_position, len(chapters) - 1)
            chapter = chapters[pos]
            header = f"{chapter.title}\n{'─' * 60}\n\n"
            self._set_text(header + chapter.content)
            total = len(chapters)
            self._status_var.set(
                f"{self._book.title}  |  Capítulo {pos + 1} de {total}"
            )
        elif isinstance(self._book, PdfBook):
            pages = self._book.pages
            if not pages:
                self._set_text("Este PDF não tem páginas legíveis.")
                return
            pos = min(self._current_position, len(pages) - 1)
            page = pages[pos]
            self._set_text(page.text or "(página sem texto)")
            self._status_var.set(
                f"{self._book.title}  |  Página {page.number} de {self._book.total_pages}"
            )

        if update_toc:
            self._toc_list.selection_clear(0, tk.END)
            self._toc_list.selection_set(self._current_position)
            self._toc_list.see(self._current_position)

    def _set_text(self, content: str) -> None:
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", content)
        self._text.yview_moveto(0)
        self._text.config(state=tk.DISABLED)

    def _show_welcome(self) -> None:
        welcome = (
            "Bem-vindo ao Leitor Ebook!\n\n"
            "Para começar:\n"
            "  • Use Arquivo → Abrir (Ctrl+O) para abrir um ebook.\n"
            "  • Formatos suportados: EPUB e PDF.\n\n"
            "Atalhos:\n"
            "  Ctrl+O   Abrir arquivo\n"
            "  ←  /  →  Capítulo / página anterior / próxima\n"
            "  Ctrl++   Aumentar fonte\n"
            "  Ctrl+-   Diminuir fonte\n"
            "  Ctrl+B   Adicionar marcador\n"
        )
        self._set_text(welcome)

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------

    def _apply_font(self) -> None:
        reading_font = font.Font(
            family=self._FONT_FAMILY, size=self._font_size
        )
        self._text.config(font=reading_font)

    def _increase_font(self) -> None:
        if self._font_size < self._MAX_FONT_SIZE:
            self._font_size += 1
            self._apply_font()

    def _decrease_font(self) -> None:
        if self._font_size > self._MIN_FONT_SIZE:
            self._font_size -= 1
            self._apply_font()

    def _reset_font(self) -> None:
        self._font_size = self._DEFAULT_FONT_SIZE
        self._apply_font()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self) -> None:
        query = self._search_var.get().strip()
        if not query:
            return

        # Remove previous highlights
        self._text.tag_remove("search_highlight", "1.0", tk.END)
        self._text.config(state=tk.NORMAL)

        start = "1.0"
        count = 0
        first_match = None
        while True:
            pos = self._text.search(
                query, start, nocase=True, stopindex=tk.END
            )
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self._text.tag_add("search_highlight", pos, end)
            if first_match is None:
                first_match = pos
            start = end
            count += 1

        self._text.tag_config(
            "search_highlight", background="#FFDD57", foreground="#000000"
        )
        if first_match:
            self._text.see(first_match)
            self._status_var.set(
                f"{count} ocorrência(s) encontrada(s) para '{query}'"
            )
        else:
            self._status_var.set(f"Nenhuma ocorrência encontrada para '{query}'")

        self._text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Bookmarks
    # ------------------------------------------------------------------

    def _add_bookmark(self) -> None:
        if self._book is None:
            messagebox.showinfo("Marcador", "Nenhum arquivo aberto.")
            return
        label = simpledialog.askstring(
            "Adicionar marcador",
            "Nome do marcador (opcional):",
            initialvalue=f"Posição {self._current_position + 1}",
        )
        if label is None:
            return
        bm = Bookmark(
            file_path=self._file_path,
            position=self._current_position,
            label=label or f"Posição {self._current_position + 1}",
        )
        add_bookmark(bm)
        self._status_var.set(f"Marcador '{bm.label}' adicionado.")

    def _show_bookmarks(self) -> None:
        if not self._file_path:
            messagebox.showinfo("Marcadores", "Nenhum arquivo aberto.")
            return

        bookmarks = get_bookmarks(self._file_path)
        if not bookmarks:
            messagebox.showinfo("Marcadores", "Nenhum marcador salvo para este arquivo.")
            return

        win = tk.Toplevel(self)
        win.title("Marcadores")
        win.geometry("400x300")
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(frame, activestyle="dotbox")
        listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for bm in bookmarks:
            listbox.insert(tk.END, f"[{bm.position + 1}] {bm.label}")

        btn_frame = ttk.Frame(win, padding=(10, 0, 10, 10))
        btn_frame.pack(fill=tk.X)

        def go_to() -> None:
            sel = listbox.curselection()
            if sel:
                bm = bookmarks[sel[0]]
                self._current_position = bm.position
                self._render_current()
                win.destroy()

        def delete_bm() -> None:
            sel = listbox.curselection()
            if sel:
                bm = bookmarks[sel[0]]
                remove_bookmark(self._file_path, bm.position)
                listbox.delete(sel[0])
                bookmarks.pop(sel[0])

        ttk.Button(btn_frame, text="Ir para", command=go_to).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="Remover", command=delete_bm).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="Fechar", command=win.destroy).pack(
            side=tk.RIGHT, padx=4
        )

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Sobre o Leitor Ebook",
            "Leitor Ebook v1.0.0\n\n"
            "Aplicativo desktop para leitura de ebooks.\n"
            "Suporta formatos EPUB e PDF.\n\n"
            "Desenvolvido em Python com tkinter.",
        )
