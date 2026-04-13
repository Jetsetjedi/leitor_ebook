/**
 * reader.js — lógica completa do leitor de ebooks.
 * Funcionalidades: paginação, zoom, marcadores, anotações, busca, TOC, progresso.
 * Sem eval(), sem innerHTML com dados do servidor sem sanitização.
 */
(function () {
  'use strict';

  // BOOK_ID, BOOK_FORMAT, START_POSITION são injetados pelo template (server-side, json-safe)
  let currentPage  = START_POSITION || 0;
  let totalPages   = 1;
  let fontSize     = 100;
  const SAVE_DELAY = 1500;
  let saveTimer    = null;

  // ── Refs DOM ─────────────────────────────────────────────────────────────
  const contentEl   = document.getElementById('book-content');
  const pageInfoEl  = document.getElementById('page-info');
  const btnPrev     = document.getElementById('btn-prev');
  const btnNext     = document.getElementById('btn-next');
  const btnToc      = document.getElementById('btn-toc');
  const btnBookmark = document.getElementById('btn-bookmark');
  const btnNote     = document.getElementById('btn-note');
  const btnSearch   = document.getElementById('btn-search');
  const sidebar     = document.getElementById('sidebar');
  const searchBar   = document.getElementById('search-bar');
  const searchInput = document.getElementById('search-input');
  const searchResultsEl = document.getElementById('search-results');
  const zoomLabel   = document.getElementById('zoom-label');
  const modalNote   = document.getElementById('modal-note');
  const noteText    = document.getElementById('note-text');

  // ── Inicialização ─────────────────────────────────────────────────────────
  loadPage(currentPage);
  loadToc();
  loadBookmarks();
  loadNotes();

  // ── Paginação ─────────────────────────────────────────────────────────────
  btnPrev.addEventListener('click', () => { if (currentPage > 0) loadPage(currentPage - 1); });
  btnNext.addEventListener('click', () => { if (currentPage < totalPages - 1) loadPage(currentPage + 1); });

  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown')
      { if (currentPage < totalPages - 1) loadPage(currentPage + 1); }
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')
      { if (currentPage > 0) loadPage(currentPage - 1); }
  });

  function loadPage(page) {
    contentEl.innerHTML = '<div class="loading-spinner">Carregando…</div>';

    fetch(`/api/book/${BOOK_ID}/page/${page}`)
      .then(r => r.json())
      .then(data => {
        currentPage  = data.current_page;
        totalPages   = data.total_pages;
        // O servidor já escapa o HTML (html.escape) — exibição segura
        contentEl.innerHTML = data.content || '<p><em>Página sem conteúdo.</em></p>';
        contentEl.scrollTop = 0;
        updatePagination();
        scheduleProgressSave();
      })
      .catch(() => {
        contentEl.textContent = 'Erro ao carregar página.';
      });
  }

  function updatePagination() {
    pageInfoEl.textContent = `${currentPage + 1} / ${totalPages}`;
    btnPrev.disabled = currentPage === 0;
    btnNext.disabled = currentPage >= totalPages - 1;
  }

  // ── Zoom ──────────────────────────────────────────────────────────────────
  document.getElementById('btn-zoom-in').addEventListener('click', () => setZoom(fontSize + 10));
  document.getElementById('btn-zoom-out').addEventListener('click', () => setZoom(fontSize - 10));

  function setZoom(size) {
    fontSize = Math.min(200, Math.max(60, size));
    contentEl.style.fontSize = `${fontSize}%`;
    zoomLabel.textContent = `${fontSize}%`;
  }

  // ── Sidebar / TOC ─────────────────────────────────────────────────────────
  btnToc.addEventListener('click', () => {
    sidebar.classList.toggle('hidden');
    activateTab('toc');
  });

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      sidebar.classList.remove('hidden');
      activateTab(btn.dataset.tab);
    });
  });

  function activateTab(name) {
    document.querySelectorAll('.tab-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.tab === name));
    document.querySelectorAll('.tab-content').forEach(c =>
      c.classList.toggle('hidden', c.id !== `tab-${name}`));
  }

  function loadToc() {
    fetch(`/api/book/${BOOK_ID}/toc`)
      .then(r => r.json())
      .then(toc => {
        const el = document.getElementById('tab-toc');
        if (!toc.length) { el.textContent = 'Índice não disponível.'; return; }
        el.innerHTML = '';
        toc.forEach(item => {
          const a = document.createElement('a');
          a.className = `toc-item level-${item.level || 1}`;
          a.textContent = item.title || `Página ${item.page ?? item.index}`;
          a.href = '#';
          a.addEventListener('click', e => {
            e.preventDefault();
            loadPage(item.page ?? item.index ?? 0);
          });
          el.appendChild(a);
        });
      });
  }

  // ── Marcadores ────────────────────────────────────────────────────────────
  btnBookmark.addEventListener('click', () => {
    fetch(`/api/book/${BOOK_ID}/bookmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: String(currentPage), label: `Página ${currentPage + 1}` }),
    })
      .then(r => r.json())
      .then(() => { loadBookmarks(); activateTab('bookmarks'); sidebar.classList.remove('hidden'); });
  });

  function loadBookmarks() {
    fetch(`/api/book/${BOOK_ID}/bookmarks`)
      .then(r => r.json())
      .then(list => renderSidebarList('tab-bookmarks', list, 'bookmark'));
  }

  // ── Anotações ─────────────────────────────────────────────────────────────
  btnNote.addEventListener('click', () => {
    noteText.value = '';
    modalNote.classList.remove('hidden');
    noteText.focus();
  });

  document.getElementById('btn-note-cancel').addEventListener('click', () =>
    modalNote.classList.add('hidden'));

  document.getElementById('btn-note-save').addEventListener('click', () => {
    const content = noteText.value.trim();
    if (!content) return;
    fetch(`/api/book/${BOOK_ID}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: String(currentPage), content }),
    })
      .then(r => r.json())
      .then(() => {
        modalNote.classList.add('hidden');
        loadNotes();
        activateTab('notes');
        sidebar.classList.remove('hidden');
      });
  });

  function loadNotes() {
    fetch(`/api/book/${BOOK_ID}/notes`)
      .then(r => r.json())
      .then(list => renderSidebarList('tab-notes', list, 'note'));
  }

  function renderSidebarList(tabId, items, type) {
    const el = document.getElementById(tabId);
    el.innerHTML = '';
    if (!items.length) {
      el.textContent = type === 'bookmark' ? 'Sem marcadores.' : 'Sem anotações.';
      return;
    }
    items.forEach(item => {
      const div = document.createElement('div');
      div.className = 'sidebar-item';

      const span = document.createElement('span');
      span.className = 'sidebar-item-text';
      span.textContent = item.label || item.content || `Pos. ${item.position}`;
      span.title = item.content || item.label || '';
      span.addEventListener('click', () => loadPage(Number(item.position) || 0));

      const del = document.createElement('button');
      del.className = 'sidebar-item-del';
      del.textContent = '✕';
      del.title = 'Remover';
      del.addEventListener('click', () => {
        const url = `/api/book/${BOOK_ID}/${type === 'bookmark' ? 'bookmarks' : 'notes'}/${item.id}`;
        fetch(url, { method: 'DELETE' }).then(() => {
          type === 'bookmark' ? loadBookmarks() : loadNotes();
        });
      });

      div.appendChild(span);
      div.appendChild(del);
      el.appendChild(div);
    });
  }

  // ── Busca ─────────────────────────────────────────────────────────────────
  btnSearch.addEventListener('click', () => searchBar.classList.toggle('hidden'));
  document.getElementById('btn-search-close').addEventListener('click', () => {
    searchBar.classList.add('hidden');
    searchResultsEl.innerHTML = '';
  });

  document.getElementById('btn-search-go').addEventListener('click', runSearch);
  searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });

  function runSearch() {
    const q = searchInput.value.trim();
    if (!q) return;
    searchResultsEl.textContent = 'Buscando…';

    fetch(`/api/book/${BOOK_ID}/search?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(results => {
        searchResultsEl.innerHTML = '';
        if (!results.length) {
          searchResultsEl.textContent = 'Nenhum resultado encontrado.';
          return;
        }
        results.forEach(r => {
          const div = document.createElement('div');
          div.className = 'search-result-item';
          div.textContent = `Pág. ${r.page + 1}: ${r.snippet}`;
          div.addEventListener('click', () => {
            loadPage(r.page);
            searchBar.classList.add('hidden');
          });
          searchResultsEl.appendChild(div);
        });
      });
  }

  // ── Progresso ─────────────────────────────────────────────────────────────
  function scheduleProgressSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      fetch(`/api/book/${BOOK_ID}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position: currentPage }),
      });
    }, SAVE_DELAY);
  }

  // ── Fecha modal ao clicar fora ─────────────────────────────────────────────
  modalNote.addEventListener('click', e => {
    if (e.target === modalNote) modalNote.classList.add('hidden');
  });
})();
