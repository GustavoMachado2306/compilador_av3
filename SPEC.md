# Especificação Formal da Linguagem — compilador_av3

Este documento define formalmente os componentes léxicos, sintáticos e semânticos suportados pelo `compilador_av3`, acompanhando a evolução incremental do projeto para a linguagem Java.

---

## 1. Fase A: Especificação Léxica (Concluída)

O analisador léxico (`src/lexer.py`) reconhece todas as construções léxicas comuns da linguagem Java:
- **Espaços e Comentários**: espaços, tabulações, quebras LF e CRLF, comentários de linha (`//`), de bloco (`/* ... */`) e Javadoc (`/** ... */`);
- **Delimitadores**: `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.`, `@`, `?`, `:`;
- **Operadores (*Maximal Munch*)**: `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`, `>>>=`, `+`, `-`, `*`, `/`, `%`, `++`, `--`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`, `!`, `&`, `|`, `^`, `~`, `<<`, `>>`, `>>>`, `->`, `::`, `...`;
- **Palavras-Chave Reservadas**: 50 palavras-chave oficiais do Java;
- **Literais**: booleanos (`true`, `false`), nulo (`null`), inteiros (dec, hex `0x`, bin `0b`, oct `0`, sufixo `L`), reais (`float`/`double`, notação científica `1e10`), `char` (`'a'`) e `String` (`"..."`).

---

## 2. Fase B: Estrutura Sintática de Arquivos Java (Concluída)

O parser (`src/parser.py`) e a AST (`src/ast_nodes.py`) reconhecem unidades de compilação completas em Java, além de manterem compatibilidade com fragmentos didáticos isolados.

### 2.1. Unidade de Compilação (`CompilationUnit`)
Uma unidade de compilação consiste em:
1. Declaração de pacote opcional (`package nome.do.pacote;`);
2. Declarações de importação zero ou mais (`import [static] caminho.[*];`);
3. Declarações de tipos zero ou mais (`class`, `interface`, `enum`);
4. Comandos de nível superior (suportados para retrocompatibilidade didática).

### 2.2. Gramática Livre de Contexto (GLC — Fase B)

```bnf
<CompilationUnit> ::= [<PackageDecl>] <ImportDecl>* <TypeDecl>* <Comando>*

<PackageDecl> ::= "package" <QualifiedName> ";"

<ImportDecl> ::= "import" ["static"] <QualifiedName> ["." "*"] ";"

<QualifiedName> ::= <IDENTIFIER> ("." <IDENTIFIER>)*

<TypeDecl> ::= <Modifiers> (<ClassDecl> | <InterfaceDecl> | <EnumDecl>)

<Modifiers> ::= ("public" | "protected" | "private" | "static" | "final"
               | "abstract" | "synchronized" | "native" | "transient"
               | "volatile" | "strictfp")*

<ClassDecl> ::= "class" <IDENTIFIER> ["extends" <TypeRef>]
                ["implements" <TypeRef> ("," <TypeRef>)*]
                "{" <ClassMember>* "}"

<InterfaceDecl> ::= "interface" <IDENTIFIER> ["<" <TypeParams> ">"]
                    ["extends" <TypeRef> ("," <TypeRef>)*]
                    "{" <InterfaceMember>* "}"

<EnumDecl> ::= "enum" <IDENTIFIER> ["implements" <TypeRef> ("," <TypeRef>)*]
               "{" [<EnumConstants>] [";" <ClassMember>*] "}"

<ClassMember> ::= <ConstructorDecl>
                | <MethodDecl>
                | <FieldDecl>
                | <TypeDecl>

<FieldDecl> ::= <Modifiers> <TypeRef> <IDENTIFIER> ["=" <Expressao>] ";"

<ConstructorDecl> ::= <Modifiers> <IDENTIFIER> "(" [<ParamList>] ")"
                      ["throws" <TypeRef> ("," <TypeRef>)*] <Block>

<MethodDecl> ::= <Modifiers> <TypeRef> <IDENTIFIER> "(" [<ParamList>] ")"
                 ["throws" <TypeRef> ("," <TypeRef>)*] (<Block> | ";")

<ParamList> ::= <Param> ("," <Param>)*
<Param> ::= <TypeRef> ["..."] <IDENTIFIER>

<TypeRef> ::= (<PrimitiveType> | <QualifiedName>) ["<" <TypeRef> ("," <TypeRef>)* ">"] ("[" "]")* ["..."]

<PrimitiveType> ::= "int" | "boolean" | "char" | "byte" | "short"
                  | "long" | "float" | "double" | "void"

<Block> ::= "{" <Statement>* "}"

<Statement> ::= <Block>
              | ";"
              | <LocalVarDecl>
              | <Assignment>
              | <IfStatement>
              | <WhileStatement>
              | <DoWhileStatement>
              | <ForStatement>
              | <EnhancedForStatement>
              | <BreakStatement>
              | <ContinueStatement>
              | <ReturnStatement>
              | <ThrowStatement>
              | <AssertStatement>
              | <TryStatement>
              | <SynchronizedStatement>
              | <ExpressionStatement>

<LocalVarDecl> ::= [<Modifiers>] <TypeRef> <IDENTIFIER> ["=" <Expressao>] ";"

<Assignment> ::= (<IDENTIFIER> | "this." <IDENTIFIER>) <AssignOp> <Expressao> ";"
<AssignOp> ::= "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=" | ">>=" | ">>>="

<IfStatement> ::= "if" "(" <Expressao> ")" <Statement> ["else" <Statement>]

<WhileStatement> ::= "while" "(" <Expressao> ")" <Statement>

<DoWhileStatement> ::= "do" <Statement> "while" "(" <Expressao> ")" ";"

<ForStatement> ::= "for" "(" [<ForInit>] ";" [<Expressao>] ";" [<Expressao>] ")" <Statement>
<ForInit> ::= <LocalVarDeclSemPontoEVirgula> | <Expressao>

<EnhancedForStatement> ::= "for" "(" [<Modifiers>] <TypeRef> <IDENTIFIER> ":" <Expressao> ")" <Statement>

<BreakStatement> ::= "break" [<IDENTIFIER>] ";"
<ContinueStatement> ::= "continue" [<IDENTIFIER>] ";"
<ReturnStatement> ::= "return" [<Expressao>] ";"
<ThrowStatement> ::= "throw" <Expressao> ";"
<AssertStatement> ::= "assert" <Expressao> [":" <Expressao>] ";"

<TryStatement> ::= "try" ["(" <ResourceList> ")"] <Block> <CatchClause>* [<FinallyBlock>]
<CatchClause> ::= "catch" "(" <TypeRef> <IDENTIFIER> ")" <Block>
<FinallyBlock> ::= "finally" <Block>
<ResourceList> ::= <Resource> (";" <Resource>)* [";"]
<Resource> ::= <LocalVarDeclSemPontoEVirgula> | <Expressao>

<SynchronizedStatement> ::= "synchronized" "(" <Expressao> ")" <Block>

<ExpressionStatement> ::= <Expressao> ";"
```

---

## 3. Fase C: Instruções e Controle de Fluxo da Linguagem Java (Concluída)

A Fase C expande o parser e a AST para reconhecer as instruções e estruturas de controle executadas dentro de métodos, construtores e blocos.

### 3.1. Nós da AST Adicionados / Adaptados

| Nó da AST | Descrição | Componentes Representados |
| :--- | :--- | :--- |
| `Block` | Bloco delimitado por chaves `{ ... }` | `statements: List[ASTNode]` |
| `LocalVariableDeclaration` | Declaração de variável local | `name`, `type_ref`, `type_name`, `modifiers`, `initializer` |
| `ExpressionStatement` | Expressão executada como comando | `expression: ASTNode` |
| `EmptyStatement` | Instrução vazia `;` | `line`, `column` |
| `IfStatement` | Condicional `if` / `else` | `condition`, `then_branch`, `else_branch` |
| `WhileStatement` | Laço `while` | `condition`, `body` |
| `DoWhileStatement` | Laço `do-while` | `body`, `condition` |
| `ForStatement` | Laço `for` tradicional | `init`, `condition`, `update`, `body` |
| `EnhancedForStatement` | Laço `for-each` | `variable`, `iterable`, `body` |
| `BreakStatement` | Desvio `break [rotulo];` | `label: Optional[str]` |
| `ContinueStatement` | Desvio `continue [rotulo];` | `label: Optional[str]` |
| `ReturnStatement` | Retorno `return [expr];` | `expression: Optional[ASTNode]` |
| `ThrowStatement` | Lançamento `throw expr;` | `expression: ASTNode` |
| `AssertStatement` | Asserção `assert cond [: msg];` | `condition`, `message` |
| `TryStatement` | Tratamento de exceções e recursos | `resources`, `body`, `catches`, `finally_block` |
| `CatchClause` | Cláusula `catch (Tipo param) { ... }` | `parameter: Parameter`, `body: Block` |
| `SynchronizedStatement` | Bloco sincronizado | `lock: ASTNode`, `body: Block` |
| `MethodCall` | Chamada de método / instanciação | `method_name`, `target`, `arguments` |
| `UnaryOp` | Operação unária prefixa ou pós-fixa | `op`, `operand`, `is_postfix` |
| `UnsupportedStatement` | Nó provisório para construções futuras | `description`, `tokens` |

---

## 4. Tabela de Símbolos e Escopos

A tabela de símbolos (`src/symbol_table.py`) suporta escopos aninhados e ordem determinística de inserção:

1. **Tipos e Palavras Reservadas Iniciais**:
   - `int`: Categoria `"palavra_reservada"`, Tipo `"tipo"`, Linha `"-"`, Ordem `1`.
   - `String`: Categoria `"tipo"`, Tipo `"tipo"`, Linha `"-"`, Ordem `2` *(String é um tipo/classe padrão do Java)*.
2. **Símbolos Declarados no Código**:
   - Classes (`categoria="classe"`)
   - Interfaces (`categoria="interface"`)
   - Enums e Constantes (`categoria="enum"`, `categoria="constante_enum"`)
   - Campos de Classe (`categoria="campo"`)
   - Construtores e Métodos (`categoria="construtor"`, `categoria="metodo"`)
   - Parâmetros Formais (`categoria="parametro"`)
   - Variáveis Locais (`categoria="variavel"`)

O isolamento lexico de escopo garante que variáveis declaradas em um método ou bloco não vazem para métodos subsequentes após a saída do escopo.

---

## 4. Fase D: Expressões Java, Precedência de Operadores e Chamadas Encadeadas (Concluída)

A Fase D introduz um analisador descendente recursivo estruturado estritamente segundo as regras de precedência e associatividade da especificação da linguagem Java (15 níveis hierárquicos).

### 4.1. Tabela de Precedência e Associatividade

| Nível | Operadores | Descrição | Associatividade | Nó da AST |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `->` | Expressões Lambda | Direita | `LambdaExpression` |
| **2** | `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `\|=`, `^=`, `<<=`, `>>=`, `>>>=` | Atribuição simples e composta | Direita | `Assignment` |
| **3** | `? :` | Operador Condicional Ternário | Direita | `ConditionalExpression` |
| **4** | `\|\|` | Disjunção Lógica (OR) | Esquerda | `BinaryOp` (`\|\|`) |
| **5** | `&&` | Conjunção Lógica (AND) | Esquerda | `BinaryOp` (`&&`) |
| **6** | `\|` | OR bit a bit (Bitwise OR) | Esquerda | `BinaryOp` (`\|`) |
| **7** | `^` | XOR bit a bit (Bitwise XOR) | Esquerda | `BinaryOp` (`^`) |
| **8** | `&` | AND bit a bit (Bitwise AND) | Esquerda | `BinaryOp` (`&`) |
| **9** | `==`, `!=` | Igualdade e Diferença | Esquerda | `BinaryOp` (`==`, `!=`) |
| **10** | `<`, `<=`, `>`, `>=`, `instanceof` | Relacionais e Comparação de Tipo | Esquerda | `BinaryOp` / `InstanceOfExpression` |
| **11** | `<<`, `>>`, `>>>` | Deslocamento de Bits (Shifts) | Esquerda | `BinaryOp` (`<<`, `>>`, `>>>`) |
| **12** | `+`, `-` | Adição e Subtração | Esquerda | `BinaryOp` (`+`, `-`) |
| **13** | `*`, `/`, `%` | Multiplicação, Divisão e Resto | Esquerda | `BinaryOp` (`*`, `/`, `%`) |
| **14** | `++`, `--`, `+`, `-`, `!`, `~`, `(Tipo)` | Unários Prefixados e Casts | Direita | `UnaryOp` / `CastExpression` |
| **15** | `.`, `()`, `[]`, `::`, `++`, `--` | Membros, Chamadas, Arrays, Referências e Pós-fixados | Esquerda | `MemberAccess`, `MethodCall`, `ArrayAccess`, `MethodReference`, `UnaryOp` |

### 4.2. Novos Nós da AST (Fase D)

| Nó da AST | Descrição | Componentes |
| :--- | :--- | :--- |
| `ConditionalExpression` | Expressão ternária `cond ? then : else` | `condition`, `then_expr`, `else_expr` |
| `MemberAccess` | Acesso qualificado a membro `alvo.membro` | `target`, `member_name` |
| `ArrayAccess` | Acesso indexado a elemento de array `arr[i]` | `array`, `index` |
| `ObjectCreationExpression` | Instanciação de objeto `new Tipo(args)` | `type_ref`, `arguments` |
| `ArrayCreationExpression` | Criação de array `new Tipo[dim1][dim2]` | `type_ref`, `dimensions`, `initializer` |
| `ArrayInitializer` | Inicializador literal `{ elem1, elem2 }` | `elements: List[ASTNode]` |
| `CastExpression` | Conversão de tipo `(Tipo) expressao` | `target_type: TypeReference`, `expression` |
| `InstanceOfExpression` | Verificação de tipo `expr instanceof Tipo` | `expression: ASTNode`, `target_type` |
| `LambdaExpression` | Expressão lambda `params -> corpo` | `parameters: List[str]`, `body`, `is_block_body` |
| `MethodReference` | Referência a método ou construtor `alvo::metodo` | `target: ASTNode`, `method_name: str` |

### 4.3. Regras de Desambiguação Sintática
- **Cast vs Expressão Parentizada**: `(Tipo) expr` é detectado verificando se os tokens entre parênteses formam um tipo válido (primitivo ou identificador com qualificadores/generics/dimensões) e se o símbolo subsequente inicia um operando unário/primário (identificador, literal, `this`, `super`, `new`, `(`, `!`, `~`). Caso contrário, é tratado como expressão com parênteses `(expr)`.
- **Lambda vs Parênteses**: `(...) ->` examina via lookahead o fechamento do parêntese e verifica a presença imediata do operador `->` (`TokenType.ARROW`).
- **Ternário vs Cabeçalho de For**: O lookahead de `_is_enhanced_for_ahead()` rastreia a profundidade de operadores ternários (`? :`), garantindo que o caractere `:` pertencente a um ternário no inicializador não seja confundido com o separador do `for-each`.

---

## 5. Tabela de Símbolos e Escopos

A tabela de símbolos (`src/symbol_table.py`) suporta escopos aninhados e ordem determinística de inserção:

1. **Tipos e Palavras Reservadas Iniciais**:
   - `int`: Categoria `"palavra_reservada"`, Tipo `"tipo"`, Linha `"-"`, Ordem `1`.
   - `String`: Categoria `"tipo"`, Tipo `"tipo"`, Linha `"-"`, Ordem `2` *(String é um tipo/classe padrão do Java)*.
2. **Símbolos Declarados no Código**:
   - Classes (`categoria="classe"`)
   - Interfaces (`categoria="interface"`)
   - Enums e Constantes (`categoria="enum"`, `categoria="constante_enum"`)
   - Campos de Classe (`categoria="campo"`)
   - Construtores e Métodos (`categoria="construtor"`, `categoria="metodo"`)
   - Parâmetros Formais e Parâmetros Lambda (`categoria="parametro"`)
   - Variáveis Locais (`categoria="variavel"`)

O isolamento léxico de escopo garante que variáveis declaradas em um método, bloco ou expressão lambda não vazem para os escopos externos.

---

## 6. Análise Semântica e Limitações Conhecidas

1. **Escopos Aninhados**: Diferenciação precisa entre campos de instância, parâmetros de método, variáveis locais e parâmetros de lambdas.
2. **Símbolos Externos e Qualificados**: Expressões qualificadas externas (ex.: `System.out.println(...)`), `this.campo`, membros de arrays (`arr.length`) e métodos de objetos não geram falsos erros de variáveis não declaradas.
3. **Detecção de Duplicidade**: Proibição de declarar duas variáveis locais, parâmetros ou campos com o mesmo nome dentro do mesmo escopo ativo.
4. **Limitações Conhecidas (Não Implementado nesta Fase)**:
   - Não há inferência de tipos completa em expressões complexas (polimorfismo e generics avançados);
   - Não há resolução de sobrecarga de métodos baseada em assinaturas de tipos;
   - Não há promoção aritmética implícita ou autoboxing/unboxing automático completo;
   - Não substitui a gramática exaustiva da especificação completa da JVM/JLS.

---

## 7. Erros Sintáticos Estruturados

Falhas sintáticas produzem mensagens no formato padronizado com linha, coluna, expectativa e símbolo encontrado:

```text
[ERRO SINTÁTICO]
Linha <L>, coluna <C>:
Era esperado <esperado>.
Encontrado: '<encontrado>'
```

Situações validadas:
- Classes sem chave de fechamento (`}`);
- Declarações de tipo sem nome (`public class {}`);
- Falta de ponto e vírgula em declarações, atribuições, retornos, throws e asserts;
- Parênteses ou chaves não balanceados em `if`, `while`, `do-while` e blocos;
- Cabeçalhos de `for` incompletos ou vazios (`for ()`);
- Condições vazias ou ausentes (`if ()`);
- Instruções `try` sem cláusula `catch`, `finally` ou recursos.

---

## 8. Gramática Normativa Java SE 26 (JLS Capítulo 19)

A partir da versão atual, o compilador adota como especificação sintática normativa o **Capítulo 19 (Syntax) da Java Language Specification (JLS), Java SE 26 Edition** (https://docs.oracle.com/javase/specs/jls/se26/html/jls-19.html), estruturado em 9 etapas de implementação (S1 a S9).

### 8.1. Etapa S1 — Nomes, Tipos, Generics e Type Annotations (Concluída)

Reconhecimento completo das produções do Grupo A (JLS §4 e §6):

1. **Nomes e Identificadores**: identificadores simples e qualificados (`a.b.c`), nomes de módulos, pacotes, tipos e membros.
2. **Tipos Primitivos e Void**: `byte`, `short`, `int`, `long`, `char`, `float`, `double`, `boolean`, `void`.
3. **Parâmetros Genéricos (`TypeParameter`)**:
   - Declaração de parâmetros genéricos com limites simples e limites de interseção: `<T extends Number & Comparable<T>>`.
   - Suporte a Type Parameters em classes, interfaces e métodos genéricos.
4. **Argumentos de Tipo (`TypeArgument`) e Wildcards (`WildcardType`)**:
   - Argumentos concretos: `<String, Integer>`.
   - Wildcards irrestritos (`<?>`), covariantes (`<? extends T>`) e contravariantes (`<? super T>`).
   - Generics aninhados em múltiplos níveis (`Map<String, List<Set<Integer>>>`).
5. **Desambiguação Léxico-Sintática de Fechamento Genérico**:
   - Algoritmo normativo de quebra determinística em fluxo de tokens para `>>` (`TokenType.RSHIFT` → `TokenType.GREATER` + `TokenType.GREATER`) e `>>>` (`TokenType.URSHIFT` → `TokenType.GREATER` + `TokenType.RSHIFT`), resolvendo o problema clássico de *Maximal Munch* em tipos genéricos aninhados.
6. **Type Annotations**:
   - Anotações opcionais em referências de tipo (`@NotNull String`, `List<@NonNull Integer>`), dimensões de array (`String @Nullable []`) e declarações de membros.
7. **Cláusula Permits**:
   - Suporte a classes seladas com lista de subtipos autorizados (`permits A, B, C`).

### 8.2. Etapa S2 — Unidades de Compilação, Pacotes, Imports e Módulos (Concluída)

Reconhecimento integral das produções do Grupo B (JLS §7 e §19):

1. **As Três Modalidades de Unidade de Compilação**:
   - `OrdinaryCompilationUnit`: pacote opcional, zero ou mais imports e zero ou mais declarações de tipos no nível superior.
   - `ModularCompilationUnit`: sequência de imports seguida obrigatoriamente por uma declaração de módulo (`ModuleDeclaration`), sem permissão para declaração de pacote.
   - `CompactCompilationUnit`: imports opcionais seguidos por membros de classe de nível superior (métodos, campos, classes internas), declarando implicitamente uma classe (`implicit_class: ClassDeclaration(name="Unnamed")`). Proíbe modificadores de acesso (`public`, `protected`, `private`, `abstract`) no nível superior, em conformidade estrita com JLS §7.3.
2. **Declarações de Pacote (`PackageDeclaration`)**:
   - Suporte a modificadores de pacote / anotações precedentes (`PackageModifier`): `@Deprecated package br.com.exemplo;`.
   - Suporte a anotações múltiplas e anotações com argumentos.
   - Diagnóstico estruturado para pacotes malformados (`package ;`, `package a..b;`, falta de `;`).
3. **As Cinco Categorias de Importação (`ImportDeclaration`)**:
   - `SingleTypeImport`: `import java.util.List;`
   - `TypeImportOnDemand`: `import java.util.*;`
   - `SingleStaticImport`: `import static java.lang.Math.PI;`
   - `StaticImportOnDemand`: `import static java.lang.Math.*;`
   - `SingleModuleImport` (Java 23+ / 26): `import module java.base;` reconhecido tanto em unidades ordinárias quanto modulares.
4. **Declaração de Módulos (`ModuleDeclaration`) e Diretivas (`ModuleDirective`)**:
   - Módulos comuns: `module com.app { ... }`.
   - Módulos abertos: `open module com.app { ... }`.
   - Módulos anotados: `@Deprecated module com.app { ... }`.
   - Diretivas estruturadas na AST:
     - `RequiresDirective`: `requires [transitive] [static] ModuleName;`
     - `ExportsDirective`: `exports PackageName [to ModuleName, ...];`
     - `OpensDirective`: `opens PackageName [to ModuleName, ...];`
     - `UsesDirective`: `uses ServiceTypeName;`
     - `ProvidesDirective`: `provides ServiceTypeName with ImplTypeName, ...;`
5. **Identificadores Contextuais**:
   - O parser reconhece contextualmente as palavras `module`, `open`, `requires`, `transitive`, `exports`, `opens`, `to`, `uses`, `provides`, `with`, permitindo seu uso livre como identificadores em classes comuns.

### 8.3. Etapa S3 — Classes, Campos, Métodos, Construtores e Inicializadores (Concluída)

Reconhecimento integral das produções do Grupo C (JLS §8 e §19) e JEP 513 (*Flexible Constructor Bodies*):

1. **Correção Normativa de Unidades Compactas (`CompactCompilationUnit`)**:
   - Conformidade estrita com JLS §7.3: exige obrigatoriamente a presença de ao menos uma declaração de método (`MethodDeclaration`).
   - Elementos anteriores ao primeiro método são restritos a `ClassMemberDeclarationNoMethod` (campos e tipos aninhados). Inicializadores de instância, estáticos e construtores são estritamente rejeitados com erro sintático se posicionados antes do primeiro método.
2. **Declarações de Campos (`FieldDeclaration`)**:
   - Suporte a declaradores múltiplos (`VariableDeclaratorList`): `int a, b = 2, c[];`.
   - Identificador de declarador (`VariableDeclaratorId`) suportando identificador simples, identificador não nomeado `_` (Java 21+) e dimensões adicionais de array em declaradores individuais.
   - Modificadores de campo (`public`, `private`, `protected`, `static`, `final`, `transient`, `volatile`) e anotações.
3. **Cabeçalhos e Declarações de Métodos (`MethodDeclaration`)**:
   - Suporte a parâmetros de recepção (`ReceiverParameter` — JLS §8.4.1): `{Annotation} UnannType [Identifier .] this` posicionado exclusivamente como primeiro parâmetro formal.
   - Dimensões de array pós-parênteses no retorno (`int metodo()[][]`).
   - Parâmetros formais (`FormalParameter`), parâmetros de aridade variável (`VariableArityParameter` / varargs `...`) e modificadores de parâmetros (`final`, anotações).
   - Cláusula `throws` com múltiplos tipos de exceção e corpo opcional (métodos abstratos e nativos terminados em `;`).
4. **Construtores e Invocação Explícita (`ConstructorDeclaration`, `ExplicitConstructorInvocation`)**:
   - Type parameters em construtores genéricos: `<T> MeuConstrutor(T valor)`.
   - Suporte a `ReceiverParameter` no construtor.
   - Invocação alternativa de construtor (`AlternateConstructorInvocation`): `this(...)` e `<TypeArgs> this(...)`.
   - Invocação de construtor da superclasse (`SuperclassConstructorInvocation`): `super(...)`, `<TypeArgs> super(...)` e qualificado `expressao.super(...)`.
5. **Flexible Constructor Bodies (JLS §8.8.7 e JEP 513)**:
   - O corpo do construtor (`ConstructorBody`) é estruturado em três seções normativas: `prologue` (comandos antes da chamada de construtor), `constructor_invocation` (chamada `this(...)` ou `super(...)`) e `epilogue` (comandos posteriores).
   - Validação sintática: no máximo uma invocação explícita de construtor é admitida; invocações de construtor são estritamente proibidas dentro de blocos aninhados (`{ super(); }`) ou estruturas de controle de fluxo (`if`, `while`, `for`, `try`).
6. **Inicializadores de Instância e Estáticos**:
   - `InstanceInitializer`: blocos `{ ... }` declarados no corpo da classe.
   - `StaticInitializer`: blocos `static { ... }` declarados no corpo da classe.
7. **Classes Aninhadas e Validação Semântica**:
   - Declarações aninhadas de classes com resolução recursiva de escopo;
   - Registro na tabela de símbolos de múltiplos declaradores de campo e construtores sem duplicidade indevida;
   - Exclusão do `receiver_parameter` da contagem de argumentos formais regulares.

### 8.4. Etapa S3.1 — Auditoria e Correção de Tipos de Declaradores, Retornos e Unnamed Variables (Concluída)

Refinamentos de conformidade com a JLS §8.3, §8.4.5, §8.8.7, §10.2 e JEP 456 / JEP 513:

1. **Tipos Efetivos de Declaradores de Campo (JLS §8.3 e §10.2)**:
   - O tipo efetivo de cada campo individual combina as dimensões do tipo base (TypeReference.array_dimensions) e as dimensões adicionais declaradas no identificador (VariableDeclaratorId.dims).
   - A AST preserva tanto o tipo comum da declaração (ield.type_ref) quanto as dimensões de cada declarador (decl.dims), permitindo consultar diretamente o tipo efetivo individual (decl.effective_type).
   - A Tabela de Símbolos registra o tipo efetivo individual (ex.: uffer como int[] e historico como int[][] em int[] buffer, historico[];).
2. **Tipos Efetivos de Retorno de Métodos (JLS §8.4.5 e §10.2)**:
   - Combina as dimensões de Result (
eturn_type.array_dimensions) e as dimensões posteriores ao MethodDeclarator (method.dims).
   - O tipo efetivo pode ser consultado diretamente via method.effective_return_type (ex.: int[][] terceiro()[][] possui tipo efetivo int[][][][]).
   - Métodos pretty() e 	o_dict() preservam todas as dimensões estruturalmente.
3. **Restrição Contextual de Underscore em Campos (JLS §8.3 e JEP 456)**:
   - O identificador isolado _ é rejeitado semanticamente como nome válido de campo (class A { int _; } e int x, _ = 0;), sem que seja registrado na tabela de símbolos.
   - Variáveis não nomeadas legítimas são estritamente preservadas nos contextos autorizados pela JLS: variáveis locais em métodos/blocos, recursos de try, parâmetros de catch (catch (Exception _)) e laços for-each (or (int _ : lista)), sem poluição da tabela de símbolos nem permissão de referência posterior.
4. **Validação do Early Construction Context (JLS §8.8.7 e JEP 513)**:
   - Em construtores com invocação explícita de super(...) ou 	his(...), as instruções do prólogo e os argumentos da invocação ocorrem no *early construction context*.
   - É rejeitado com erro semântico qualquer uso de 	his, 	his.campo, 	his.metodo() ou acesso/atribuição a campos e métodos de instância no prólogo.
   - Construtores sem invocação explícita realizam a chamada implicitamente no início, não constituindo contexto precoce de construção.
