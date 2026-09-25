# Especificação Formal da Linguagem — compilador_av3

Este documento define formalmente os componentes léxicos, sintáticos e semânticos suportados pelo `compilador_av3`.

---

## 1. Tokens Reconhecidos

Cada token preserva seu tipo, lexema original, linha e coluna:

| Token | Padrão / Descrição | Exemplo |
| :--- | :--- | :--- |
| `KEYWORD_INT` | Palavra reservada `int` | `int` |
| `KEYWORD_STRING` | Palavra reservada `String` | `String` |
| `IDENTIFIER` | `[a-zA-Z_][a-zA-Z0-9_]*` | `total`, `_x1` |
| `NUMBER` | Sequência de dígitos decimais `[0-9]+` | `10`, `42` |
| `STRING_LITERAL` | Caracteres delimitados por aspas duplas `"..."` | `"Gustavo"`, `"ola"` |
| `ASSIGN` | Operador de atribuição `=` | `=` |
| `PLUS` | Operador aritmético de soma `+` | `+` |
| `MINUS` | Operador aritmético de subtração `-` | `-` |
| `SEMICOLON` | Delimitador de fim de comando `;` | `;` |
| `LPAREN` | Abre parênteses `(` | `(` |
| `RPAREN` | Fecha parênteses `)` | `)` |
| `EOF` | Fim de arquivo | `""` |

---

## 2. Gramática Livre de Contexto (GLC)

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

---

## 3. Tabela de Símbolos

A tabela de símbolos armazena palavras reservadas e variáveis com ordem determinística de inserção:

1. **Palavras Reservadas** (pré-carregadas conforme o Barema da AV3):
   - `int`: Categoria `"palavra_reservada"`, Tipo `"tipo"`, Linha `"-"`, Ordem `1`.
   - `String`: Categoria `"palavra_reservada"`, Tipo `"tipo"`, Linha `"-"`, Ordem `2`.
2. **Variáveis Declaradas**:
   - **Nome**: identificador da variável.
   - **Categoria**: `"variavel"`.
   - **Tipo**: `"int"` ou `"String"`.
   - **Linha**: número da linha da declaração.
   - **Ordem**: ordem sequencial de inserção (1-indexada).

> **Garantia**: Palavras reservadas e identificadores não sofrem duplicações indevidas na tabela.

---

## 4. Regras Semânticas

1. **Variável não declarada**:
   - O uso de qualquer variável em atribuições ou expressões sem declaração prévia gera erro semântico.
2. **Declaração duplicada**:
   - É proibido declarar uma variável com o mesmo nome mais de uma vez no mesmo escopo.
3. **Compatibilidade na atribuição e inicialização**:
   - Variáveis do tipo `int` só podem receber expressões que avaliem para `int`.
   - Variáveis do tipo `String` só podem receber expressões do tipo `String`.
4. **Operações aritméticas**:
   - Operadores `+` e `-` operam unicamente sobre tipos numéricos (`int`).
   - Valores do tipo `String` não são permitidos em operações aritméticas.
5. **Continuidade de análise**:
   - A análise semântica não é interrompida no primeiro erro; múltiplos erros são coletados e exibidos juntos.
