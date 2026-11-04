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
