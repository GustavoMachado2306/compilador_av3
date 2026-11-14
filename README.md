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
  - **Etapa S3 & S3.1 — Classes, Campos, Métodos, Construtores e Inicializadores (Concluída)**:
    - Produções do Grupo C (JLS §8 e §19) e JEP 513 implementadas e cobertas por testes (`tests/test_java26_class_members.py`);
    - Correção normativa de `CompactCompilationUnit` exigindo ao menos uma declaração de método e restringindo elementos pré-método a `ClassMemberDeclarationNoMethod`;
    - Declarações múltiplas de variáveis em campos (`VariableDeclaratorList`) e identificadores não nomeados (`_`);
    - Parâmetros de recepção (`ReceiverParameter` — `this`), dimensões no retorno (`int m()[][]`), varargs (`...`) e modificadores de parâmetros;
    - Construtores genéricos com type parameters (`<T> Nome(...)`);
    - Implementação de *Flexible Constructor Bodies* (JLS §8.8.7 e JEP 513) dividindo o corpo em `prologue`, `constructor_invocation` (`this(...)` / `super(...)`) e `epilogue`, com validação semântica de *early construction context*;
    - Inicializadores de instância (`{ ... }`) e estáticos (`static { ... }`);
    - Classes aninhadas com análise de escopo recursivo.
  - **Etapa S4 — Interfaces Normais, Enums e Records (Concluída)**:
    - Produções centrais do Grupo D (JLS §8.9, §8.10, §9.1–§9.5 e §19, exceto `@interface` da Etapa S5) cobertas por 4 novas suítes dedicadas (`tests/test_java26_interfaces.py`, `tests/test_java26_enums.py`, `tests/test_java26_records.py`, `tests/test_java26_record_constructors.py`);
    - Interfaces normais (`InterfaceDeclaration`, `InterfaceBody`, `InterfaceExtends`, `InterfacePermits`, constantes implícitas `public static final` e métodos `abstract`, `default`, `static` e `private`);
    - Enums completos (`EnumDeclaration`, `EnumBody`, `EnumConstantList`, argumentos, anotações, *trailing comma*, `EnumConstantBody` específico da constante e `EnumBodyDeclarations` com construtores `private`);
    - Records (`RecordDeclaration`, `RecordHeader`, `RecordComponent`, `VariableArityRecordComponent`, identificador contextual `record` e restrições de campos/métodos);
    - Construtores de records (`NormalCanonicalConstructor`, `CompactConstructorDeclaration`, `NonCanonicalRecordConstructor` e detecção de canônico implícito).
  - **Etapa S5 — Annotations e Annotation Interfaces (Concluída)**:
    - Produções do Grupo E (JLS §9.6, §9.7, §4.11 e §19) implementadas e cobertas por 4 novas suítes (`tests/test_java26_annotation_interfaces.py`, `tests/test_java26_annotations.py`, `tests/test_java26_type_annotations.py`, `tests/test_java26_annotation_semantics.py`);
    - Declarações `@interface` (`AnnotationInterfaceDeclaration`, `AnnotationInterfaceBody`, `AnnotationInterfaceElementDeclaration`, `AnnotationDefaultValue`, constantes, dimensões pós-parênteses e tipos aninhados);
    - Annotations normais (`NormalAnnotation` com `ElementValuePairList`/`ElementValuePair`), simples (`SingleElementAnnotation`), marcadoras (`MarkerAnnotation`), inicializadores `{...}` (`ElementValueArrayInitializer`) e literais de classe (`ClassLiteral`: `String.class`, `int.class`, `void.class`, `String[].class`);
    - *Type Annotations* completos (generics, wildcards, `Outer.@B Inner`, arrays multidimensionais anotados, casts, `instanceof`, `new @Ann`, varargs `...`, `ReceiverParameter`, `TypeParameter` e separação pré/pós-modificadores);
    - Validações semânticas de `@Target`, `@Repeatable` (e contrato do container), elementos obrigatórios, chaves duplicadas/desconhecidas, constantes em tempo de compilação, compatibilidade de tipos, ciclos de `@interface` e auditoria herdada S4 (métodos abstratos em `enum` e accessors explícitos de `record`).
    - Não realiza resolução de `@interface` em arquivos/JARs externos fora da unidade atual (além das anotações padrão integradas do JDK).
  - **Etapa S6 — Blocos, Declarações Locais e Instruções Completas (Concluída)**:
    - Produções do Grupo G (JLS §14 e Capítulo 19) cobertas por 8 novas suítes dedicadas (`tests/test_java26_blocks.py`, `tests/test_java26_local_declarations.py`, `tests/test_java26_local_types.py`, `tests/test_java26_control_statements.py`, `tests/test_java26_loops_labels.py`, `tests/test_java26_try_statements.py`, `tests/test_java26_switch_statements.py`, `tests/test_java26_statement_semantics.py`);
    - `Block`, `BlockStatement`, `LocalClassOrInterfaceDeclaration` (`class`, `interface`, `enum`, `record` locais + rejeição de `@interface` local), `LocalVariableDeclaration`, `LocalVariableType` (`var` com todas as restrições JLS §14.4.1 e variáveis `_` não nomeadas JEP 456);
    - `Statement`, `StatementNoShortIf` (resolução formal de *dangling `else`*), `StatementExpression` rigorosa, `LabeledStatement`, `EmptyStatement`, `AssertStatement`, `ThrowStatement`, `SynchronizedStatement`, `ReturnStatement`, `BreakStatement`, `ContinueStatement`, laços (`while`, `do/while`, `for` com listas múltiplas `StatementExpressionList`, `enhanced for` com `var` e `_`);
    - `TryStatement` / `TryWithResourcesStatement` (`ResourceSpecification` com `;` final opcional, recursos por declaração/var/referência Java 9+), `CatchClause` com `CatchType` multi-catch, `SwitchStatement` com grupos `:` e switch rules `->`, `CaseConstantList`, `case null`, `case null, default` e `YieldStatement` com `SwitchExpression` auxiliar mínima (patterns/guards na Etapa S7 e expressão switch *poly-expression* completa na S8).
  - **Etapa S7 & Auditoria S7.1 — Patterns, Pattern Matching, Switch Moderno e Separação de Preview (Concluída)**:
    - Produções estáveis do Grupo H (JLS §§6.3, 14.11, 14.30, 15.20.2 e 15.28.1) cobertas por 9 suítes dedicadas (`tests/test_java26_patterns.py`, `tests/test_java26_record_patterns.py`, `tests/test_java26_instanceof_patterns.py`, `tests/test_java26_pattern_scope.py`, `tests/test_java26_switch_patterns.py`, `tests/test_java26_pattern_dominance.py`, `tests/test_java26_switch_exhaustiveness.py`, `tests/test_java26_pattern_semantics.py`, `tests/test_java26_pattern_preview_separation.py`);
    - `Pattern`, `TypePattern` (com `@Annotation`, `final`, genéricos/arrays e `_`), `RecordPattern` (aninhamento, `var`, genéricos, aridade e proibições de annotations sobre o tipo do record), `ComponentPatternList`, `ComponentPattern`, `MatchAllPattern` (`_`), `Guard` (`when` estritamente contextual), `PatternCaseLabel` e `PatternInstanceOfExpression` (preservando `InstanceOfExpression`);
    - Escopo sensível ao fluxo (*flow-scoping* JLS §6.3) em `!`, `&&`, `||`, `?:`, `if`/`else`, `while`, `for`, `do-while`, `switch` (sem vazar para a tabela de símbolos global), regras de dominância recursiva (JLS §14.30.3 / §14.11.1) e exaustividade incluindo hierarquias `sealed` multinível e decomposição recursiva de records;
    - Separação estrita de preview JEP 530 (desabilitado por padrão via `enable_preview_primitive_patterns=False`): rejeita tipos primitivos em `instanceof`, `switch` labels, componentes primitivos de `RecordPattern` (`Ponto(int x, int y)`), `instanceof` clássico com primitivo e seletores/constantes `boolean`/`long`/`float`/`double`, mantendo `var` e `_` em `RecordPattern` mesmo para campos primitivos; a flag opcional `enable_preview_primitive_patterns=True` habilita apenas um subconjunto parcial de preview (sem matriz integral JLS §5.7.1–§5.7.2 nem exaustividade por faixa numérica); registro honesto de tipos externos em `unresolved_checks` e auditoria herdada S6 (`break rotulado;` em blocos).
  - **Etapa S8 — Expressões Completas, Inferência de Tipos e Switch Expressions (Concluída)**:
    - Cobertura integral do Grupo I e integração final de `SwitchExpression` do Grupo H (JLS §15) validada por 12 suítes dedicadas (`109` novos testes: `tests/test_java26_expression_precedence.py`, `tests/test_java26_arithmetic_expressions.py`, `tests/test_java26_assignment_expressions.py`, `tests/test_java26_casts_conversions.py`, `tests/test_java26_method_invocations.py`, `tests/test_java26_object_creation.py`, `tests/test_java26_array_expressions.py`, `tests/test_java26_lambda_expressions.py`, `tests/test_java26_method_references.py`, `tests/test_java26_poly_expressions.py`, `tests/test_java26_switch_expression_typing.py`, `tests/test_java26_expression_semantics.py`);
    - Todos os 17 níveis de precedência e associatividade, promoções numéricas unária/binária, estreitamento constante, verificação de *l-values* modificáveis e atribuições compostas;
    - Casts primitivos, de referência e de interseção (`(A & B) expr`), invocação com herança/sobrecarga/genéricos explícitos (`Tipo.<T>m(...)`), diamond `<>`, `outer.new`, `AnonymousClassDeclaration` e criação/indexação de arrays (JLS §15.10.1);
    - Todas as formas de `LambdaExpression` (com captura efetivamente final JLS §15.27.2), todas as 5 formas de `MethodReference` (incluindo `int[]::new`) e tipagem polimórfica (*target-typing* e unificação) para ternários, lambdas, method references e `SwitchExpression` (`->` e `yield`), com registro honesto de referências externas em `unresolved_checks`.

- **Etapa S9 — Auditoria Final de Conformidade Java SE 26 (Concluída)**:
  - Auditoria cruzada da matriz de cobertura (`docs/JAVA26_SYNTAX_COVERAGE.md`), dos diagnósticos e de cenários negativos/positivos entre escopos, tipos, expressões, OOP e preview;
  - Correções pontuais para `synchronized` (rejeita primitivo/`void`), `throw` (exige subtipo de `Throwable` quando conhecido) e `var` (rejeita inicializador `void`), além da suíte `tests/test_java26_s9_audit_regressions.py`;
  - **Configuração Preview**: recursos preview da JEP 530 (*primitive patterns*) ficam desabilitados por padrão (`enable_preview_primitive_patterns=False`) e podem ser habilitados explicitamente apenas para o subconjunto parcial documentado;
  - **Limitações conhecidas**: análise de unidade única (tipos externos não embutidos são registrados em `unresolved_checks`), sem JLS §16 (*definite assignment* integral), sem JLS §18 (inferência genérica completa), sem captura integral de wildcards (JLS §5.1.10), sem sistema completo de warnings e sem execução/runtime Java.

---

## 3. Estrutura do Projeto

```text
compilador_av3/
├── README.md
├── SPEC.md
├── docs/
│   └── JAVA26_SYNTAX_COVERAGE.md
├── examples/
│   ├── exemplo_fase_a.java
│   ├── Pessoa.java                             # Exemplo de classe Java completa (Fase B)
│   ├── FluxoJava.java                          # Exemplo com instruções e controle de fluxo (Fase C)
│   ├── ExpressoesJava.java                     # Exemplo com expressões, precedência, arrays e casts (Fase D)
│   ├── exemplo_classes_s3.java                 # Exemplo completo da Etapa S3 (construtores flexíveis, inicializadores, etc.)
│   ├── exemplo_interfaces_enums_records_s4.java# Exemplo integrado da Etapa S4 (interfaces, enums, records e construtores)
│   ├── exemplo_annotations_s5.java             # Exemplo integrado da Etapa S5 (@interface, annotations, @Repeatable e type annotations)
│   ├── exemplo_instrucoes_s6.java              # Exemplo integrado da Etapa S6 (blocos, var, tipos locais, try-with-resources, switch e yield)
│   ├── exemplo_pattern_matching_s7.java        # Exemplo integrado da Etapa S7 (TypePattern, RecordPattern, when, sealed e switch exaustivo)
│   └── exemplo_expressoes_s8.java              # Exemplo integrado da Etapa S8 (precedência, casts, sobrecarga, lambdas, method refs, switch expression)
├── src/
│   ├── __init__.py
│   ├── main.py                                 # Entrypoint unificado (compatível com CLI, GUI e imports públicos)
│   ├── compiler/                               # Núcleo do compilador
│   │   ├── __init__.py
│   │   ├── token.py                            # Enum de tokens e dataclass Token
│   │   ├── lexer.py                            # Analisador léxico Java completo (Fase A)
│   │   ├── symbol_table.py                     # Tabela de símbolos com escopos e categorias
│   │   ├── parser.py                           # Analisador sintático (Fases B–D e Etapas S1–S8)
│   │   ├── ast_nodes.py                        # Nós da AST com pretty-printing hierárquico e to_dict()
│   │   ├── semantic.py                         # Analisador semântico básico (escopos, tipos e verificações essenciais)
│   │   └── pipeline.py                         # Pipeline unificado (AnalysisResult, analyze_source, analyze_sources)
│   └── interfaces/                             # Interfaces de usuário
│       ├── __init__.py
│       ├── cli.py                              # Interface de linha de comando (CLI e modo interativo)
│       ├── gui.py                              # Interface gráfica Tkinter com fallback automático
│       └── web_gui.py                          # Interface Web Local zero-dependências (http.server)
└── tests/
    ├── test_compiler.py                        # 73 testes: testes didáticos e de robustez (regressão)
    ├── test_lexer_java.py                      # 58 testes: suíte de testes dedicada ao léxico Java
    ├── test_syntax_java.py                     # 26 testes: suíte de testes de sintaxe e declarações
    ├── test_statements_java.py                 # 25 testes: suíte de testes de controle de fluxo
    ├── test_expressions_java.py                # 29 testes: suíte de testes de expressões e precedência
    ├── test_java26_names_types.py              # 20 testes: suíte da Etapa S1 (JLS §4 e §6)
    ├── test_java26_compilation_units.py        # 50 testes: suíte da Etapa S2 (JLS §7 e §19)
    ├── test_java26_class_members.py            # 93 testes: suíte da Etapa S3 e S3.1 (JLS §8 e JEP 513)
    ├── test_java26_interfaces.py               # 28 testes: suíte da Etapa S4 — Interfaces Normais (JLS §9.1–§9.5)
    ├── test_java26_enums.py                    # 26 testes: suíte da Etapa S4 — Enums e Corpos de Constantes (JLS §8.9)
    ├── test_java26_records.py                  # 24 testes: suíte da Etapa S4 — Records e Componentes (JLS §8.10)
    ├── test_java26_record_constructors.py      # 22 testes: suíte da Etapa S4 — Construtores de Records (JLS §8.10.4)
    ├── test_java26_annotation_interfaces.py    # 17 testes: suíte da Etapa S5 — Declarações @interface e Elementos (JLS §9.6)
    ├── test_java26_annotations.py              # 11 testes: suíte da Etapa S5 — Marker, Single-Element, Normal e ClassLiteral (JLS §9.7)
    ├── test_java26_type_annotations.py         # 10 testes: suíte da Etapa S5 — Type Annotations e Separação de Modificadores (JLS §4.11)
    ├── test_java26_annotation_semantics.py     # 12 testes: suíte da Etapa S5 — Semântica (@Target/@Repeatable/Constantes) e Auditoria S4
    ├── test_java26_blocks.py                   # 11 testes: suíte da Etapa S6 — Blocos e Escopo Local (JLS §14.2)
    ├── test_java26_local_declarations.py       # 17 testes: suíte da Etapa S6 — Declarações Locais, Arrays, 'var' e '_' (JLS §14.4)
    ├── test_java26_local_types.py              # 11 testes: suíte da Etapa S6 — Tipos Locais class/interface/enum/record (JLS §14.3)
    ├── test_java26_control_statements.py       # 12 testes: suíte da Etapa S6 — ExpressionStatement, Dangling Else, Assert, Yield (JLS §14)
    ├── test_java26_loops_labels.py             #  9 testes: suíte da Etapa S6 — Laços Tradicionais/Aprimorados e Rótulos (JLS §14.7, §14.12–§14.16)
    ├── test_java26_try_statements.py           #  7 testes: suíte da Etapa S6 — Try/Catch/Multicatch e Try-with-Resources (JLS §14.20)
    ├── test_java26_switch_statements.py        #  9 testes: suíte da Etapa S6 — Switch Statements ':' / '->', case null e Yield (JLS §14.11)
    ├── test_java26_statement_semantics.py      #  8 testes: suíte da Etapa S6 — Semântica Contextual e Integração S1–S6
    ├── test_java26_patterns.py                 #  7 testes: suíte da Etapa S7 — Patterns, Unnamed '_' e 'when' contextual (JLS §14.30)
    ├── test_java26_record_patterns.py          #  9 testes: suíte da Etapa S7 — Record Patterns, aridade, aninhamento e genéricos
    ├── test_java26_instanceof_patterns.py      #  6 testes: suíte da Etapa S7 — PatternInstanceOfExpression vs clássico (JLS §15.20.2)
    ├── test_java26_pattern_scope.py            #  8 testes: suíte da Etapa S7 — Flow-Scoping (JLS §6.3) em expressões e instruções
    ├── test_java26_switch_patterns.py          #  7 testes: suíte da Etapa S7 — Switch com patterns, guards 'when' e case null
    ├── test_java26_pattern_dominance.py        #  5 testes: suíte da Etapa S7 — Regras de dominância em switch e records (JLS §14.11.1 / §14.30.3)
    ├── test_java26_switch_exhaustiveness.py         #  6 testes: suíte da Etapa S7 — Exaustividade sealed, enums e records (JLS §14.11.2 / §15.28.1)
    ├── test_java26_pattern_semantics.py             #  6 testes: suíte da Etapa S7 — Auditoria S6, Preview JEP 530 e Fronteira Externa
    ├── test_java26_pattern_preview_separation.py    # 10 testes: suíte S7.1 — Separação Estável Java SE 26 vs Preview JEP 530
    ├── test_java26_expression_precedence.py         # 21 testes: suíte da Etapa S8/S8.1 — 17 Níveis de Precedência e Associatividade (JLS §15)
    ├── test_java26_operator_semantics.py            # 31 testes: suíte da Etapa S8.1 — Tipos Resultantes e Compatibilidade de Operadores
    ├── test_java26_primitive_conversions.py         #  8 testes: suíte da Etapa S8.2 — Conversões Primitivas e Promoções (JLS §5.1.1–§5.1.4, §5.6)
    ├── test_java26_reference_conversions.py         #  9 testes: suíte da Etapa S8.2 — Conversões de Referência, Classes e Arrays (JLS §5.1.5, §5.5)
    ├── test_java26_boxing_unboxing.py               #  9 testes: suíte da Etapa S8.2 — Boxing, Unboxing e Widening (JLS §5.1.7, §5.1.8)
    ├── test_java26_cast_expressions.py              #  8 testes: suíte da Etapa S8.2 — Casts Primitivos, Referência, Interseção e Instanceof
    ├── test_java26_constant_narrowing.py            #  9 testes: suíte da Etapa S8.2 — Narrowing Constante Implícito (JLS §5.2)
    ├── test_java26_field_access.py                  #  9 testes: suíte da Etapa S8.3 — Acesso a Campos, this/super, Estático e Encadeado
    ├── test_java26_array_access.py                  #  7 testes: suíte da Etapa S8.3 — Indexação 1D/ND, Índices e .length
    ├── test_java26_method_invocation.py             #  7 testes: suíte da Etapa S8.3 — Invocações, Contexto Estático, void e Encadeamento
    ├── test_java26_array_creation.py                #  6 testes: suíte da Etapa S8.3 — Criação de Arrays, Dimensões e Inicializadores
    ├── test_java26_s82_regressions.py               #  6 testes: suíte da Etapa S8.3 — Regressões S8.2 (Unboxing/Narrowing e Wildcards)
    ├── test_java26_arithmetic_expressions.py        # 10 testes: suíte da Etapa S8 — Promoção Numérica e Operadores Unários/Binários
    ├── test_java26_assignment_expressions.py        #  9 testes: suíte da Etapa S8 — Atribuições, Estreitamento Constante e L-Values
    ├── test_java26_casts_conversions.py             #  9 testes: suíte da Etapa S8 — Casts Primitivos, Referência e Interseção (JLS §15.16)
    ├── test_java26_method_invocations.py            # 10 testes: suíte da Etapa S8 — Métodos, Herança, Sobrecarga e Genéricos Explícitos
    ├── test_java26_object_creation.py               # 11 testes: suíte da Etapa S8/S8.3 — Diamond <>, Outer.new, Construtores e Classes Anônimas
    ├── test_java26_array_expressions.py             #  9 testes: suíte da Etapa S8 — Criação JLS §15.10.1, Inicializadores e .length
    ├── test_java26_lambda_expressions.py            # 14 testes: suíte da Etapa S8/S8.4 — Lambdas, Parâmetros, Blocos e Retornos
    ├── test_java26_method_references.py             # 13 testes: suíte da Etapa S8/S8.4 — As 5 Formas de Method Reference (incl. int[]::new)
    ├── test_java26_functional_interfaces.py         #  8 testes: suíte da Etapa S8.4 — Interfaces Funcionais (JLS §9.8) e @FunctionalInterface
    ├── test_java26_lambda_typing.py                 #  7 testes: suíte da Etapa S8.4 — Target Typing, Sobrecargas e Incompatibilidades
    ├── test_java26_lambda_capture.py                #  6 testes: suíte da Etapa S8.4 — Captura Efetivamente Final (JLS §15.27.2)
    ├── test_java26_s84_regressions.py               #  6 testes: suíte da Etapa S8.4 — Regressões e Integração Lambda/MethodRef
    ├── test_java26_poly_expressions.py              #  9 testes: suíte da Etapa S8 — Poly-Expressions, Ternários e Retorno/Atribuição
    ├── test_java26_switch_expression_typing.py      #  9 testes: suíte da Etapa S8 — SwitchExpression, yield, Exaustividade e LUB
    ├── test_java26_switch_expressions.py            #  9 testes: suíte da Etapa S8.5 — Switch Expressions (JLS §15.28), yield e Exaustividade
    ├── test_java26_switch_expression_types.py       #  8 testes: suíte da Etapa S8.5 — Unificação e Compatibilidade de Tipos em Switch Expressions
    ├── test_java26_class_literals.py                #  7 testes: suíte da Etapa S8.5 — Class Literals (.class), Outer.this e Outer.super
    ├── test_java26_s85_regressions.py               #  8 testes: suíte da Etapa S8.5 — Auditoria Final e Regressões S8.1–S8.5
    ├── test_java26_s9_audit_regressions.py          #  6 testes: suíte da Etapa S9 — Auditoria Final de Conformidade
    └── test_java26_expression_semantics.py          #  8 testes: suíte da Etapa S8 — Integração S1–S8, Preview JEP 530 e unresolved_checks
```

---

## 4. Como Executar (Arquitetura Tripla: Tkinter, Web Local e CLI)

### 1. Inicialização Automática com Fallback (Tkinter -> Web GUI)
Na raiz do projeto (`compilador_av3/`), execute:

```bash
python -m src.main
# ou
python -m src.interfaces.gui
```
Tenta abrir a interface gráfica nativa (`tkinter`). Se o `tkinter` não estiver instalado ou não houver servidor gráfico disponível, inicia automaticamente a **Interface Web Local** no navegador padrão.

### 2. Interface Web Local Zero-Dependências
Para abrir diretamente no navegador web (Windows, Linux ou macOS sem depender do `tkinter`):

```bash
python -m src.main --web
# ou
python -m src.interfaces.web_gui
```

### 3. Modo Terminal / CLI
Para executar diretamente no terminal (inclusive via SSH/terminal puro):

```bash
python -m src.main --cli
python -m src.main --cli examples/ExpressoesJava.java
python -m src.interfaces.cli --cli examples/ExpressoesJava.java
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

Execute a suíte completa de testes automatizados (**978 testes ao todo, 100% aprovados**):

```bash
python -m unittest discover tests
```

Ou execute cada suíte individualmente:

```bash
python -m unittest -v tests/test_compiler.py                        # 73 testes
python -m unittest -v tests/test_lexer_java.py                      # 58 testes
python -m unittest -v tests/test_syntax_java.py                     # 26 testes
python -m unittest -v tests/test_statements_java.py                 # 25 testes
python -m unittest -v tests/test_expressions_java.py                # 29 testes
python -m unittest -v tests/test_java26_names_types.py              # 20 testes
python -m unittest -v tests/test_java26_compilation_units.py        # 50 testes
python -m unittest -v tests/test_java26_class_members.py            # 93 testes (87 S3 + 6 S3.1)
python -m unittest -v tests/test_java26_interfaces.py               # 28 testes
python -m unittest -v tests/test_java26_enums.py                    # 26 testes
python -m unittest -v tests/test_java26_records.py                  # 24 testes
python -m unittest -v tests/test_java26_record_constructors.py      # 22 testes
python -m unittest -v tests/test_java26_annotation_interfaces.py    # 17 testes
python -m unittest -v tests/test_java26_annotations.py              # 11 testes
python -m unittest -v tests/test_java26_type_annotations.py         # 10 testes
python -m unittest -v tests/test_java26_annotation_semantics.py     # 12 testes
python -m unittest -v tests/test_java26_blocks.py                   # 11 testes
python -m unittest -v tests/test_java26_local_declarations.py       # 17 testes
python -m unittest -v tests/test_java26_local_types.py              # 11 testes
python -m unittest -v tests/test_java26_control_statements.py       # 12 testes
python -m unittest -v tests/test_java26_loops_labels.py             #  9 testes
python -m unittest -v tests/test_java26_try_statements.py           #  7 testes
python -m unittest -v tests/test_java26_switch_statements.py        #  9 testes
python -m unittest -v tests/test_java26_statement_semantics.py      #  8 testes
python -m unittest -v tests/test_java26_patterns.py                 #  7 testes
python -m unittest -v tests/test_java26_record_patterns.py          #  9 testes
python -m unittest -v tests/test_java26_instanceof_patterns.py      #  6 testes
python -m unittest -v tests/test_java26_pattern_scope.py            #  8 testes
python -m unittest -v tests/test_java26_switch_patterns.py          #  7 testes
python -m unittest -v tests/test_java26_pattern_dominance.py        #  5 testes
python -m unittest -v tests/test_java26_switch_exhaustiveness.py    #  6 testes
python -m unittest -v tests/test_java26_pattern_semantics.py             #  6 testes
python -m unittest -v tests/test_java26_pattern_preview_separation.py    # 10 testes
python -m unittest -v tests/test_java26_expression_precedence.py         # 21 testes
python -m unittest -v tests/test_java26_operator_semantics.py            # 31 testes
python -m unittest -v tests/test_java26_primitive_conversions.py         #  8 testes
python -m unittest -v tests/test_java26_reference_conversions.py         #  9 testes
python -m unittest -v tests/test_java26_boxing_unboxing.py               #  9 testes
python -m unittest -v tests/test_java26_cast_expressions.py              #  8 testes
python -m unittest -v tests/test_java26_constant_narrowing.py            #  9 testes
python -m unittest -v tests/test_java26_field_access.py                  #  9 testes
python -m unittest -v tests/test_java26_array_access.py                  #  7 testes
python -m unittest -v tests/test_java26_method_invocation.py             #  7 testes
python -m unittest -v tests/test_java26_array_creation.py                #  6 testes
python -m unittest -v tests/test_java26_s82_regressions.py               #  6 testes
python -m unittest -v tests/test_java26_arithmetic_expressions.py        # 10 testes
python -m unittest -v tests/test_java26_assignment_expressions.py        #  9 testes
python -m unittest -v tests/test_java26_casts_conversions.py             #  9 testes
python -m unittest -v tests/test_java26_method_invocations.py            # 10 testes
python -m unittest -v tests/test_java26_object_creation.py               # 11 testes
python -m unittest -v tests/test_java26_array_expressions.py             #  9 testes
python -m unittest -v tests/test_java26_lambda_expressions.py            # 14 testes
python -m unittest -v tests/test_java26_method_references.py             # 13 testes
python -m unittest -v tests/test_java26_functional_interfaces.py         #  8 testes
python -m unittest -v tests/test_java26_lambda_typing.py                 #  7 testes
python -m unittest -v tests/test_java26_lambda_capture.py                #  6 testes
python -m unittest -v tests/test_java26_s84_regressions.py               #  6 testes
python -m unittest -v tests/test_java26_poly_expressions.py              #  9 testes
python -m unittest -v tests/test_java26_switch_expression_typing.py      #  9 testes
python -m unittest -v tests/test_java26_switch_expressions.py            #  9 testes
python -m unittest -v tests/test_java26_switch_expression_types.py       #  8 testes
python -m unittest -v tests/test_java26_class_literals.py                #  7 testes
python -m unittest -v tests/test_java26_s85_regressions.py               #  8 testes
python -m unittest -v tests/test_java26_s9_audit_regressions.py          #  6 testes
python -m unittest -v tests/test_java26_expression_semantics.py          #  8 testes
```
