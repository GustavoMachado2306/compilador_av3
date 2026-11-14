# compilador_av3

Compilador e analisador acadêmico para a linguagem Java desenvolvido em Python (sem dependências externas), com foco em análise léxica abrangente, parser completo com construção de AST, tabela de símbolos por escopo, análise semântica básica e interfaces de execução (CLI, GUI Tkinter e Web GUI local).

---

## 1. Fluxo do Compilador

```text
Código Fonte Java
     ↓
Análise Léxica (Lexer)
     ↓
Tokens
     ↓
Análise Sintática (Parser)
     ↓
Árvore Sintática Abstrata (AST)
     ↓
Tabela de Símbolos + Análise Semântica Básica
```

---

## 2. Escopo Implementado

- **Analisador Léxico (`src/compiler/lexer.py`)**:
  - Comentários de linha (`//`), bloco (`/* ... */`) e Javadoc (`/** ... */`);
  - Delimitadores, operadores com *Maximal Munch* (`=`, `+=`, `->`, `::`, `...`, `<<`, `>>`, `>>>`, etc.), palavras reservadas e literais (`true`, `false`, `null`, inteiros dec/hex/bin/oct, `float`/`double`, `char`, `String`).
- **Analisador Sintático e AST (`src/compiler/parser.py`, `src/compiler/ast_nodes.py`)**:
  - Unidades de compilação ordinárias, modulares e compactas (`package`, `import`, `import static`, `import module`, `module`);
  - Declarações de classes, interfaces, enums, records, `@interface`, construtores, campos, métodos, inicializadores e tipos aninhados/locais;
  - Annotations, Type Annotations, generics (`<T extends ...>`, wildcards `? extends`/`? super`), patterns (`TypePattern`, `RecordPattern`, `_`, `when`) e switch moderno (`:` e `->`, `SwitchExpression`, `yield`);
  - Instruções (`if`/`else`, `while`, `do/while`, `for`, `enhanced for`, `try`/`catch`/`finally`, `try-with-resources`, `switch`, `return`, `break`/`continue` rotulados, `throw`, `assert`, `synchronized`) e todos os níveis de precedência de expressões, casts, lambdas (`->`), method references (`::`), arrays e instanciações.
- **Tabela de Símbolos e Analisador Semântico (`src/compiler/symbol_table.py`, `src/compiler/semantic.py`)**:
  - Escopos aninhados, detecção de identificadores não declarados e declarações duplicadas no mesmo escopo;
  - Tipagem básica (primitivos, `void`, `String`, `null`, tipos declarados na unidade), *widening* numérico, concatenação de `String`, validação de condições booleanas, `return`, `break`/`continue` e chamadas locais;
  - Tolerância para referências externas (ex.: `System.out.println`).

---

## 3. Estrutura do Projeto

```text
compilador_av3/
├── README.md
├── examples/
│   ├── ExpressoesJava.java
│   ├── FluxoJava.java
│   ├── Pessoa.java
│   ├── exemplo_annotations_s5.java
│   ├── exemplo_classes_s3.java
│   ├── exemplo_compacto_s2.java
│   ├── exemplo_expressoes_s8.java
│   ├── exemplo_fase_a.java
│   ├── exemplo_instrucoes_s6.java
│   ├── exemplo_interfaces_enums_records_s4.java
│   ├── exemplo_modular_s2.java
│   ├── exemplo_ordinario_s2.java
│   └── exemplo_pattern_matching_s7.java
├── src/
│   ├── __init__.py
│   ├── main.py                                 # Entrypoint unificado (compatível com CLI, GUI e imports públicos)
│   ├── compiler/                               # Núcleo do compilador
│   │   ├── __init__.py
│   │   ├── ast_nodes.py                        # Nós da AST com pretty-printing hierárquico e to_dict()
│   │   ├── lexer.py                            # Analisador léxico Java
│   │   ├── parser.py                           # Analisador sintático descendente recursivo
│   │   ├── pipeline.py                         # Pipeline unificado (AnalysisResult, analyze_source, read_source_file)
│   │   ├── semantic.py                         # Analisador semântico básico
│   │   ├── symbol_table.py                     # Tabela de símbolos com escopos e categorias
│   │   └── token.py                            # Enum de tokens e dataclass Token
│   └── interfaces/                             # Interfaces de usuário
│       ├── __init__.py
│       ├── cli.py                              # Interface de linha de comando (CLI e modo interativo)
│       ├── gui.py                              # Interface gráfica Tkinter com fallback para Web GUI
│       └── web_gui.py                          # Interface Web Local zero-dependências (http.server)
└── tests/
    ├── test_ast_serialization_regression.py    #   4 testes: serialização AST (.to_dict / .pretty)
    ├── test_compiler.py                        #  73 testes: regressão do pipeline, CLI, GUI e tabela de símbolos
    ├── test_expressions_java.py                #  29 testes: expressões e precedência
    ├── test_java26_annotations.py              #  11 testes: annotations e ClassLiteral
    ├── test_java26_compilation_units.py        #  50 testes: pacotes, imports, módulos e unidades compactas
    ├── test_java26_expression_precedence.py    #  21 testes: 17 níveis de precedência e associatividade
    ├── test_java26_names_types.py              #  20 testes: nomes, tipos, generics e wildcards
    ├── test_java26_patterns.py                 #   7 testes: patterns, unnamed '_' e 'when' contextual
    ├── test_java26_s84_regressions.py          #   6 testes: regressões de lambdas e method references
    ├── test_java26_type_annotations.py         #  10 testes: type annotations e modificadores
    ├── test_lexer_java.py                      #  61 testes: analisador léxico Java
    ├── test_semantic_core.py                   #  14 testes: análise semântica básica e escopos
    ├── test_statements_java.py                 #  25 testes: instruções e controle de fluxo
    └── test_syntax_java.py                     #  30 testes: declarações de classes, interfaces, enums e métodos
```

---

## 4. Como Executar

### 1. Inicialização Automática com Fallback (Tkinter -> Web GUI)
Na raiz do projeto:

```bash
python -m src.main
# ou
python -m src.interfaces.gui
```
Tenta abrir a interface gráfica nativa (`tkinter`). Se o `tkinter` não estiver instalado ou não houver servidor gráfico disponível, inicia automaticamente a **Interface Web Local** no navegador padrão.

### 2. Interface Web Local Zero-Dependências
```bash
python -m src.main --web
# ou
python -m src.interfaces.web_gui
```

### 3. Modo Terminal / CLI
```bash
python -m src.main --cli
python -m src.main --cli examples/Pessoa.java
python -m src.interfaces.cli --cli examples/Pessoa.java
python -m src.main examples/ExpressoesJava.java
```

---

## 5. Como Executar os Testes

Execute a suíte completa (**361 testes, 100% aprovados**):

```bash
python -B -m unittest discover tests
```
