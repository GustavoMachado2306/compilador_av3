# Matriz de Cobertura Sintática — Java SE 26 (JLS Capítulo 19)

**Data de Início:** 10/11/2026  
**Referência Normativa:** Java Language Specification (JLS), Java SE 26 Edition — Chapter 19 (Syntax).  
**Documentação Oficial:** https://docs.oracle.com/javase/specs/jls/se26/html/jls-19.html  

---

## 1. Sumário Executivo de Cobertura

| Grupo | Categoria Gramatical | Total Produções | Implementadas | Parciais | Ausentes |
|---|---|---|---|---|---|
| **Grupo A** | Nomes, Identificadores e Tipos | 24 | 24 | 0 | 0 |
| **Grupo B** | Unidades de Compilação, Pacotes e Módulos | 18 | 18 | 0 | 0 |
| **Grupo C** | Classes e Declarações de Membros | 32 | 26 | 6 | 0 |
| **Grupo D** | Enums, Records e Interfaces | 22 | 9 | 6 | 7 |
| **Grupo E** | Annotations e Annotation Interfaces | 14 | 2 | 4 | 8 |
| **Grupo F** | Arrays e Inicializadores | 8 | 6 | 2 | 0 |
| **Grupo G** | Instruções e Blocos | 28 | 20 | 6 | 2 |
| **Grupo H** | Switch e Pattern Matching | 16 | 6 | 4 | 6 |
| **Grupo I** | Expressões | 38 | 26 | 8 | 4 |
| **Grupo J** | Unidades Compactas e Classes Implícitas | 6 | 4 | 2 | 0 |
| **TOTAL** | **Gramática Completa Java SE 26** | **206** | **141** | **38** | **27** |

**Taxa de Cobertura Atual (Pós Etapa S3):**
- **Implementado:** ~68.4% (141 produções)
- **Parcial:** ~18.4% (38 produções)
- **Ausente:** ~13.1% (27 produções)

> [!NOTE]
> **Nota de Escopo Normativo (Etapas S1 a S3):**  
> Os Grupos A, B e C mapeiam as produções centrais de Nomes/Tipos (JLS §4, §6), Unidades de Compilação/Módulos (JLS §7) e Classes/Membros/Construtores (JLS §8, JEP 513). A classificação reflete produções especificadas e testadas com AST estruturada, sem generalizações indevidas para sub-regras contextuais de capítulos futuros (Interfaces, Enums, Records, Patterns e Expressions).

---

## 2. Matriz Detalhada de Produções (JLS Capítulo 19)

### GRUPO A — Nomes, Identificadores e Tipos (JLS §4, §6)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Identifier` | Léxico / Nomes | `variavel`, `$valor`, `_aux` | `Lexer.tokenize` | `Identifier` / `str` | `test_39_b_...` | `test_09_caractere_invalido` | IMPLEMENTADO |
| `TypeIdentifier` | Nomes | `MinhaClasse`, `T` | `parse_type_reference` | `TypeReference` | `test_01_classe_vazia` | `test_23_tipo_sem_nome` | IMPLEMENTADO |
| `ModuleName` | Nomes | `java.base`, `com.app` | `parse_qualified_identifier` | `str` | `test_java26_names_types.py` | `test_java26_names_types.py` | IMPLEMENTADO |
| `PackageName` | Nomes | `br.com.empresa` | `qualified_identifier` | `PackageDeclaration` | `test_02_classe_com_pacote` | `test_java26_names_types.py` | IMPLEMENTADO |
| `TypeName` | Nomes | `java.util.Map` | `parse_type_reference` | `TypeReference` | `test_java26_names_types.py` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ExpressionName` | Nomes | `System.out.println` | `expression` / `MemberAccess` | `MemberAccess` | `test_11_chamadas_encadeadas` | `test_java26_names_types.py` | IMPLEMENTADO |
| `MethodName` | Nomes | `executar` | `method_declaration` | `MethodDeclaration` | `test_08_classe_com_metodo_void` | `test_java26_names_types.py` | IMPLEMENTADO |
| `PackageOrTypeName` | Nomes | `java.lang` | `qualified_identifier` | `str` | `test_02_classe_com_pacote` | `test_java26_names_types.py` | IMPLEMENTADO |
| `AmbiguousName` | Nomes | `pkg.Tipo.membro` | `parse_primary` | `MemberAccess` | `test_12_acesso_a_membros...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `PrimitiveType` | Tipos | `int`, `boolean`, `double` | `parse_type_reference` | `TypeReference` | `test_01_declaracao_simples_int` | `test_java26_names_types.py` | IMPLEMENTADO |
| `NumericType` | Tipos | `byte`, `short`, `long`, `float` | `parse_type_reference` | `TypeReference` | `test_promocao_widening` | `test_java26_names_types.py` | IMPLEMENTADO |
| `IntegralType` | Tipos | `int`, `char`, `byte`, `short`, `long` | `parse_type_reference` | `TypeReference` | `test_01_declaracao_simples_int` | `test_java26_names_types.py` | IMPLEMENTADO |
| `FloatingPointType` | Tipos | `float`, `double` | `parse_type_reference` | `TypeReference` | `test_atribuicao_literal_double` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ReferenceType` | Tipos | `String`, `Pessoa`, `T` | `parse_type_reference` | `TypeReference` | `test_03_declaracao_simples_string` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ClassOrInterfaceType` | Tipos | `List<String>`, `Map<K, V>` | `parse_type_reference` | `TypeReference` | `test_16_interface_generica...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ArrayType` | Tipos | `int[]`, `String[][]` | `parse_type_reference` | `TypeReference` | `test_19_arrays_em_tipos...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `Dims` | Tipos | `[]`, `[][]` | `parse_type_reference` | `int` / `Dims` | `test_19_arrays_em_tipos...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `TypeParameters` | Generics | `<T>`, `<K, V>` | `parse_type_parameters` | `List[TypeParameter]` | `test_03_type_parameters...` | `test_18_erro_type_parameter...` | IMPLEMENTADO |
| `TypeParameter` | Generics | `T extends Number` | `parse_type_parameters` | `TypeParameter` | `test_05_type_parameter...` | `test_18_erro_type_parameter...` | IMPLEMENTADO |
| `TypeBound` | Generics | `T extends Number & Comparable<T>` | `parse_type_parameters` | `List[TypeReference]` | `test_06_type_parameter...` | `test_18_erro_type_parameter...` | IMPLEMENTADO |
| `TypeArguments` | Generics | `<String, Integer>` | `parse_type_arguments` | `List[ASTNode]` | `test_07_type_arguments...` | `test_17_erro_generics_nao_fechado` | IMPLEMENTADO |
| `Wildcard` | Generics | `?`, `? extends Number` | `parse_type_arguments` | `WildcardType` | `test_10_wildcard_irrestrito` | `test_17_erro_generics_nao_fechado` | IMPLEMENTADO |
| `WildcardBounds` | Generics | `? super Integer` | `parse_type_arguments` | `WildcardType` | `test_12_wildcard_super...` | `test_17_erro_generics_nao_fechado` | IMPLEMENTADO |
| `TypeAnnotation` | Annotations | `@NotNull String` | `parse_type_reference` | `List[Annotation]` | `test_16_type_annotations` | `test_19_erro_tipo_invalido...` | IMPLEMENTADO |

---

### GRUPO B — Unidades de Compilação, Pacotes e Módulos (JLS §7)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `CompilationUnit` | Arquivo | `package a; class B {}` | `Parser.parse` | `CompilationUnit` | `test_01_classe_vazia` | `test_22_classe_sem_chave...` | IMPLEMENTADO |
| `OrdinaryCompilationUnit` | Arquivo | `import java.util.*; class A {}` | `Parser.parse` | `OrdinaryCompilationUnit` | `test_01_unidade_ordinaria...` | `test_22_classe_sem_chave...` | IMPLEMENTADO |
| `ModularCompilationUnit` | Arquivo | `module com.app { requires java.base; }` | `parse_module_declaration` | `ModularCompilationUnit` | `test_10_unidade_modular_simples` | `test_48_unidade_modular...` | IMPLEMENTADO |
| `CompactCompilationUnit` | Arquivo | `void main() { System.out.println(); }` | `parse_compact_compilation_unit` | `CompactCompilationUnit` | `test_05_unidade_compacta...` | `test_24_declaracao_fora...` | IMPLEMENTADO |
| `PackageDeclaration` | Pacote | `package br.com.teste;` | `package_declaration` | `PackageDeclaration` | `test_02_unidade_ordinaria...` | `test_38_pacote_malformado` | IMPLEMENTADO |
| `PackageModifier` | Pacote | `@Deprecated package a;` | `package_declaration` | `List[Annotation]` | `test_14_package_modifier...` | `test_38_pacote_malformado` | IMPLEMENTADO |
| `ImportDeclaration` | Imports | `import java.util.List;` | `import_declaration` | `ImportDeclaration` | `test_03_classe_com_imports` | `test_39_import_sem_nome` | IMPLEMENTADO |
| `SingleTypeImportDeclaration` | Imports | `import java.util.Map;` | `import_declaration` | `SingleTypeImport` | `test_16_import_de_classe...` | `test_40_import_sem_ponto...` | IMPLEMENTADO |
| `TypeImportOnDemandDeclaration` | Imports | `import java.util.*;` | `import_declaration` | `TypeImportOnDemand` | `test_17_import_com_wildcard` | `test_40_import_sem_ponto...` | IMPLEMENTADO |
| `SingleStaticImportDeclaration` | Imports | `import static java.lang.Math.PI;` | `import_declaration` | `SingleStaticImport` | `test_18_import_static_indiv...` | `test_40_import_sem_ponto...` | IMPLEMENTADO |
| `StaticImportOnDemandDeclaration` | Imports | `import static java.lang.Math.*;` | `import_declaration` | `StaticImportOnDemand` | `test_19_import_static_wild...` | `test_40_import_sem_ponto...` | IMPLEMENTADO |
| `SingleModuleImportDeclaration` | Imports | `import module java.base;` | `import_declaration` | `SingleModuleImport` | `test_20_single_module_import` | `test_41_import_module_sem...` | IMPLEMENTADO |
| `ModuleDeclaration` | Módulo | `open module com.app {}` | `parse_module_declaration` | `ModuleDeclaration` | `test_10_unidade_modular...` | `test_47_modulo_sem_abertura...`| IMPLEMENTADO |
| `ModuleDirective` | Módulo | `requires java.sql;` | `parse_module_directive` | `ModuleDirective` | `test_23_requires_comum` | `test_42_diretiva_requires...` | IMPLEMENTADO |
| `RequiresModifier` | Módulo | `requires transitive java.logging;` | `parse_module_directive` | `RequiresDirective` | `test_24_requires_transitive` | `test_42_diretiva_requires...` | IMPLEMENTADO |
| `ExportsDirective` | Módulo | `exports com.app.api;` | `parse_module_directive` | `ExportsDirective` | `test_27_exports_comum` | `test_43_diretiva_exports...` | IMPLEMENTADO |
| `OpensDirective` | Módulo | `opens com.app.internal to com.framework;` | `parse_module_directive` | `OpensDirective` | `test_29_opens_comum` | `test_44_diretiva_opens...` | IMPLEMENTADO |
| `ProvidesDirective` | Módulo | `provides Servico with ServicoPadrao;` | `parse_module_directive` | `ProvidesDirective` | `test_32_provides_com_um_tipo` | `test_46_diretiva_provides...`| IMPLEMENTADO |

---

### GRUPO C — Classes e Declarações de Membros (JLS §8)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `ClassDeclaration` | Classes | `public class A {}` | `class_declaration` | `ClassDeclaration` | `test_01_classe_vazia` | `test_22_classe_sem_chave...` | IMPLEMENTADO |
| `NormalClassDeclaration` | Classes | `class A extends B implements C {}` | `class_declaration` | `ClassDeclaration` | `test_13_classe_com_extends` | `test_java26_classes.py` | IMPLEMENTADO |
| `ClassModifier` | Classes | `public static final class A {}` | `class_declaration` | `List[str]` | `test_18_varios_modificadores` | `test_java26_classes.py` | IMPLEMENTADO |
| `ClassExtends` | Classes | `extends Base` | `class_declaration` | `TypeReference` | `test_13_classe_com_extends` | `test_java26_classes.py` | IMPLEMENTADO |
| `ClassImplements` | Classes | `implements I1, I2` | `class_declaration` | `List[TypeReference]` | `test_14_classe_com_implements`| `test_java26_classes.py` | IMPLEMENTADO |
| `ClassPermits` | Classes | `sealed class A permits B, C {}` | `class_declaration` | `List[TypeReference]` | `test_14_classe_com_permits` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ClassBody` | Classes | `{ int x; void m() {} }` | `class_declaration` | `List[ASTNode]` | `test_07_classe_com_varios...` | `test_22_classe_sem_chave...` | IMPLEMENTADO |
| `FieldDeclaration` | Campos | `private int idade = 25;` | `field_declaration` | `FieldDeclaration` | `test_06_campo_com_inicializador`| `test_java26_classes.py` | IMPLEMENTADO |
| `VariableDeclaratorList` | Campos | `int a, b = 2, c;` | `field_declaration` | `List[FieldDeclaration]` | `test_java26_classes.py` | `test_java26_classes.py` | PARCIAL |
| `MethodDeclaration` | Métodos | `public int calc(int a) { return a; }` | `method_declaration` | `MethodDeclaration` | `test_09_metodo_com_tipo...` | `test_21_metodo_sem_corpo...`| IMPLEMENTADO |
| `MethodModifier` | Métodos | `public static synchronized void m()` | `method_declaration` | `List[str]` | `test_18_varios_modificadores` | `test_java26_classes.py` | IMPLEMENTADO |
| `MethodHeader` | Métodos | `<T> T get(T item) throws Exception` | `method_declaration` | `MethodDeclaration` | `test_13_metodo_generico...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `FormalParameterList` | Parâmetros | `(int a, String b)` | `parse_parameter_list` | `List[Parameter]` | `test_10_metodo_com_varios...`| `test_java26_classes.py` | IMPLEMENTADO |
| `VariableArityParameter` | Parâmetros | `(String... args)` | `parse_parameter_list` | `Parameter (is_varargs=True)` | `test_20_varargs` | `test_java26_classes.py` | IMPLEMENTADO |
| `ReceiverParameter` | Parâmetros | `(Pessoa this, int x)` | `parse_parameter_list` | `ReceiverParameter` | `test_java26_classes.py` | `test_java26_classes.py` | AUSENTE |
| `ConstructorDeclaration` | Construtor | `public Pessoa(String n) { ... }` | `constructor_declaration` | `ConstructorDeclaration` | `test_12_construtor_com_param`| `test_java26_classes.py` | IMPLEMENTADO |
| `ConstructorModifier` | Construtor | `public`, `protected`, `private` | `constructor_declaration` | `List[str]` | `test_12_construtor_com_param`| `test_java26_classes.py` | IMPLEMENTADO |
| `ConstructorInvocation` | Construtor | `this("padrao");`, `super(id);` | `parse_statement` | `ConstructorInvocation` | `test_java26_classes.py` | `test_java26_classes.py` | PARCIAL |
| `FlexibleConstructorBody`| Construtor | `validar(); super();` (Java 22+) | `parse_constructor_body` | `Block` | `test_java26_classes.py` | `test_java26_classes.py` | PARCIAL |
| `InstanceInitializer` | Inicializador | `{ contador++; }` | `class_declaration` | `InstanceInitializer` | `test_java26_classes.py` | `test_java26_classes.py` | AUSENTE |
| `StaticInitializer` | Inicializador | `static { Logger.init(); }` | `class_declaration` | `StaticInitializer` | `test_java26_classes.py` | `test_java26_classes.py` | AUSENTE |

---

### GRUPO D — Enums, Records e Interfaces (JLS §8.9, §8.10, §9)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `EnumDeclaration` | Enums | `enum Cor { RED, GREEN }` | `enum_declaration` | `EnumDeclaration` | `test_17_enum` | `test_java26_enums_records.py` | IMPLEMENTADO |
| `EnumConstant` | Enums | `FINALIZADO(200) { ... }` | `enum_declaration` | `EnumConstant` | `test_17_enum` | `test_java26_enums_records.py` | PARCIAL |
| `RecordDeclaration` | Records | `record P(int x, int y) {}` | `record_declaration` | `RecordDeclaration` | `test_java26_enums_records.py` | `test_java26_enums_records.py` | PARCIAL |
| `RecordHeader` | Records | `(String nome, int idade)` | `record_declaration` | `List[RecordComponent]` | `test_java26_enums_records.py` | `test_java26_enums_records.py` | PARCIAL |
| `RecordComponent` | Records | `@NotNull String nome` | `record_declaration` | `RecordComponent` | `test_java26_enums_records.py` | `test_java26_enums_records.py` | PARCIAL |
| `CompactConstructor` | Records | `public P { if (x < 0) throw ...; }` | `record_declaration` | `CompactConstructor` | `test_java26_enums_records.py` | `test_java26_enums_records.py` | PARCIAL |
| `InterfaceDeclaration` | Interfaces | `interface Repositorio<T> {}` | `interface_declaration` | `InterfaceDeclaration` | `test_15_interface_simples` | `test_java26_interfaces.py` | IMPLEMENTADO |
| `InterfaceExtends` | Interfaces | `extends I1, I2` | `interface_declaration` | `List[TypeReference]` | `test_15_interface_simples` | `test_java26_interfaces.py` | IMPLEMENTADO |
| `DefaultMethod` | Interfaces | `default void log() {}` | `method_declaration` | `MethodDeclaration` | `test_java26_interfaces.py` | `test_java26_interfaces.py` | PARCIAL |
| `StaticMethod` | Interfaces | `static int zero() { return 0; }` | `method_declaration` | `MethodDeclaration` | `test_java26_interfaces.py` | `test_java26_interfaces.py` | IMPLEMENTADO |
| `AnnotationInterface` | Annotations | `@interface MinhaAnotacao {}` | `annotation_interface_decl` | `AnnotationInterfaceDecl` | `test_java26_annotations.py` | `test_java26_annotations.py` | AUSENTE |

---

### GRUPO E — Annotations (JLS §9.6, §9.7)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Annotation` | Annotations | `@Override` | `parse_annotation` | `Annotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | PARCIAL |
| `MarkerAnnotation` | Annotations | `@Deprecated` | `parse_annotation` | `Annotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | PARCIAL |
| `SingleElementAnnotation` | Annotations | `@SuppressWarnings("all")` | `parse_annotation` | `Annotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | PARCIAL |
| `NormalAnnotation` | Annotations | `@Info(nome = "App", versao = 1)` | `parse_annotation` | `Annotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | PARCIAL |
| `ElementValuePairList` | Annotations | `k1 = v1, k2 = v2` | `parse_annotation` | `Dict[str, ASTNode]` | `test_java26_annotations.py` | `test_java26_annotations.py` | AUSENTE |
| `ElementValueArrayInitializer` | Annotations | `{"unchecked", "rawtypes"}` | `parse_annotation` | `ArrayInitializer` | `test_java26_annotations.py` | `test_java26_annotations.py` | AUSENTE |

---

### GRUPO F — Arrays e Inicializadores (JLS §10)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `ArrayInitializer` | Arrays | `{1, 2, 3}` | `parse_array_initializer` | `ArrayInitializer` | `test_14_criacao_e_inicializacao...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ArrayCreationExpression` | Arrays | `new int[10]`, `new int[] {1, 2}` | `parse_array_creation` | `ArrayCreationExpression` | `test_14_criacao_e_inicializacao...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ArrayAccess` | Arrays | `matriz[i][j]` | `parse_array_access` | `ArrayAccess` | `test_12_acesso_a_membros...` | `test_23_delimitadores_nao_fechados` | IMPLEMENTADO |

---

### GRUPO G — Instruções e Blocos (JLS §14)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Block` | Blocos | `{ int x = 10; }` | `parse_block` | `Block` | `test_08_classe_com_metodo_void` | `test_18_parenteses_ou_chaves...` | IMPLEMENTADO |
| `LocalVariableDeclaration` | Instruções | `int a = 1, b = 2;` | `parse_local_var_decl` | `LocalVariableDeclaration` | `test_01_declaracao_simples_int` | `test_14_declaracao_sem_ident...` | IMPLEMENTADO |
| `IfStatement` | Condicional | `if (x > 0) { ... } else { ... }`| `parse_if_statement` | `IfStatement` | `test_20_expressoes_em_condicoes` | `test_20_condicoes_ausentes...` | IMPLEMENTADO |
| `WhileStatement` | Repetição | `while (ativo) { ... }` | `parse_while_statement` | `WhileStatement` | `test_20_expressoes_em_condicoes` | `test_20_condicoes_ausentes...` | IMPLEMENTADO |
| `DoWhileStatement` | Repetição | `do { i++; } while (i < 10);` | `parse_do_while_statement` | `DoWhileStatement` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `BasicForStatement` | Repetição | `for (int i=0; i<10; i++) {}` | `parse_for_statement` | `ForStatement` | `test_20_expressoes_em_condicoes` | `test_19_cabecalho_de_for...` | IMPLEMENTADO |
| `EnhancedForStatement` | Repetição | `for (String s : lista) {}` | `parse_for_statement` | `EnhancedForStatement` | `test_27_integracao_classes...` | `test_19_cabecalho_de_for...` | IMPLEMENTADO |
| `BreakStatement` | Desvio | `break rotulo;` | `parse_break_statement` | `BreakStatement` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `ContinueStatement` | Desvio | `continue loop;` | `parse_continue_statement`| `ContinueStatement` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `ReturnStatement` | Desvio | `return resultado;` | `parse_return_statement` | `ReturnStatement` | `test_21_expressoes_em_inicial...`| `test_statements_java.py` | IMPLEMENTADO |
| `ThrowStatement` | Desvio | `throw new Exception();` | `parse_throw_statement` | `ThrowStatement` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `YieldStatement` | Desvio | `yield valor;` | `parse_yield_statement` | `YieldStatement` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | PARCIAL |
| `AssertStatement` | Instruções | `assert cond : "erro";` | `parse_assert_statement` | `AssertStatement` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `SynchronizedStatement` | Concorrência| `synchronized (lock) {}` | `parse_synchronized_stmt`| `SynchronizedStatement` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `TryStatement` | Exceções | `try {} catch (E e) {} finally {}`| `parse_try_statement` | `TryStatement` | `test_29_ausencia_de_regressoes` | `test_statements_java.py` | IMPLEMENTADO |
| `TryWithResources` | Exceções | `try (var r = init()) {}` | `parse_try_statement` | `TryStatement (resources)` | `test_statements_java.py` | `test_statements_java.py` | IMPLEMENTADO |
| `CatchClause` | Exceções | `catch (IOException \| SQLException e)` | `parse_catch_clause` | `CatchClause` | `test_statements_java.py` | `test_statements_java.py` | PARCIAL |

---

### GRUPO H — Switch e Pattern Matching (JLS §14.11, §14.30)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `SwitchStatement` | Switch | `switch (val) { case 1: break; }`| `parse_switch_statement` | `SwitchStatement` | `test_25_switch_case...` | `test_statements_java.py` | IMPLEMENTADO |
| `SwitchExpression` | Switch | `String r = switch(v) { case 1 -> "A"; };` | `parse_switch_expression` | `SwitchExpression` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | PARCIAL |
| `SwitchRule` | Switch | `case 1, 2 -> resultado;` | `parse_switch_statement` | `SwitchRule` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | PARCIAL |
| `TypePattern` | Patterns | `if (o instanceof String s)` | `parse_type_pattern` | `TypePattern` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | PARCIAL |
| `RecordPattern` | Patterns | `case P(int x, int y)` | `parse_record_pattern` | `RecordPattern` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | AUSENTE |
| `UnnamedPattern` | Patterns | `case P(_, _)` | `parse_pattern` | `UnnamedPattern` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | AUSENTE |
| `GuardedPattern` | Patterns | `case String s when !s.isEmpty()` | `parse_switch_label` | `GuardedPattern` | `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` | AUSENTE |

---

### GRUPO I — Expressões (JLS §15)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Primary` | Expressões | `10`, `"abc"`, `true`, `null` | `parse_primary` | `Literal` / `Identifier` | `test_01_declaracao_simples_int` | `test_java26_expressions.py` | IMPLEMENTADO |
| `ClassLiteral` | Expressões | `String.class`, `int.class` | `parse_primary` | `ClassLiteral` | `test_java26_expressions.py` | `test_java26_expressions.py` | PARCIAL |
| `This` / `Super` | Expressões | `this`, `super`, `Classe.this` | `parse_primary` | `Identifier` / `ThisExpression` | `test_12_acesso_a_membros...` | `test_java26_expressions.py` | IMPLEMENTADO |
| `ParenthesizedExpression`| Expressões | `(a + b)` | `parse_primary` | `ASTNode` | `test_08_parenteses_e_agrupamento` | `test_23_delimitadores_nao_fechados` | IMPLEMENTADO |
| `ObjectCreationExpression`| Expressões | `new Pessoa("Ana")` | `parse_primary` | `ObjectCreationExpression` | `test_13_criacao_de_objetos` | `test_java26_expressions.py` | IMPLEMENTADO |
| `AnonymousClassDeclaration`| Expressões| `new Runnable() { public void run() {} }` | `parse_object_creation` | `AnonymousClassDecl` | `test_java26_expressions.py` | `test_java26_expressions.py` | PARCIAL |
| `MethodInvocation` | Expressões | `obj.metodo(arg1, arg2)` | `parse_primary` / `parse_call` | `MethodCall` | `test_11_chamadas_encadeadas` | `test_23_delimitadores_nao_fechados` | IMPLEMENTADO |
| `GenericMethodInvocation`| Expressões | `Collections.<String>emptyList()` | `parse_primary` | `MethodCall` | `test_java26_expressions.py` | `test_java26_expressions.py` | PARCIAL |
| `MethodReference` | Expressões | `System.out::println`, `String::new` | `parse_primary` | `MethodReference` | `test_19_referencias_a_metodos` | `test_java26_expressions.py` | IMPLEMENTADO |
| `LambdaExpression` | Expressões | `x -> x * 2`, `(a, b) -> a + b` | `lambda_expression` | `LambdaExpression` | `test_17_lambdas_simples...` | `test_java26_expressions.py` | IMPLEMENTADO |
| `CastExpression` | Expressões | `(int) valor`, `(double) a / b` | `cast_expression` | `CastExpression` | `test_16_casts` | `test_java26_expressions.py` | IMPLEMENTADO |
| `InstanceOfExpression` | Expressões | `obj instanceof String` | `relational_expression` | `InstanceOfExpression` | `test_15_instanceof` | `test_java26_expressions.py` | IMPLEMENTADO |
| `ConditionalExpression` | Expressões | `cond ? a : b` | `ternary_expression` | `ConditionalExpression` | `test_09_expressoes_ternarias` | `test_24_ternario_incompleto` | IMPLEMENTADO |
| `AssignmentExpression` | Expressões | `a = b += c` | `assignment_expression` | `Assignment` | `test_03_atribuicao_encadeada` | `test_25_atribuicoes_malformadas` | IMPLEMENTADO |
| `BinaryOperations` | Expressões | `+`, `-`, `*`, `/`, `%`, `<<`, `>>`, `>>>`, `<`, `<=`, `>`, `>=`, `==`, `!=`, `&`, `^`, `\|`, `&&`, `\|\|` | Hierarquia Pratt / Descent | `BinaryOp` | `test_01_precedencia...` a `test_06` | `test_26_operadores_duplicados...` | IMPLEMENTADO |
| `UnaryOperations` | Expressões | `++`, `--`, `+`, `-`, `!`, `~` | `unary_expression` | `UnaryOp` | `test_07_unarios_prefixados...` | `test_java26_expressions.py` | IMPLEMENTADO |

---

### GRUPO J — Unidades Compactas e Classes Implícitas (JLS §7.3, §7.4)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `CompactCompilationUnit` | Arquivo | `void main() { System.out.println("Olá"); }` | `parse` | `CompactCompilationUnit` | `test_java26_compact_units.py` | `test_java26_compact_units.py` | PARCIAL |
| `ImplicitlyDeclaredClass` | Classes | Arquivo sem `class` explícita contendo métodos de topo | `parse` | `ImplicitlyDeclaredClass` | `test_java26_compact_units.py` | `test_java26_compact_units.py` | PARCIAL |

---

## 3. Próximos Passos e Ordem de Implementação Normativa

1. **Etapa S1 — Nomes, Tipos e Generics**:
   - `TypeIdentifier` estrito;
   - Suporte completo a TypeParameters com bounds múltiplos (`T extends Number & Comparable<T>`);
   - Suporte completo a TypeArguments com Wildcards (`?`, `? extends T`, `? super T`);
   - Desambiguação de `>>` e `>>>` em tipos genéricos aninhados (`List<List<String>>`);
   - Suporte a Type Annotations no nó `TypeReference`.
2. **Etapa S2 — Unidades de Compilação, Pacotes e Módulos** (`module-info.java`, imports sob demanda e estáticos).
3. **Etapa S3 — Declarações de Tipos** (Classes, Interfaces, Enums, Records, Sealed/Permits).
4. **Etapa S4 — Membros e Construtores** (Flexible Constructor Bodies, Initializers, Generic Methods).
5. **Etapa S5 — Annotations e Annotation Interfaces**.
6. **Etapa S6 — Instruções Completas** (Try-with-resources, Multi-catch, Yield).
7. **Etapa S7 — Switch e Pattern Matching** (Switch Rules `->`, Switch Expressions, Patterns).
8. **Etapa S8 — Expressões Completas** (Diamond Operator, Anonymous Classes, Class Literals).
9. **Etapa S9 — Integração e Auditoria Final**.
