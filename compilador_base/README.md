# Base do Analisador/Compilador — AV3

Projeto didático para a AV3 de Compiladores. A base analisa um subconjunto propositalmente pequeno de Java e cobre o fluxo:

**arquivo fonte → lexer → tokens → parser → AST → tabela de símbolos → semântica**

## Como executar

Na pasta raiz:

```bash
python -m src.main examples/exemplo.java
```

Teste também:

```bash
python -m src.main examples/erro_semantico.java
```

## Escopo inicial

- declaração `int` e `String`;
- identificadores;
- números inteiros;
- strings simples;
- atribuição;
- `+` e `-`;
- `;`;
- tabela de símbolos;
- AST em texto;
- checagem básica de variável não declarada;
- checagem básica de compatibilidade de tipos.

Este projeto **não tenta implementar Java completo**. A ideia é manter o trabalho pequeno e alinhado ao barema.

## Estratégia de Git recomendada

`main` deve ser a versão integrada e sempre executável.

Branches sugeridas:

- `feature/lexer` — integrante 1: tokens e regras léxicas;
- `feature/symbol-table` — integrante 2: tabela de símbolos;
- `feature/parser-ast` — integrante 3: GLC, parser e AST;
- `feature/semantic` — integrante 4: validação semântica.

Cada integrante trabalha em **uma base comum**, não em um compilador separado. Cada branch deve entregar uma melhoria isolada e os merges devem ocorrer na `main` somente depois de testar.
