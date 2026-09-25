# compilador_av3

Compilador e analisador didático desenvolvido em Python para a avaliação AV3 da disciplina de Compiladores. O projeto implementa um subconjunto restrito, previsível e robusto de uma linguagem imperativa inspirada em Java/C.

---

## 1. Fluxo do Compilador

```text
Código Fonte
     ↓
Análise Léxica (Lexer)
     ↓
Tokens
     ↓
Tabela de Símbolos
     ↓
Análise Sintática (Parser)
     ↓
Árvore Sintática Abstrata (AST)
     ↓
Análise Semântica
```

---

## 2. Subconjunto da Linguagem

- **Tipos**: `int`, `String`
- **Literais**: Números inteiros (ex.: `10`) e strings delimitadas por aspas duplas (ex.: `"Gustavo"`).
- **Identificadores**: Iniciam com letra ou `_`, seguidos de letras, dígitos ou `_`.
- **Comandos**:
  - Declaração simples: `int x;`, `String nome;`
  - Declaração com inicialização: `int x = 10;`, `String nome = "Gustavo";`
  - Atribuição: `x = 20;`, `nome = "Maria";`
- **Expressões**: Literais, identificadores, parênteses `( )` e operadores aritméticos numéricos `+` e `-`.

> **Nota Semântica**: `+` e `-` são operadores estritamente numéricos. `String` não participa de operações aritméticas.

---

## 3. Gramática Oficial (GLC)

```bnf
<Programa> ::= <Comando>*

<Comando> ::= <Declaracao> | <Atribuicao>

<Declaracao> ::= <Tipo> <Identificador> ";"
               | <Tipo> <Identificador> "=" <Expressao> ";"

<Tipo> ::= "int" | "String"

<Atribuicao> ::= <Identificador> "=" <Expressao> ";"

<Expressao> ::= <Termo> (("+" | "-") <Termo>)*

<Termo> ::= <Identificador>
          | <Numero>
          | <StringLiteral>
          | "(" <Expressao> ")"
```

A especificação detalhada de tokens e regras semânticas está disponível em [SPEC.md](SPEC.md).

---

## 4. Estrutura do Projeto

```text
compilador_av3/
├── README.md
├── SPEC.md
├── src/
│   ├── __init__.py
│   ├── token.py
│   ├── lexer.py
│   ├── symbol_table.py
│   ├── parser.py
│   ├── ast_nodes.py
│   ├── semantic.py
│   ├── main.py
│   └── gui.py
└── tests/
    └── test_compiler.py
```

---

## 5. Como Executar

### Modo Terminal (Linha de Comando)

Na pasta raiz do projeto (`compilador_av3/`), execute:

```bash
python -m src.main <caminho_do_arquivo.java>
```

Exemplo:
```bash
python -m src.main arquivo.java
```

### Modo Gráfico (Interface Tkinter)

Para iniciar a aplicação visual do compilador:

```bash
python -m src.gui
```

> **Apresentação**: A interface inicia com o editor completamente **vazio**. O usuário deve abrir o arquivo `.java` ou `.c` fornecido externamente pelo professor (via botão **Abrir** / `Ctrl+O`) ou digitar/colar o código no editor, e em seguida pressionar **Analisar** (`F5`). O projeto é independente de arquivos de exemplo fixos.

#### Recursos da Interface Gráfica:
- **Editor de Código**: Área de texto monoespaçada com numeração de linhas, rolagem bidirecional, suporte a abrir e salvar arquivos `.java`, `.c` e `.txt`.
- **Pipeline de Análise**: Execução integrada sobre o código carregado sem travar a interface e com isolamento total de estado entre execuções.
- **Aba Tokens**: Tabela (`Treeview`) detalhando `#`, `Tipo`, `Lexema`, `Linha` e `Coluna` de cada token reconhecido.
- **Aba Tabela de Símbolos**: Relação tabular (`Treeview`) detalhando `Ordem`, `Identificador`, `Categoria`, `Tipo` e `Linha` para palavras reservadas e variáveis declaradas.
- **Aba AST**: Visualização hierárquica e textual da Árvore Sintática Abstrata produzida pelo parser (`pretty()`).
- **Aba Semântica**: Diagnóstico semântico exibindo aprovação `[OK]` ou os erros de tipagem/escopo detectados.
- **Aba Erros**: Painel consolidado que categoriza e apresenta falhas de entrada, léxicas, sintáticas e semânticas.
- **Atalhos Rápidos**:
  - `Ctrl+O`: Abrir arquivo
  - `Ctrl+S`: Salvar arquivo
  - `F5`: Executar análise
  - `Ctrl+L`: Limpar editor e resultados

### Categorias de Erro Tratadas

Todas as mensagens de erro são estruturadas e controladas sem tracebacks para o usuário:
- `[ERRO DE ENTRADA]`
- `[ERRO LÉXICO]`
- `[ERRO SINTÁTICO]`
- `[ERRO SEMÂNTICO]`

---

## 6. Como Executar os Testes

Execute a suíte automatizada oficial via `unittest`:

```bash
python -m unittest -v tests/test_compiler.py
```
