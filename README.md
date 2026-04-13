# Leitor Ebook

Aplicativo desktop em Python para leitura de ebooks.

## Funcionalidades

- Abertura de arquivos **EPUB** e **PDF**
- Exibição de capítulos (EPUB) e páginas (PDF) com rolagem
- Índice / Sumário na barra lateral esquerda
- Controle de tamanho de fonte (A+ / A-)
- Busca de texto com realce visual
- Marcadores: adicionar, navegar e remover posições salvas
- Lista de arquivos recentes
- Atalhos de teclado

## Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `Ctrl+O` | Abrir arquivo |
| `←` / `→` | Capítulo / página anterior / próxima |
| `Ctrl++` | Aumentar fonte |
| `Ctrl+-` | Diminuir fonte |
| `Ctrl+0` | Tamanho de fonte padrão |
| `Ctrl+B` | Adicionar marcador |

## Requisitos

- Python 3.8+
- Bibliotecas listadas em `requirements.txt`
- `tkinter` (incluso no Python padrão; em Linux instale `python3-tk`)

## Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Linux: instalar tkinter se necessário
sudo apt install python3-tk
```

## Execução

```bash
python main.py
```

## Estrutura do Projeto

```
leitor_ebook/          # Pacote principal
├── __init__.py
├── app.py             # Janela principal (interface tkinter)
├── epub_reader.py     # Leitor de arquivos EPUB
├── pdf_reader.py      # Leitor de arquivos PDF
└── bookmarks.py       # Gerenciamento de marcadores e arquivos recentes
tests/
└── test_readers.py    # Testes unitários
main.py                # Ponto de entrada
requirements.txt       # Dependências Python
```

## Testes

```bash
python -m pytest tests/ -v
```
