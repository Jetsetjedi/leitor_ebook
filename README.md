# 📚 Leitor Ebook

Leitor de ebooks local com interface web, construído em Python + Flask.  
Projeto de estudo — **use somente ebooks de sua propriedade ou de domínio público.**

## Funcionalidades

- Suporte a **PDF, EPUB, MOBI e TXT**
- Navegação por páginas / capítulos
- Marcadores e anotações por livro
- Busca no texto
- Histórico de leitura (posição salva automaticamente)
- Zoom / ajuste de tamanho de fonte
- Interface web moderna, sem frameworks JS externos

## Segurança implementada

| Proteção | Detalhes |
|---|---|
| OWASP A01 – Broken Access Control | Todas as rotas validam o `book_id` antes de acessar arquivos |
| OWASP A02 – Cryptographic Failures | `SECRET_KEY` via variável de ambiente; cookies `HttpOnly + SameSite` |
| OWASP A03 – Injection | Queries 100% parametrizadas; HTML de ebooks sanitizado antes de exibir |
| OWASP A04 – Insecure Design | Uploads validados por extensão **e** magic number real |
| OWASP A05 – Security Misconfiguration | Flask-Talisman: CSP, X-Content-Type, X-XSS-Protection, Referrer-Policy |
| OWASP A07 – Auth Failures | Rate limiting com Flask-Limiter |
| Path Traversal | Nomes de arquivo no disco são UUIDs gerados internamente |
| Max upload | 50 MB configurável |

## Instalação

**Pré-requisito:** Python 3.11+

```bash
# 1. Clone o repositório
git clone https://github.com/Jetsetjedi/leitor_ebook.git
cd leitor_ebook

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e defina SECRET_KEY com um valor único e seguro:
# python -c "import secrets; print(secrets.token_hex(32))"

# 5. Inicie o servidor
python run.py
```

Acesse: **http://127.0.0.1:5000**

## Testes

```bash
pip install pytest
pytest tests/
```

## Estrutura do Projeto

```
leitor_ebook/
├── app/
│   ├── __init__.py          # Factory da aplicação Flask
│   ├── config.py            # Configurações por ambiente
│   ├── models/
│   │   └── database.py      # SQLite (queries parametrizadas)
│   ├── routes/
│   │   ├── main.py          # Página da biblioteca
│   │   ├── reader.py        # Leitor
│   │   └── api.py           # API JSON
│   ├── utils/
│   │   ├── file_handler.py  # Upload seguro
│   │   └── book_processor.py# Extração de conteúdo por formato
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│       ├── index.html
│       └── reader.html
├── data/                    # Banco SQLite (gerado automaticamente)
├── uploads/                 # Arquivos enviados (não commitar)
├── tests/
├── run.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Aviso Legal

Este software é destinado a uso **pessoal e educacional**.  
Não distribua ebooks protegidos por direitos autorais.

## Licença

MIT — veja [LICENSE](LICENSE).
