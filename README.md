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

- **Fases Futuras (Próximos Passos)**:
  - Fase E: Ampliação semântica, verificação de tipos e inferência estrita de tipos Java;
  - Fase F: Resolução de sobrecarga de métodos e polimorfismo complexo.

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
│   └── ExpressoesJava.java       # Exemplo com expressões, precedência, arrays e casts (Fase D)
├── src/
│   ├── __init__.py
│   ├── token.py                  # Enum de tokens e dataclass Token
│   ├── lexer.py                  # Analisador léxico Java completo (Fase A)
│   ├── symbol_table.py           # Tabela de símbolos com escopos e categorias
│   ├── parser.py                 # Analisador sintático de comandos, tipos e expressões (Fases B, C e D)
│   ├── ast_nodes.py              # Nós da AST com pretty-printing hierárquico
│   ├── semantic.py               # Validador semântico com suporte a escopos locais e expressões
│   ├── main.py                   # Pipeline unificado e CLI (arquitetura tripla)
│   ├── gui.py                    # Interface gráfica Tkinter com fallback automático
│   └── web_gui.py                # Interface Web Local zero-dependências (http.server)
└── tests/
    ├── test_compiler.py          # 62 testes: testes didáticos e de robustez (regressão)
    ├── test_lexer_java.py        # 42 testes: suíte de testes dedicada à Fase A do Java
    ├── test_syntax_java.py       # 26 testes: suíte de testes dedicada à Fase B do Java
    ├── test_statements_java.py   # 24 testes: suíte de testes dedicada à Fase C do Java
    └── test_expressions_java.py  # 29 testes: suíte de testes dedicada à Fase D do Java
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

Execute a suíte completa de testes automatizados (**183 testes ao todo, 100% aprovados**):

```bash
python -m unittest discover tests
```

Ou execute cada suíte individualmente:

```bash
python -m unittest -v tests/test_compiler.py         # 62 testes
python -m unittest -v tests/test_lexer_java.py       # 42 testes
python -m unittest -v tests/test_syntax_java.py      # 26 testes
python -m unittest -v tests/test_statements_java.py  # 24 testes
python -m unittest -v tests/test_expressions_java.py # 29 testes
```
