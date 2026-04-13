/**
 * main.js - Página da biblioteca
 * Sem bibliotecas externas, sem eval(), sem innerHTML com dados não sanitizados.
 */
(function () {
  'use strict';

  const dropZone  = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const statusEl  = document.getElementById('upload-status');

  // ── Drag-and-drop ────────────────────────────────────────────────────────
  dropZone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(evt =>
    dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('drag-over'); })
  );
  ['dragleave', 'drop'].forEach(evt =>
    dropZone.addEventListener(evt, () => dropZone.classList.remove('drag-over'))
  );
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) uploadFile(fileInput.files[0]);
  });

  // ── Upload ────────────────────────────────────────────────────────────────
  function uploadFile(file) {
    const MAX = 50 * 1024 * 1024;
    const ALLOWED = ['pdf', 'epub', 'mobi', 'txt'];
    const ext = file.name.split('.').pop().toLowerCase();

    if (!ALLOWED.includes(ext)) {
      showStatus('Formato não suportado. Use PDF, EPUB, MOBI ou TXT.', 'error');
      return;
    }
    if (file.size > MAX) {
      showStatus('Arquivo muito grande. Máximo: 50 MB.', 'error');
      return;
    }

    const label = document.getElementById('drop-label');
    label.textContent = `Enviando ${escapeHtml(file.name)}…`;

    const form = new FormData();
    form.append('file', file);

    fetch('/api/upload', { method: 'POST', body: form })
      .then(r => r.json().then(data => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (ok) {
          showStatus(`"${escapeHtml(data.title)}" adicionado com sucesso!`, 'success');
          setTimeout(() => location.reload(), 1200);
        } else {
          showStatus(escapeHtml(data.error || 'Erro no upload.'), 'error');
        }
      })
      .catch(() => showStatus('Erro de conexão.', 'error'))
      .finally(() => { label.textContent = 'Arraste um arquivo ou clique aqui'; });
  }

  // ── Deletar livro ─────────────────────────────────────────────────────────
  document.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = Number(btn.dataset.id);
      if (!Number.isInteger(id) || id <= 0) return;
      if (!confirm('Remover este livro da biblioteca?')) return;

      fetch(`/api/book/${id}`, { method: 'DELETE' })
        .then(r => { if (r.ok) location.reload(); })
        .catch(() => alert('Erro ao remover livro.'));
    });
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  function showStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.className = `status-msg ${type}`;
    statusEl.hidden = false;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();
