# compilador_av3

Compilador e analisador didático desenvolvido em Python para a avaliação AV3 da disciplina de Compiladores. O projeto está passando por uma expansão incremental para suportar as construções mais comuns da linguagem Java, preservando a arquitetura em camadas e o funcionamento tanto em terminal (CLI) quanto via interface gráfica (Tkinter).

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

## 2. Status Atual da Evolução para Java

O projeto adota uma abordagem incremental sólida, sem bibliotecas externas:

- **Fase A — Analisador Léxico (Concluída)**:
  - Suporte completo a comentários: linha (`//`), bloco (`/* ... */`) e Javadoc (`/** ... */`);
  - Delimitadores Java: `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.`, `@`, `?`, `:`;
  - Operadores de tamanho variável (*Maximal Munch*): `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`, `!`, `&`, `|`, `^`, `~`, `<<`, `>>`, `>>>`, `<<=`, `>>=`, `>>>=`, `->`, `::`, `...`;
  - Palavras-chave: 50 palavras reservadas do Java (`class`, `public`, `return`, etc.), além dos literais `true`, `false` e `null`;
  - Números: decimais, hexadecimais (`0x`), binários (`0b`), octais (`0`), underscores válidos (`1_000_000`), sufixos `L`/`l`, números `float` e `double`, notação científica (`1e10`);
  - Textos e Caracteres: literais `char` (`'a'`), strings com escapes válidos (`\n`, `\t`, `\"`, `\uXXXX`) e detecção de literais malformados.

- **Fase B — Estrutura de Arquivos Java (Concluída)**:
  - Unidade de compilação completa (`CompilationUnit`) com pacote e imports opcionais;
  - Declarações de pacote (`package exemplo.modelo;`);
  - Declarações de importação simples, com wildcard e estáticas (`import java.util.List;`, `import java.util.*;`, `import static java.lang.Math.PI;`);
  - Classes com modificadores, `extends` e `implements` (`public class Pessoa extends Base implements Runnable`);
  - Interfaces simples e genéricas (`public interface Conversor<T>`);
  - Enums com constantes e membros (`public enum Status { NOVO, EM_ANDAMENTO }`);
  - Campos com tipos primitivos, de referência, arrays e inicializadores;
  - Construtores com parâmetros e corpo `{ ... }`;
  - Métodos com tipo de retorno, parâmetros, cláusula `throws` e corpo ou assinatura abstrata;
  - Parâmetros com tipos, dimensões de arrays e varargs (`String... args`);
  - Blocos de métodos (`Block`) com balanceamento estrito de chaves e instruções de retorno (`return`);
  - Tabela de símbolos com escopos hierárquicos e classificação coerente de `String` como tipo.

- **Fase C — Instruções e Controle de Fluxo da Linguagem Java (Concluída)**:
  - Blocos de código aninhados `{ ... }` com escopos locais de variáveis;
  - Declarações de variáveis locais (`LocalVariableDeclaration`), com ou sem inicializador e modificadores (ex.: `final`);
  - Instruções de atribuição simples e compostas (`=`, `+=`, `-=`, `*=`, `/=`, `%=`, etc.);
  - Chamadas de métodos como comandos (`System.out.println(...)`, `recurso.executar()`, chamadas encadeadas);
  - Instrução vazia `;` (`EmptyStatement`);
  - Retorno com e sem valor (`return;`, `return expr;`);
  - Condicionais: `if`, `if/else`, `if/else if/else`, condicionais aninhadas e comandos de ramo único sem chaves;
  - Laços de repetição: `while`, `do/while`, `for` tradicional (inicialização, condição e atualização) e `for` aprimorado (*enhanced for* / *for-each* com coleções e arrays);
  - Desvios incondicionais: `break` e `continue`, com e sem rótulos;
  - Lançamento de exceções: `throw expr;`;
  - Tratamento de exceções: `try/catch/finally`, múltiplos blocos `catch` e `try` com recursos (*try-with-resources*);
  - Asserções: `assert condicao [: mensagem];`;
  - Sincronização: blocos `synchronized (lock) { ... }`;
  - Suporte a operadores relacionais (`<`, `<=`, `>`, `>=`, `==`, `!=`), lógicos (`&&`, `||`, `!`) e unários (`++`, `--`) para condições e atualizações de laços;
  - Representação hierárquica legível na AST via `.pretty()`.

- **Fase D — Expressões Java, Precedência de Operadores e Chamadas Encadeadas (Concluída)**:
  - Hierarquia completa de 15 níveis de precedência e associatividade estrita do Java;
  - Operadores binários associativos à esquerda: aditivos (`+`, `-`), multiplicativos (`*`, `/`, `%`), deslocamento (`<<`, `>>`, `>>>`), relacionais (`<`, `<=`, `>`, `>=`), igualdade (`==`, `!=`), bit a bit (`&`, `^`, `|`) e lógicos (`&&`, `||`);
  - Operadores associativos à direita: atribuições simples e compostas (`=`, `+=`, `-=`, etc.) e operador condicional ternário (`?:`);
  - Expressões ternárias aninhadas (`cond ? a : cond2 ? b : c`) sem conflito com o separador `:` do `for` aprimorado;
  - Operadores unários prefixados (`++`, `--`, `+`, `-`, `!`, `~`) e pós-fixados (`++`, `--`);
  - Expressões primárias e encadeadas: chamadas encadeadas (`obj.metodo().outro()`), acesso a membros (`this.campo`, `alvo.propriedade`) e indexação de arrays unidimensionais e multidimensionais (`matriz[i][j]`);
  - Criação de objetos (`new Classe(args)`) e criação e inicialização de arrays (`new int[10]`, `new String[2][3]`, `new int[] {1, 2}`, `{1, 2, 3}`);
  - Operador `instanceof` para verificação de tipo (`objeto instanceof String`);
  - Casts explícitos (`(int) valor`, `(String) objeto`, `(double) a / b`) com desambiguação sintática determinística em relação a expressões parentizadas `(expr)`;
  - Expressões lambda (`x -> x * 2`, `(a, b) -> a + b`, `() -> executar()`, `x -> { return x + 1; }`) com corpo como expressão ou bloco;
  - Referências a métodos e construtores (`System.out::println`, `String::valueOf`, `String::new`, `objeto::executar`).

- **Expansão Normativa Java SE 26 (JLS Capítulo 19)**:
  - Documentação da matriz de cobertura em `docs/JAVA26_SYNTAX_COVERAGE.md` (206 produções mapeadas);
  - **Etapa S1 — Nomes, Tipos, Generics e Type Annotations (Concluída)**:
    - 100% das produções do Grupo A (JLS §4 e §6) implementadas e cobertas por testes (`tests/test_java26_names_types.py`);
    - Desambiguação léxico-sintática determinística de fechamento de generics aninhados (`>>` e `>>>`);
    - Parâmetros genéricos com limites de interseção (`<T extends Number & Comparable<T>>`), wildcards irrestritos e delimitados (`? extends T`, `? super T`), métodos genéricos e Type Annotations (`@NotNull String`).
  - **Etapa S2 — Unidades de Compilação, Pacotes, Imports e Módulos (Concluída)**:
    - 100% das produções do Grupo B (JLS §7 e §19) implementadas e cobertas por testes (`tests/test_java26_compilation_units.py`);
    - Suporte às 3 modalidades de unidades de compilação: `OrdinaryCompilationUnit`, `ModularCompilationUnit` e `CompactCompilationUnit` (com classe declarada implicitamente);
    - Anotações de pacote (`@Deprecated package ...`);
    - As 5 categorias de imports da JLS: `SingleTypeImport`, `TypeImportOnDemand`, `SingleStaticImport`, `StaticImportOnDemand` e `SingleModuleImport` (`import module java.base;`);
    - Declaração de módulos (`ModuleDeclaration`) e diretivas normativas: `RequiresDirective` (`transitive`, `static`), `ExportsDirective` (`to`), `OpensDirective` (`to`), `UsesDirective` e `ProvidesDirective` (`with`);
    - Suporte a palavras-chave contextuais sem poluição da tabela de palavras reservadas globais.
  - **Etapa S3 — Classes, Campos, Métodos, Construtores e Inicializadores (Concluída)**:
    - 100% das produções do Grupo C (JLS §8 e §19) implementadas e cobertas por testes (`tests/test_java26_class_members.py`);
    - Correção normativa de `CompactCompilationUnit` exigindo ao menos uma declaração de método e restringindo elementos pré-método a `ClassMemberDeclarationNoMethod`;
    - Declarações múltiplas de variáveis em campos (`VariableDeclaratorList`) e identificadores não nomeados (`_`);
    - Parâmetros de recepção (`ReceiverParameter` — `this`), dimensões no retorno (`int m()[][]`), varargs (`...`) e modificadores de parâmetros;
    - Construtores genéricos com type parameters (`<T> Nome(...)`);
    - Implementação de *Flexible Constructor Bodies* (JLS §8.8.7 e JEP 513) dividindo o corpo em `prologue`, `constructor_invocation` (`this(...)` / `super(...)`) e `epilogue`;
    - Inicializadores de instância (`{ ... }`) e estáticos (`static { ... }`);
    - Classes aninhadas com análise de escopo recursivo.

- **Fases Futuras (Próximos Passos)**:
  - Etapa S4: Interfaces, enums e records (JLS §8.9, §8.10, §9);
  - Etapa S5: Annotations e declarações de tipos anotados (JLS §9.6, §9.7);
  - Etapa S6: Blocos, instruções e controle de fluxo avançado (JLS §14);
  - Etapa S7: Switch aprimorado e Pattern Matching (JLS §14.11, §14.30);
  - Etapa S8: Expressões completas e primárias modernas (JLS §15);
  - Etapa S9: Unidades compactas, classes implícitas e recuperação de erros (JLS §7.3).

---

## 3. Estrutura do Projeto

```text
compilador_av3/
├── README.md
├── SPEC.md
├── examples/
│   ├── exemplo_fase_a.java
│   ├── Pessoa.java               # Exemplo de classe Java completa (Fase B)
│   ├── FluxoJava.java            # Exemplo com instruções e controle de fluxo (Fase C)
│   ├── ExpressoesJava.java       # Exemplo com expressões, precedência, arrays e casts (Fase D)
│   └── exemplo_classes_s3.java   # Exemplo completo da Etapa S3 (construtores flexíveis, inicializadores, etc.)
├── src/
│   ├── __init__.py
│   ├── token.py                  # Enum de tokens e dataclass Token
│   ├── lexer.py                  # Analisador léxico Java completo (Fase A)
│   ├── symbol_table.py           # Tabela de símbolos com escopos e categorias
│   ├── parser.py                 # Analisador sintático de comandos, tipos e expressões (Fases B, C, D e Etapas S1-S3)
│   ├── ast_nodes.py              # Nós da AST com pretty-printing hierárquico
│   ├── semantic.py               # Validador semântico com suporte a escopos locais e expressões
│   ├── main.py                   # Pipeline unificado e CLI (arquitetura tripla)
│   ├── gui.py                    # Interface gráfica Tkinter com fallback automático
│   └── web_gui.py                # Interface Web Local zero-dependências (http.server)
└── tests/
    ├── test_compiler.py                 # 73 testes: testes didáticos e de robustez (regressão)
    ├── test_lexer_java.py               # 58 testes: suíte de testes dedicada ao léxico Java
    ├── test_syntax_java.py              # 26 testes: suíte de testes de sintaxe e declarações
    ├── test_statements_java.py          # 25 testes: suíte de testes de controle de fluxo
    ├── test_expressions_java.py         # 29 testes: suíte de testes de expressões e precedência
    ├── test_java26_names_types.py       # 20 testes: suíte da Etapa S1 (JLS §4 e §6)
    ├── test_java26_compilation_units.py # 50 testes: suíte da Etapa S2 (JLS §7 e §19)
    └── test_java26_class_members.py     # 87 testes: suíte da Etapa S3 (JLS §8, JEP 513 e S3.1) (JLS §8 e JEP 513)
```

---

## 4. Como Executar (Arquitetura Tripla: Tkinter, Web Local e CLI)

### 1. Inicialização Automática com Fallback (Tkinter -> Web GUI)
Na raiz do projeto (`compilador_av3/`), execute:

```bash
python -m src.main
# ou
python -m src.gui
```
Tenta abrir a interface gráfica nativa (`tkinter`). Se o `tkinter` não estiver instalado ou não houver servidor gráfico disponível, inicia automaticamente a **Interface Web Local** no navegador padrão.

### 2. Interface Web Local Zero-Dependências
Para abrir diretamente no navegador web (Windows, Linux ou macOS sem depender do `tkinter`):

```bash
python -m src.main --web
# ou
python -m src.web_gui
```

### 3. Modo Terminal / CLI
Para executar diretamente no terminal (inclusive via SSH/terminal puro):

```bash
python -m src.main --cli
python -m src.main --cli examples/ExpressoesJava.java
python -m src.main <caminho_do_arquivo.java>
```

Exemplo com arquivo Java contendo expressões e controle de fluxo da Fase D:
```bash
python -m src.main examples/ExpressoesJava.java
```

#### Recursos da Interface Gráfica:
- **Editor de Código**: Área de texto com numeração de linhas sincronizada, rolagem e atalhos (`Ctrl+O` para abrir, `Ctrl+S` para salvar, `F5` para analisar, `Ctrl+L` para limpar).
- **Aba Tokens**: Visualização tabular com `#`, `Tipo`, `Lexema`, `Linha` e `Coluna` de cada token.
- **Aba Tabela de Símbolos**: Relação tabular com `Ordem`, `Identificador`, `Categoria`, `Tipo` e `Linha`.
- **Aba AST**: Visualização hierárquica da árvore sintática gerada (`CompilationUnit`, `IfStatement`, `ForStatement`, `ConditionalExpression`, etc.).
- **Aba Semântica**: Relatório da validação semântica com prevenção de falsos erros para bibliotecas externas.
- **Aba Erros**: Diagnóstico consolidado com mensagens amigáveis e estruturadas.

---

## 5. Como Executar os Testes

Execute a suíte completa de testes automatizados (**368 testes ao todo, 100% aprovados**):

```bash
python -m unittest discover tests
```

Ou execute cada suíte individualmente:

```bash
python -m unittest -v tests/test_compiler.py                 # 73 testes
python -m unittest -v tests/test_lexer_java.py               # 58 testes
python -m unittest -v tests/test_syntax_java.py              # 26 testes
python -m unittest -v tests/test_statements_java.py          # 25 testes
python -m unittest -v tests/test_expressions_java.py         # 29 testes
python -m unittest -v tests/test_java26_names_types.py       # 20 testes
python -m unittest -v tests/test_java26_compilation_units.py # 50 testes
python -m unittest -v tests/test_java26_class_members.py     # 87 testes
```
