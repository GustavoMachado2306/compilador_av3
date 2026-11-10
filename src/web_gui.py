import json
import socket
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .main import analyze_source, read_source_file


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def list_example_files() -> list:
    """Lista os arquivos de exemplo disponíveis na pasta examples/."""
    items = []
    if EXAMPLES_DIR.exists() and EXAMPLES_DIR.is_dir():
        for p in sorted(EXAMPLES_DIR.iterdir()):
            if p.is_file() and p.suffix.lower() in (".java", ".c", ".txt"):
                content, err = read_source_file(str(p))
                if err is None and content is not None:
                    items.append({"name": p.name, "content": content})
    return items


def build_analysis_payload(source: str) -> dict:
    """
    Executa Lexer, Parser, SymbolTable e SemanticAnalyzer sobre o código-fonte
    e retorna um dicionário serializável em JSON para a rota POST /analyze.
    """
    if source is None:
        source = ""

    result = analyze_source(source)

    tokens_data = [
        {
            "index": idx,
            "type": tok.type.name,
            "lexeme": tok.lexeme,
            "line": tok.line,
            "column": tok.column,
        }
        for idx, tok in enumerate(result.tokens, start=1)
    ]

    symbols_data = []
    if result.symbol_table is not None:
        for sym in result.symbol_table.all():
            symbols_data.append(
                {
                    "order": sym.get("order", "-"),
                    "name": sym.get("name", ""),
                    "category": sym.get("category", ""),
                    "type": sym.get("type", ""),
                    "line": sym.get("line", "-"),
                }
            )

    if result.ast is not None:
        ast_text = result.ast.pretty()
    else:
        ast_text = "(Árvore sintática não gerada devido a erros na análise)"

    if result.semantic_errors:
        semantic_text = (
            f"ERROS SEMÂNTICOS ENCONTRADOS ({len(result.semantic_errors)}):\n\n"
            + "\n\n".join(str(e) for e in result.semantic_errors)
        )
        semantic_ok = False
    elif result.ast is not None:
        semantic_text = "[OK]\nValidação semântica concluída sem erros básicos."
        semantic_ok = True
    else:
        semantic_text = "(Validação semântica não executada devido a erro léxico ou sintático)"
        semantic_ok = False

    errors_list = []
    if getattr(result, "lexical_errors", None):
        for le in result.lexical_errors:
            errors_list.append(str(le))
    elif result.lexical_error:
        errors_list.append(str(result.lexical_error))

    if getattr(result, "syntactic_errors", None):
        for se in result.syntactic_errors:
            errors_list.append(str(se))
    elif result.syntactic_error:
        errors_list.append(str(result.syntactic_error))

    for sem_err in result.semantic_errors:
        errors_list.append(str(sem_err))

    if result.has_errors:
        errors_text = ("\n\n" + ("-" * 60) + "\n\n").join(errors_list)
        status_text = f"Análise concluída com erro(s): {len(errors_list)} problema(s) detectado(s)"
    else:
        if not source.strip():
            errors_text = "[OK]\nArquivo vazio: nenhum comando para analisar."
            status_text = "Análise concluída: arquivo vazio"
        else:
            errors_text = (
                "[OK]\nNenhum erro encontrado no código-fonte.\n"
                "O programa está conforme com a gramática e regras semânticas."
            )
            status_text = "Análise concluída com sucesso (0 erros)"

    return {
        "success": result.success,
        "has_errors": result.has_errors,
        "source": source,
        "tokens": tokens_data,
        "symbols": symbols_data,
        "ast": ast_text,
        "semantic_text": semantic_text,
        "semantic_ok": semantic_ok,
        "errors": errors_list,
        "errors_text": errors_text,
        "status": status_text,
    }


WEB_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compilador AV3 — Interface Web Local</title>
<style>
  :root {
    --bg-canvas: #09090b;
    --bg-surface: #121215;
    --bg-elevated: #18181b;
    --bg-hover: #222227;
    --border-hairline: #27272a;
    --border-focus: #3b82f6;
    --text-primary: #fafafa;
    --text-secondary: #a1a1aa;
    --text-muted: #71717a;
    --accent-blue: #2563eb;
    --accent-blue-hover: #1d4ed8;
    --accent-blue-soft: rgba(37, 99, 235, 0.14);
    --status-ok-bg: rgba(16, 185, 129, 0.1);
    --status-ok-text: #34d399;
    --status-ok-border: rgba(16, 185, 129, 0.25);
    --status-err-bg: rgba(244, 63, 94, 0.1);
    --status-err-text: #fb7185;
    --status-err-border: rgba(244, 63, 94, 0.25);
    --font-sans: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    --font-mono: "Consolas", "JetBrains Mono", "SFMono-Regular", Menlo, monospace;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    background-color: var(--bg-canvas);
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 1.5;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  header {
    background-color: var(--bg-surface);
    border-bottom: 1px solid var(--border-hairline);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-shrink: 0;
  }

  .brand-title {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text-primary);
  }

  .brand-subtitle {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .toolbar {
    background-color: var(--bg-canvas);
    border-bottom: 1px solid var(--border-hairline);
    padding: 10px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .file-indicator {
    font-size: 12px;
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }

  button, select, .file-upload-label {
    height: 34px;
    padding: 0 12px;
    border-radius: 6px;
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 150ms ease-out;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border-hairline);
    background-color: var(--bg-elevated);
    color: var(--text-primary);
    user-select: none;
  }

  button:hover, select:hover, .file-upload-label:hover {
    background-color: var(--bg-hover);
    border-color: #3f3f46;
  }

  button:active, .file-upload-label:active {
    transform: scale(0.99);
  }

  button:focus-visible, select:focus-visible {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
  }

  .btn-primary {
    background-color: var(--accent-blue);
    border-color: var(--accent-blue);
    color: #ffffff;
    font-weight: 600;
  }

  .btn-primary:hover {
    background-color: var(--accent-blue-hover);
    border-color: var(--accent-blue-hover);
  }

  input[type="file"] {
    display: none;
  }

  main {
    flex: 1;
    display: grid;
    grid-template-rows: minmax(220px, 44%) 1fr;
    gap: 12px;
    padding: 12px 20px;
    overflow: hidden;
  }

  .panel {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-hairline);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .panel-header {
    padding: 8px 14px;
    border-bottom: 1px solid var(--border-hairline);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background-color: var(--bg-elevated);
    flex-shrink: 0;
  }

  .panel-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
  }

  .editor-wrapper {
    flex: 1;
    display: flex;
    position: relative;
    overflow: hidden;
    background-color: var(--bg-surface);
  }

  .line-numbers {
    min-width: 48px;
    width: auto;
    padding: 10px 10px 10px 8px;
    text-align: right;
    background-color: var(--bg-elevated);
    border-right: 1px solid var(--border-hairline);
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 20px;
    font-variant-numeric: tabular-nums;
    white-space: pre;
    user-select: none;
    overflow: hidden;
    flex-shrink: 0;
    cursor: default;
  }

  textarea#code-editor {
    flex: 1;
    background-color: transparent;
    color: var(--text-primary);
    border: none;
    padding: 10px 14px;
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 20px;
    resize: none;
    outline: none;
    white-space: pre;
    overflow: auto;
    tab-size: 4;
    word-break: normal;
    overflow-wrap: normal;
  }

  .tabs-bar {
    display: flex;
    align-items: center;
    background-color: var(--bg-elevated);
    border-bottom: 1px solid var(--border-hairline);
    padding: 0 8px;
    gap: 4px;
    flex-shrink: 0;
  }

  .tab-btn {
    height: 36px;
    padding: 0 14px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
  }

  .tab-btn:hover {
    background-color: rgba(255, 255, 255, 0.03);
    color: var(--text-primary);
  }

  .tab-btn.active {
    color: #60a5fa;
    border-bottom-color: var(--accent-blue);
    background-color: var(--accent-blue-soft);
  }

  .tab-badge {
    margin-left: 6px;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    background-color: #27272a;
    color: var(--text-secondary);
  }

  .tab-content {
    flex: 1;
    overflow: auto;
    display: none;
    padding: 0;
  }

  .tab-content.active {
    display: block;
  }

  table.data-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }

  table.data-table thead th {
    position: sticky;
    top: 0;
    background-color: var(--bg-elevated);
    color: var(--text-secondary);
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 8px 14px;
    border-bottom: 1px solid var(--border-hairline);
    text-align: left;
    z-index: 1;
  }

  table.data-table tbody td {
    padding: 7px 14px;
    border-bottom: 1px solid var(--border-hairline);
    color: var(--text-primary);
  }

  table.data-table tbody tr:hover {
    background-color: var(--bg-hover);
  }

  .num-col {
    text-align: right;
    width: 80px;
    color: var(--text-secondary);
  }

  pre.output-pre {
    padding: 14px;
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text-primary);
  }

  pre.output-pre.status-ok {
    color: var(--status-ok-text);
  }

  pre.output-pre.status-err {
    color: var(--status-err-text);
  }

  .empty-state {
    padding: 36px 20px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }

  footer.status-bar {
    background-color: var(--bg-surface);
    border-top: 1px solid var(--border-hairline);
    padding: 6px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-secondary);
    flex-shrink: 0;
  }
</style>
</head>
<body>

<header>
  <div>
    <div class="brand-title">Compilador AV3</div>
    <div class="brand-subtitle">Analisador Didático: Léxico • Tabela de Símbolos • Sintático • AST • Semântica</div>
  </div>
  <div class="header-controls">
    <select id="example-select" aria-label="Selecionar exemplo da pasta examples">
      <option value="">Carregar exemplo de examples/...</option>
    </select>
    <label class="file-upload-label" for="file-input">Abrir Arquivo (.java / .c)</label>
    <input type="file" id="file-input" accept=".java,.c,.txt">
  </div>
</header>

<div class="toolbar">
  <div class="toolbar-actions">
    <button type="button" class="btn-primary" id="btn-analyze">Analisar Código (F5)</button>
    <button type="button" id="btn-clear">Limpar Resultados (Ctrl+L)</button>
    <button type="button" id="btn-copy">Copiar Tudo (Ctrl+Shift+C)</button>
  </div>
  <div class="file-indicator" id="file-label">Nenhum arquivo aberto</div>
</div>

<main>
  <section class="panel" aria-label="Editor de código fonte">
    <div class="panel-header">
      <span class="panel-title">Editor de Código Fonte</span>
      <span class="file-indicator" id="cursor-info">Linha 1, Coluna 1</span>
    </div>
    <div class="editor-wrapper">
      <div class="line-numbers" id="line-numbers">1</div>
      <textarea id="code-editor" wrap="off" spellcheck="false" placeholder="Digite ou carregue um código Java para analisar..."></textarea>
    </div>
  </section>

  <section class="panel" aria-label="Resultados da análise">
    <nav class="tabs-bar" role="tablist">
      <button type="button" class="tab-btn active" data-tab="tab-tokens">Tokens <span class="tab-badge" id="badge-tokens">0</span></button>
      <button type="button" class="tab-btn" data-tab="tab-symbols">Tabela de Símbolos <span class="tab-badge" id="badge-symbols">0</span></button>
      <button type="button" class="tab-btn" data-tab="tab-ast">AST</button>
      <button type="button" class="tab-btn" data-tab="tab-semantic">Semântica</button>
      <button type="button" class="tab-btn" data-tab="tab-errors">Erros <span class="tab-badge" id="badge-errors">0</span></button>
    </nav>

    <div class="tab-content active" id="tab-tokens">
      <div id="tokens-container" class="empty-state">(Aguardando análise)</div>
    </div>

    <div class="tab-content" id="tab-symbols">
      <div id="symbols-container" class="empty-state">(Aguardando análise)</div>
    </div>

    <div class="tab-content" id="tab-ast">
      <pre class="output-pre" id="ast-output"></pre>
    </div>

    <div class="tab-content" id="tab-semantic">
      <pre class="output-pre" id="semantic-output">(Aguardando análise)</pre>
    </div>

    <div class="tab-content" id="tab-errors">
      <pre class="output-pre" id="errors-output">(Aguardando análise)</pre>
    </div>
  </section>
</main>

<footer class="status-bar">
  <span id="status-text">Pronto</span>
  <span>Modo Web Local • Zero Dependências</span>
</footer>

<script>
  const editor = document.getElementById('code-editor');
  const lineNumbers = document.getElementById('line-numbers');
  const cursorInfo = document.getElementById('cursor-info');
  const fileLabel = document.getElementById('file-label');
  const statusText = document.getElementById('status-text');
  const exampleSelect = document.getElementById('example-select');
  const fileInput = document.getElementById('file-input');

  let lastAnalysisData = null;

  function updateLineNumbers() {
    const lines = editor.value.split('\\n').length || 1;
    const nums = [];
    for (let i = 1; i <= lines; i++) {
      nums.push(i);
    }
    lineNumbers.textContent = nums.join('\\n');
    lineNumbers.scrollTop = editor.scrollTop;
  }

  function updateCursorInfo() {
    const pos = editor.selectionStart || 0;
    const upToCursor = editor.value.slice(0, pos);
    const lines = upToCursor.split('\\n');
    const line = lines.length;
    const col = lines[lines.length - 1].length + 1;
    cursorInfo.textContent = `Linha ${line}, Coluna ${col}`;
  }

  editor.addEventListener('input', () => {
    updateLineNumbers();
    updateCursorInfo();
  });
  editor.addEventListener('scroll', () => {
    lineNumbers.scrollTop = editor.scrollTop;
  });
  lineNumbers.addEventListener('wheel', (e) => {
    editor.scrollTop += e.deltaY;
    e.preventDefault();
  }, { passive: false });
  editor.addEventListener('click', updateCursorInfo);
  editor.addEventListener('keyup', updateCursorInfo);

  // Alternância de abas
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectTab(btn.getAttribute('data-tab'));
    });
  });

  function selectTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
    });
    document.querySelectorAll('.tab-content').forEach(c => {
      c.classList.toggle('active', c.id === tabId);
    });
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderTokens(tokens) {
    const container = document.getElementById('tokens-container');
    document.getElementById('badge-tokens').textContent = tokens.length;
    if (!tokens.length) {
      container.className = 'empty-state';
      container.innerHTML = '(Nenhum token gerado)';
      return;
    }
    container.className = '';
    const rows = tokens.map(t => `
      <tr>
        <td class="num-col">${t.index}</td>
        <td>${escapeHtml(t.type)}</td>
        <td>${escapeHtml(t.lexeme)}</td>
        <td class="num-col">${t.line}</td>
        <td class="num-col">${t.column}</td>
      </tr>
    `).join('');
    container.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th class="num-col">#</th>
            <th>Tipo</th>
            <th>Lexema</th>
            <th class="num-col">Linha</th>
            <th class="num-col">Coluna</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  function renderSymbols(symbols) {
    const container = document.getElementById('symbols-container');
    document.getElementById('badge-symbols').textContent = symbols.length;
    if (!symbols.length) {
      container.className = 'empty-state';
      container.innerHTML = '(Tabela de símbolos vazia)';
      return;
    }
    container.className = '';
    const rows = symbols.map(s => `
      <tr>
        <td class="num-col">${escapeHtml(s.order)}</td>
        <td>${escapeHtml(s.name)}</td>
        <td>${escapeHtml(s.category)}</td>
        <td>${escapeHtml(s.type)}</td>
        <td class="num-col">${escapeHtml(s.line)}</td>
      </tr>
    `).join('');
    container.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th class="num-col">Ordem</th>
            <th>Identificador</th>
            <th>Categoria</th>
            <th>Tipo</th>
            <th class="num-col">Linha</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  async function runAnalysis() {
    statusText.textContent = 'Analisando código...';
    try {
      const response = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: editor.value })
      });
      const data = await response.json();
      lastAnalysisData = data;

      renderTokens(data.tokens || []);
      renderSymbols(data.symbols || []);

      const astEl = document.getElementById('ast-output');
      astEl.textContent = data.ast || '';

      const semEl = document.getElementById('semantic-output');
      semEl.textContent = data.semantic_text || '';
      semEl.className = 'output-pre ' + (data.semantic_ok ? 'status-ok' : (data.has_errors ? 'status-err' : ''));

      const errEl = document.getElementById('errors-output');
      errEl.textContent = data.errors_text || '';
      errEl.className = 'output-pre ' + (data.has_errors ? 'status-err' : 'status-ok');
      document.getElementById('badge-errors').textContent = (data.errors || []).length;

      statusText.textContent = data.status || 'Análise concluída';

      if (data.has_errors) {
        selectTab('tab-errors');
      } else if (editor.value.trim()) {
        selectTab('tab-ast');
      }
    } catch (err) {
      statusText.textContent = 'Falha ao comunicar com o servidor local';
    }
  }

  function clearResults() {
    lastAnalysisData = null;
    document.getElementById('tokens-container').className = 'empty-state';
    document.getElementById('tokens-container').textContent = '(Aguardando análise)';
    document.getElementById('symbols-container').className = 'empty-state';
    document.getElementById('symbols-container').textContent = '(Aguardando análise)';
    document.getElementById('badge-tokens').textContent = '0';
    document.getElementById('badge-symbols').textContent = '0';
    document.getElementById('badge-errors').textContent = '0';
    document.getElementById('ast-output').textContent = '';
    const semEl = document.getElementById('semantic-output');
    semEl.className = 'output-pre';
    semEl.textContent = '(Aguardando análise)';
    const errEl = document.getElementById('errors-output');
    errEl.className = 'output-pre';
    errEl.textContent = '(Aguardando análise)';
    statusText.textContent = 'Pronto';
  }

  async function copyAll() {
    const src = editor.value.trim() ? editor.value : '(vazio)';
    let tokStr = '(Nenhum token gerado)';
    let symStr = '(Vazia)';
    if (lastAnalysisData && lastAnalysisData.tokens && lastAnalysisData.tokens.length) {
      tokStr = lastAnalysisData.tokens
        .map(t => `${t.index}\\t${t.type}\\t${t.lexeme}\\tL:${t.line}\\tC:${t.column}`)
        .join('\\n');
    }
    if (lastAnalysisData && lastAnalysisData.symbols && lastAnalysisData.symbols.length) {
      symStr = lastAnalysisData.symbols
        .map(s => `${s.order}\\t${s.name}\\t${s.category}\\t${s.type}\\tL:${s.line}`)
        .join('\\n');
    }
    const astStr = document.getElementById('ast-output').textContent.trim() || '(Vazia)';
    const semStr = document.getElementById('semantic-output').textContent.trim() || '(Vazia)';
    const errStr = document.getElementById('errors-output').textContent.trim() || '(Nenhum erro)';

    const report = [
      `=== CÓDIGO FONTE ===\\n${src}`,
      `=== TOKENS ===\\n${tokStr}`,
      `=== TABELA DE SÍMBOLOS ===\\n${symStr}`,
      `=== AST ===\\n${astStr}`,
      `=== SEMÂNTICA ===\\n${semStr}`,
      `=== ERROS ===\\n${errStr}`
    ].join('\\n\\n');

    try {
      await navigator.clipboard.writeText(report);
      statusText.textContent = 'Tudo copiado para a área de transferência!';
    } catch (e) {
      statusText.textContent = 'Não foi possível copiar automaticamente.';
    }
  }

  document.getElementById('btn-analyze').addEventListener('click', runAnalysis);
  document.getElementById('btn-clear').addEventListener('click', clearResults);
  document.getElementById('btn-copy').addEventListener('click', copyAll);

  // Carrega lista de exemplos de examples/
  async function loadExamplesList() {
    try {
      const res = await fetch('/examples');
      const data = await res.json();
      (data.examples || []).forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.name;
        opt.textContent = `examples/${item.name}`;
        exampleSelect.appendChild(opt);
      });
    } catch (e) {}
  }

  exampleSelect.addEventListener('change', async () => {
    const name = exampleSelect.value;
    if (!name) return;
    try {
      const res = await fetch('/example?name=' + encodeURIComponent(name));
      const data = await res.json();
      if (data.content !== undefined) {
        editor.value = data.content;
        fileLabel.textContent = `Arquivo: ${data.name}`;
        updateLineNumbers();
        clearResults();
        statusText.textContent = `Exemplo carregado: ${data.name}`;
      }
    } catch (e) {
      statusText.textContent = 'Erro ao carregar arquivo de exemplo';
    }
  });

  fileInput.addEventListener('change', (ev) => {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      editor.value = String(reader.result || '');
      fileLabel.textContent = `Arquivo: ${file.name}`;
      exampleSelect.value = '';
      updateLineNumbers();
      clearResults();
      statusText.textContent = `Arquivo carregado: ${file.name}`;
    };
    reader.readAsText(file, 'utf-8');
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'F5') {
      e.preventDefault();
      runAnalysis();
    } else if ((e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L')) {
      e.preventDefault();
      clearResults();
    } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'c' || e.key === 'C')) {
      e.preventDefault();
      copyAll();
    }
  });

  updateLineNumbers();
  loadExamplesList();
</script>
</body>
</html>
"""


class CompilerHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP zero-dependências para a Interface Web do Compilador."""

    def log_message(self, format, *args):
        # Silencia logs verbosos no console durante uso interativo ou testes
        return

    def _send_json(self, payload: dict, status_code: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status_code: int = 200):
        body = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html"):
            self._send_html(WEB_HTML, 200)
            return

        if route == "/examples":
            examples = [{"name": item["name"]} for item in list_example_files()]
            self._send_json({"examples": examples}, 200)
            return

        if route == "/example":
            params = urllib.parse.parse_qs(parsed.query)
            name = params.get("name", [""])[0]
            for item in list_example_files():
                if item["name"] == name:
                    self._send_json(item, 200)
                    return
            self._send_json({"error": f"Exemplo '{name}' não encontrado."}, 404)
            return

        self._send_json({"error": "Rota não encontrada."}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/analyze":
            self._send_json({"error": "Rota não encontrada."}, 404)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else ""

        source = ""
        if raw_body:
            try:
                data = json.loads(raw_body)
                if isinstance(data, dict):
                    source = data.get("source", "")
                else:
                    source = str(data)
            except json.JSONDecodeError:
                parsed_form = urllib.parse.parse_qs(raw_body)
                if "source" in parsed_form:
                    source = parsed_form["source"][0]
                else:
                    source = raw_body

        payload = build_analysis_payload(source)
        self._send_json(payload, 200)


def create_web_server(host: str = "127.0.0.1", preferred_port: int = 8000) -> tuple:
    """
    Cria uma instância de HTTPServer na porta preferencial (8000) ou escolhe
    automaticamente uma porta livre caso a porta esteja ocupada.
    Retorna (server, url).
    """
    ports_to_try = [preferred_port] + list(range(preferred_port + 1, preferred_port + 25)) + [0]
    last_err = None
    for port in ports_to_try:
        try:
            server = HTTPServer((host, port), CompilerHTTPRequestHandler)
            actual_port = server.server_address[1]
            url = f"http://{host}:{actual_port}"
            return server, url
        except OSError as err:
            last_err = err
            continue
    raise RuntimeError(f"Não foi possível iniciar o servidor web local: {last_err}")


def start_web_gui(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    """Inicia o servidor HTTP da Interface Web Local e abre o navegador padrão."""
    server, url = create_web_server(host=host, preferred_port=port)
    print(f"[WEB GUI] Interface Web Local iniciada em: {url}")
    print("[WEB GUI] Pressione Ctrl+C no terminal para encerrar o servidor.")
    if open_browser:
        try:
            threading.Timer(0.15, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[WEB GUI] Servidor encerrado pelo usuário.")
    finally:
        server.server_close()


def main():
    start_web_gui()


if __name__ == "__main__":
    main()

