# Matriz de Cobertura Sintática — Java SE 26 (JLS Capítulo 19)

**Data de Início:** 10/11/2026  
**Referência Normativa:** Java Language Specification (JLS), Java SE 26 Edition — Chapter 19 (Syntax).  
**Documentação Oficial:** https://docs.oracle.com/javase/specs/jls/se26/html/jls-19.html  

---

## 1. Sumário Executivo de Cobertura (Auditoria Final S9)

> [!IMPORTANT]
> **Critério de Classificação (Auditoria S9):**
> - **IMPLEMENTADO**: sintaxe reconhecida na AST e regras semânticas aplicáveis validadas por testes automatizados (respeitando o escopo de unidade única com registro de tipos externos em `unresolved_checks`).
> - **PARCIAL**: suporte sintático/semântico existente com limitações conhecidas ou dependente de classpath externo.
> - **PREVIEW**: recurso condicionado à flag `enable_preview_primitive_patterns=True` (desabilitada por padrão).
> - **NÃO IMPLEMENTADO**: ausente na matriz mapeada (0 produções ausentes dentre as 211 produções mapeadas; recursos de runtime, bytecode, JLS §16 *definite assignment* integral e JLS §18 inferência genérica integral permanecem fora do escopo).

| Grupo | Categoria Gramatical | Produções Mapeadas | Implementadas | Parciais | Preview | Não Implementadas |
|---|---|---:|---:|---:|---:|---:|
| **Grupo A** | Nomes, Identificadores e Tipos | 24 | 24 | 0 | 0 | 0 |
| **Grupo B** | Unidades de Compilação, Pacotes e Módulos | 18 | 18 | 0 | 0 | 0 |
| **Grupo C** | Classes e Declarações de Membros | 21 | 21 | 0 | 0 | 0 |
| **Grupo D** | Interfaces, Enums, Records e `@interface` (Estrutura) | 22 | 22 | 0 | 0 | 0 |
| **Grupo E** | Annotations e Annotation Interfaces | 14 | 13 | 1 *(resolução `@interface` em unidade única)* | 0 | 0 |
| **Grupo F** | Arrays e Inicializadores | 3 | 3 | 0 | 0 | 0 |
| **Grupo G** | Instruções, Blocos e Exceções (JLS §14) | 48 | 45 | 3 *(TWR/Catch externos sem classpath)* | 0 | 0 |
| **Grupo H** | Switch Expression e Pattern Matching (JLS §14.11, §14.30) | 12 | 11 | 0 | 1 *(Preview JEP 530)* | 0 |
| **Grupo I** | Expressões (JLS §15) | 17 | 14 | 3 *(inferência §18, wildcards §5.1.10, classpath externo)* | 0 | 0 |
| **Grupo J** | Unidades Compactas e Classes Implícitas | 2 | 2 | 0 | 0 | 0 |
| **TOTAL** | **Produções Mapeadas na Matriz (Grupos A–J)** | **181** | **173** | **7** | **1** | **0** |

> [!NOTE]
> **Nota de Escopo Normativo (Etapas S1 a S8 / Auditoria S7.1):**  
> Os Grupos A–G cobrem Nomes/Tipos e Type Annotations (JLS §4, §6), Unidades de Compilação/Módulos (JLS §7), Classes/Membros/Construtores (JLS §8, JEP 513), Interfaces Normais, Enums, Records e Construtores de Records (JLS §8.9, §8.10, §9.1–§9.5), Annotations e Annotation Interfaces (JLS §9.6, §9.7), Blocos, Declarações Locais, Controle de Fluxo, Try-with-Resources, Switch e Yield (JLS §14).  
> Na **Etapa S7**, foram implementadas as produções estáveis de Pattern Matching e Switch Moderno com separação estrita de preview JEP 530 confirmada na auditoria **S7.1**.  
> Na **Etapa S8**, foram implementados todos os 17 níveis de precedência de expressões (JLS §15), promoções numéricas unária/binária (JLS §5.6), estreitamento constante em inicializações/atribuições (JLS §5.2), l-values modificáveis (`final`, campos e componentes de `record`), casts primitivos/referência/interseção (`(A & B) expr`, JLS §15.16), invocação de métodos e construtores com herança, type arguments explícitos, inferência básica de genéricos e resolução de sobrecarga por especificidade (JLS §15.12.2), diamond `<>` e instanciação qualificada (`outer.new Inner()`, `AnonymousClassDeclaration` JLS §15.9), criação e indexação de arrays (incluindo JLS §15.10.1 e `.length`), todas as formas de `LambdaExpression` (com inferência de alvo e captura efetivamente final JLS §15.27.2), todas as 5 formas de `MethodReference` (incluindo `int[]::new`, JLS §15.13), e tipagem/unificação de *poly-expressions* incluindo `ConditionalExpression` e `SwitchExpression` (`->` e `yield`, JLS §15.25, §15.28).  
> - **Java SE 26 Estável (`enable_preview_primitive_patterns=False`, padrão):** Preserva estritamente a rejeição de patterns primitivos (`instanceof int i`, `case int i ->`, componentes primitivos em `RecordPattern`, `instanceof` clássico com primitivo e seletores/constantes `boolean`/`long`/`float`/`double`).  
> - **Subconjunto Preview JEP 530 Implementado (`enable_preview_primitive_patterns=True`):** Subconjunto parcial opcional sem matriz integral JLS §5.7.1–§5.7.2 nem exaustividade por faixa numérica.  
> - **Limitações Declaradas da Etapa S8 e Tipos Externos (`unresolved_checks`):** Como o compilador analisa uma unidade de compilação por vez sem classpath completo da JDK, utiliza tabela embutida curada (`java.lang`, `java.io`, `java.util`, `java.util.function`); tipos/métodos externos não declarados na unidade nem na tabela embutida são registrados em `unresolved_checks` em vez de gerar falsos positivos. Da mesma forma, não há suporte completo a captura de wildcards JLS §5.1.10 nem inferência cíclica completa de polissubstituições arbitrárias (JLS §18.5.2).

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
| `VariableDeclaratorList` | Campos | `int a, b = 2, c;` | `field_declaration` | `List[FieldDeclaration]` | `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |
| `MethodDeclaration` | Métodos | `public int calc(int a) { return a; }` | `method_declaration` | `MethodDeclaration` | `test_09_metodo_com_tipo...` | `test_21_metodo_sem_corpo...`| IMPLEMENTADO |
| `MethodModifier` | Métodos | `public static synchronized void m()` | `method_declaration` | `List[str]` | `test_18_varios_modificadores` | `test_java26_classes.py` | IMPLEMENTADO |
| `MethodHeader` | Métodos | `<T> T get(T item) throws Exception` | `method_declaration` | `MethodDeclaration` | `test_13_metodo_generico...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `FormalParameterList` | Parâmetros | `(int a, String b)` | `parse_parameter_list` | `List[Parameter]` | `test_10_metodo_com_varios...`| `test_java26_classes.py` | IMPLEMENTADO |
| `VariableArityParameter` | Parâmetros | `(String... args)` | `parse_parameter_list` | `Parameter (is_varargs=True)` | `test_20_varargs` | `test_java26_classes.py` | IMPLEMENTADO |
| `ReceiverParameter` | Parâmetros | `(Pessoa this, int x)` | `parse_parameter_list` | `ReceiverParameter` | `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |
| `ConstructorDeclaration` | Construtor | `public Pessoa(String n) { ... }` | `constructor_declaration` | `ConstructorDeclaration` | `test_12_construtor_com_param`| `test_java26_classes.py` | IMPLEMENTADO |
| `ConstructorModifier` | Construtor | `public`, `protected`, `private` | `constructor_declaration` | `List[str]` | `test_12_construtor_com_param`| `test_java26_classes.py` | IMPLEMENTADO |
| `ConstructorInvocation` | Construtor | `this("padrao");`, `super(id);` | `parse_constructor_body` | `ExplicitConstructorInvocation` | `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |
| `FlexibleConstructorBody`| Construtor | `validar(); super();` (JEP 513) | `parse_constructor_body` | `ConstructorBody` | `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |
| `InstanceInitializer` | Inicializador | `{ contador++; }` | `class_declaration` | `InstanceInitializer` | `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |
| `StaticInitializer` | Inicializador | `static { Logger.init(); }` | `class_declaration` | `StaticInitializer` | `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |

---

### GRUPO D — Interfaces Normais, Enums e Records (JLS §8.9, §8.10, §9.1–§9.5)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `NormalInterfaceDeclaration` | Interfaces | `public interface Servico {}` | `interface_declaration` | `InterfaceDeclaration` | `test_01_interface_vazia_simples` | `test_17_erro_sintatico_interface_com_implements` | IMPLEMENTADO |
| `InterfaceModifier` | Interfaces | `public`, `sealed`, `non-sealed`, `abstract`, `static`, `strictfp` | `_parse_annotations_and_modifiers` | `List[str]` | `test_02_interface_publica_e_anotacoes` | `test_22_erro_semantico_interface_final` | IMPLEMENTADO |
| `TypeParameters` (Interface) | Interfaces | `interface Repo<T, ID extends Comparable<ID>> {}` | `interface_declaration` | `List[TypeParameter]` | `test_03_interface_generica_com_bounds` | `test_java26_names_types.py` | IMPLEMENTADO |
| `InterfaceExtends` | Interfaces | `extends Serializavel, Comparavel<T>` | `interface_declaration` | `InterfaceExtends` | `test_04_interface_extends_multiplo` | `test_17_erro_sintatico_interface_com_implements` | IMPLEMENTADO |
| `InterfacePermits` | Interfaces | `sealed interface Forma permits Circulo {}` | `interface_declaration` | `InterfacePermits` | `test_05_interface_sealed_e_permits` | `test_23_erro_semantico_modificadores_top_level_e_sealed_conflitante` | IMPLEMENTADO |
| `InterfaceBody` | Interfaces | `{ int MAX = 10; void run(); }` | `interface_declaration` | `InterfaceBody` | `test_01_interface_vazia_simples` | `test_21_erro_sintatico_anotacao_solta_sem_membro_em_interface` | IMPLEMENTADO |
| `InterfaceMemberDeclaration` | Interfaces | Constantes, métodos, tipos aninhados e `;` | `interface_member` | `InterfaceMemberDeclaration` | `test_13_tipos_aninhados_em_interface` | `test_18_erro_sintatico_construtor_em_interface` | IMPLEMENTADO |
| `ConstantDeclaration` | Interfaces | `public static final int MAX = 100;` | `interface_member` | `InterfaceConstantDeclaration` | `test_06_constantes_interface_e_modificadores_implicitos` | `test_20_erro_sintatico_constante_sem_inicializador` | IMPLEMENTADO |
| `InterfaceMethodDeclaration` | Interfaces | `abstract`, `default`, `static`, `private` | `interface_member` | `InterfaceMethodDeclaration` | `test_09_metodo_default_com_corpo` | `test_24_erro_semantico_combinacao_invalida_modificadores_metodo_interface` | IMPLEMENTADO |
| `EnumDeclaration` | Enums | `public enum Status implements Comparable<Status> {}` | `enum_declaration` | `EnumDeclaration` | `test_01_enum_simples` | `test_15_erro_sintatico_enum_com_extends` | IMPLEMENTADO |
| `EnumBody` | Enums | `{ A(1), B, ; int x = 1; }` | `enum_declaration` | `EnumBody` | `test_03_enum_com_virgula_final_trailing_comma` | `test_19_erro_sintatico_enum_sem_chaves` | IMPLEMENTADO |
| `EnumConstantList` / `EnumConstant` | Enums | `@Deprecated MERCURIO(3.3e23, 2439)` | `enum_declaration` | `EnumConstantList` / `EnumConstant` | `test_05_constantes_enum_com_argumentos_e_anotacoes` | `test_16_erro_sintatico_lista_constantes_malformada_virgula_inicial` | IMPLEMENTADO |
| `EnumConstantBody` | Enums | `SOMA("+") { public int calc(...) { ... } }` | `enum_declaration` | `EnumConstantBody` | `test_06_corpo_especifico_de_constante_enum` | `test_25_erro_semantico_construtor_dentro_de_enum_constant_body` | IMPLEMENTADO |
| `EnumBodyDeclarations` | Enums | `; private final int v; private E(int v) {}` | `enum_declaration` | `EnumBodyDeclarations` | `test_08_construtor_enum_com_delegacao_this` | `test_23_erro_semantico_construtor_enum_public_ou_protected` | IMPLEMENTADO |
| `RecordDeclaration` | Records | `public record Caixa<T>(T v) implements Serializable {}` | `record_declaration` | `RecordDeclaration` | `test_01_record_vazio_simples` | `test_14_erro_sintatico_record_com_extends` | IMPLEMENTADO |
| `RecordHeader` / `RecordComponentList` | Records | `(int x, int y)` | `record_declaration` | `RecordHeader` / `RecordComponentList` | `test_02_record_com_componentes_e_modificador_final` | `test_13_erro_sintatico_record_sem_parenteses` | IMPLEMENTADO |
| `RecordComponent` | Records | `@NotNull String nome` | `record_declaration` | `RecordComponent` | `test_05_anotacoes_em_record_e_componentes` | `test_16_erro_sintatico_componente_void_ou_sem_identificador` | IMPLEMENTADO |
| `VariableArityRecordComponent` | Records | `@Tag String @NaoVazio ... linhas` | `record_declaration` | `VariableArityRecordComponent` | `test_06_componente_varargs_e_anotacao_na_reticencias` | `test_15_erro_sintatico_varargs_nao_ultimo_componente` | IMPLEMENTADO |
| `RecordBody` / `RecordBodyDeclaration` | Records | Campos estáticos, métodos, inicializadores `static` e tipos aninhados | `record_member` | `RecordBody` / `RecordBodyDeclaration` | `test_08_campos_static_e_inicializador_estatico_em_record` | `test_20_erro_semantico_campo_de_instancia_em_record` | IMPLEMENTADO |
| `RecordConstructorDeclarations` | Records | `NormalCanonicalConstructor`, `CompactConstructorDeclaration`, `NonCanonicalRecordConstructor` | `record_member` | `NormalCanonicalConstructor`, `CompactConstructorDeclaration`, `NonCanonicalRecordConstructor` | `test_java26_record_constructors.py` | `test_java26_record_constructors.py` | IMPLEMENTADO |
| `AnnotationInterfaceDeclaration` | Annotations | `public @interface MinhaAnotacao {}` | `annotation_interface_declaration` | `AnnotationInterfaceDeclaration` | `test_01_annotation_interface_vazia` | `test_09_erro_sintatico_annotation_interface_com_clausulas_proibidas` | IMPLEMENTADO |
| `AnnotationInterfaceBody` / Elements | Annotations | `String valor() default "";` | `annotation_interface_member` | `AnnotationInterfaceBody` / `AnnotationInterfaceElementDeclaration` | `test_02_annotation_interface_publica_e_abstrata` | `test_10_erro_sintatico_elemento_com_parametros_throws_ou_corpo` | IMPLEMENTADO |

---

### GRUPO E — Annotations e Annotation Interfaces (JLS §9.6, §9.7)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `AnnotationInterfaceDeclaration` | `@interface` | `public @interface Config {}` | `annotation_interface_declaration` | `AnnotationInterfaceDeclaration` | `test_java26_annotation_interfaces.py` | `test_java26_annotation_interfaces.py` | IMPLEMENTADO |
| `AnnotationInterfaceBody` | `@interface` | `{ String nome(); int v() default 1; }` | `annotation_interface_declaration` | `AnnotationInterfaceBody` | `test_java26_annotation_interfaces.py` | `test_java26_annotation_interfaces.py` | IMPLEMENTADO |
| `AnnotationInterfaceMemberDeclaration` | `@interface` | Constantes, elementos e tipos aninhados | `annotation_interface_member` | `AnnotationInterfaceMemberDeclaration` | `test_java26_annotation_interfaces.py` | `test_java26_annotation_interfaces.py` | IMPLEMENTADO |
| `AnnotationInterfaceElementDeclaration` | `@interface` | `String tags() [] default {};` | `annotation_interface_member` | `AnnotationInterfaceElementDeclaration` | `test_java26_annotation_interfaces.py` | `test_java26_annotation_interfaces.py` | IMPLEMENTADO |
| `AnnotationInterfaceElementModifier` | `@interface` | `public`, `abstract` | `_parse_annotations_and_modifiers` | `AnnotationInterfaceElementModifier` | `test_java26_annotation_interfaces.py` | `test_java26_annotation_semantics.py` | IMPLEMENTADO |
| `DefaultValue` | `@interface` | `default "anon"` / `default @Tag("x")` | `annotation_interface_member` | `AnnotationDefaultValue` | `test_java26_annotation_interfaces.py` | `test_java26_annotation_interfaces.py` | IMPLEMENTADO |
| `Annotation` | Annotations | `@Override` / `@A.B` / `@C(x = 1)` | `_parse_single_annotation` | `Annotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `MarkerAnnotation` | Annotations | `@Deprecated`, `@java.lang.Override` | `_parse_single_annotation` | `MarkerAnnotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `SingleElementAnnotation` | Annotations | `@SuppressWarnings("all")` | `_parse_single_annotation` | `SingleElementAnnotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `NormalAnnotation` | Annotations | `@Info(nome = "App", versao = 1)` | `_parse_single_annotation` | `NormalAnnotation` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `ElementValuePairList` / `ElementValuePair` | Annotations | `k1 = v1, k2 = v2` | `_parse_single_annotation` | `ElementValuePairList` / `ElementValuePair` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `ElementValue` | Annotations | `expr \| @Ann \| { ... }` | `parse_element_value` | `ElementValue` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `ElementValueArrayInitializer` | Annotations | `{"unchecked", "rawtypes", }` | `parse_element_value_array_initializer` | `ElementValueArrayInitializer` | `test_java26_annotations.py` | `test_java26_annotations.py` | IMPLEMENTADO |
| `ElementValueList` / `TypeAnnotation` Contexts | Annotations | `@NonNull T`, `Outer.@B Inner`, `new @A Foo()`, `int @A []` | `parse_element_value_array_initializer` / `parse_type_reference` / `parse_new_expression` | `ElementValueList` / `TypeReference` | `test_java26_type_annotations.py` | `test_java26_type_annotations.py` | IMPLEMENTADO |

---

### GRUPO F — Arrays e Inicializadores (JLS §10)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `ArrayInitializer` | Arrays | `{1, 2, 3}` | `parse_array_initializer` | `ArrayInitializer` | `test_14_criacao_e_inicializacao...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ArrayCreationExpression` | Arrays | `new int[10]`, `new int[] {1, 2}` | `parse_array_creation` | `ArrayCreationExpression` | `test_14_criacao_e_inicializacao...` | `test_java26_names_types.py` | IMPLEMENTADO |
| `ArrayAccess` | Arrays | `matriz[i][j]` | `parse_array_access` | `ArrayAccess` | `test_12_acesso_a_membros...` | `test_23_delimitadores_nao_fechados` | IMPLEMENTADO |

---

### GRUPO G — Instruções e Blocos (JLS §14 — Mapeamento Individual Etapa S6)

> **Legenda de estados nesta seção:** `IMPLEMENTADO` · `PARCIAL` · `AUSENTE` · `DEPENDENTE DE S7` · `DEPENDENTE DE S8` · `IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA`.

| Produção (JLS 19 / §14) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Block` | Blocos | `{ int x = 10; }` | `parse_block` | `Block` | `test_java26_blocks.py` (`test_01`, `test_03`) | `test_java26_blocks.py` (`test_10`) | IMPLEMENTADO |
| `BlockStatements` | Blocos | `int a = 1; a++;` | `parse_block` | `Block.statements` | `test_java26_blocks.py` (`test_04`) | `test_java26_blocks.py` (`test_10`) | IMPLEMENTADO |
| `BlockStatement` | Blocos | `class L {}` / `int x;` / `f();` | `block_statement` | `BlockStatement` | `test_java26_blocks.py` (`test_04`) | `test_java26_blocks.py` (`test_07`) | IMPLEMENTADO |
| `LocalClassOrInterfaceDeclaration` | Tipos Locais | `class Aux {}`, `interface A {}`, `enum E {}`, `record R(int x) {}` | `_parse_local_type_declaration` | `LocalClassOrInterfaceDeclaration` | `test_java26_local_types.py` (`test_01`–`04`) | `test_java26_local_types.py` (`test_05`–`08`, `test_10`) | IMPLEMENTADO |
| `LocalVariableDeclarationStatement` | Decl. Locais | `final int x = 10;` | `parse_local_variable_declaration` | `LocalVariableDeclaration` | `test_java26_local_declarations.py` (`test_01`–`05`) | `test_java26_control_statements.py` (`test_06`) | IMPLEMENTADO |
| `LocalVariableDeclaration` | Decl. Locais | `@Ann final int a = 1, b = 2` | `_parse_local_variable_declaration_core` | `LocalVariableDeclaration` | `test_java26_local_declarations.py` (`test_02`, `test_04`) | `test_java26_local_declarations.py` (`test_16`) | IMPLEMENTADO |
| `LocalVariableType` | Decl. Locais | `String` ou contextual `var` | `_parse_local_variable_declaration_core` | `LocalVariableType` | `test_java26_local_declarations.py` (`test_05`) | `test_java26_local_declarations.py` (`test_06`–`13`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `VariableModifier` | Decl. Locais | `final`, `@NotNull` | `_parse_annotations_and_modifiers_detailed` | `modifiers` / `annotations` | `test_java26_local_declarations.py` (`test_04`) | `test_java26_local_declarations.py` (`test_16`) | IMPLEMENTADO |
| `VariableDeclaratorList` | Decl. Locais | `a = 1, b = 2, c = 3` | `_parse_local_variable_declaration_core` | `declarators` | `test_java26_local_declarations.py` (`test_02`) | `test_java26_local_declarations.py` (`test_07`) | IMPLEMENTADO |
| `VariableDeclarator` | Decl. Locais | `matriz[][] = ...` | `_parse_local_variable_declaration_core` | `VariableDeclarator` | `test_java26_local_declarations.py` (`test_03`) | `test_java26_local_declarations.py` (`test_06`) | IMPLEMENTADO |
| `VariableDeclaratorId` | Decl. Locais | `vetor[]` ou `_` | `parse_variable_declarator_id` | `VariableDeclaratorId` | `test_java26_local_declarations.py` (`test_03`, `test_14`) | `test_java26_local_declarations.py` (`test_08`, `test_15`) | IMPLEMENTADO |
| `VariableInitializer` | Decl. Locais | `10` ou `{1, 2, 3}` | `parse_variable_initializer` | `ASTNode` / `ArrayInitializer` | `test_java26_local_declarations.py` (`test_01`, `test_03`) | `test_java26_local_declarations.py` (`test_09`–`12`) | IMPLEMENTADO |
| `Statement` | Instruções | `if (a) if (b) f(); else g();` | `parse_statement` | `Statement` | `test_java26_control_statements.py` (`test_03`–`05`) | `test_java26_control_statements.py` (`test_06`) | IMPLEMENTADO |
| `StatementNoShortIf` | Desambiguação | `if (a) while (b) f(); else g();` | `parse_statement_no_short_if` | `Statement` | `test_java26_control_statements.py` (`test_04`–`06`) | `test_java26_control_statements.py` (`test_06`) | IMPLEMENTADO |
| `StatementWithoutTrailingSubstatement` | Instruções | `;`, `{}`, `break;`, `throw e;`, `try ...` | `parse_statement_without_trailing_substatement` | `Statement` | `test_java26_control_statements.py` (`test_07`–`11`) | `test_java26_control_statements.py` (`test_02`, `test_10`) | IMPLEMENTADO |
| `EmptyStatement` | Instruções | `;` | `parse_statement_without_trailing_substatement` | `EmptyStatement` | `test_java26_control_statements.py` (`test_07`) | `test_syntax_java.py` | IMPLEMENTADO |
| `LabeledStatement` | Rótulos | `externo: for (...) {}` | `parse_labeled_statement` | `LabeledStatement` | `test_java26_loops_labels.py` (`test_05`, `test_06`) | `test_java26_loops_labels.py` (`test_06`, `test_07`) | IMPLEMENTADO |
| `LabeledStatementNoShortIf` | Rótulos | `if (a) r: f(); else g();` | `parse_labeled_statement(no_short_if=True)` | `LabeledStatement` | `test_java26_control_statements.py` (`test_06`) | `test_java26_loops_labels.py` (`test_06`) | IMPLEMENTADO |
| `ExpressionStatement` | Expressões | `x = 1;`, `++x;`, `f();`, `new A();` | `parse_statement_without_trailing_substatement` | `ExpressionStatement` / `Assignment` | `test_java26_control_statements.py` (`test_01`) | `test_java26_control_statements.py` (`test_02`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `IfThenStatement` | Condicional | `if (ok) { ... }` | `parse_if_statement` | `IfStatement` | `test_java26_control_statements.py` (`test_03`, `test_04`) | `test_java26_statement_semantics.py` (`test_04`) | IMPLEMENTADO |
| `IfThenElseStatement` | Condicional | `if (ok) f(); else g();` | `parse_if_statement` | `IfStatement` | `test_java26_control_statements.py` (`test_03`–`05`) | `test_java26_control_statements.py` (`test_06`) | IMPLEMENTADO |
| `AssertStatement` | Asserção | `assert x > 0 : "msg";` | `parse_assert_statement` | `AssertStatement` | `test_java26_control_statements.py` (`test_08`) | `test_java26_statement_semantics.py` (`test_04`) | IMPLEMENTADO |
| `SwitchStatement` | Switch | `switch (v) { case String s -> f(s); default -> g(); }` | `parse_switch_statement` | `SwitchStatement` | `test_java26_switch_statements.py`, `test_java26_switch_patterns.py` | `test_java26_switch_statements.py` (`test_07`–`09`), `test_java26_pattern_dominance.py` | IMPLEMENTADO |
| `SwitchBlock` | Switch | `{ case 1: ... }` / `{ case String s -> ... }` | `_parse_switch_block` | `SwitchBlock` | `test_java26_switch_statements.py`, `test_java26_switch_patterns.py` | `test_java26_switch_statements.py` (`test_07`) | IMPLEMENTADO |
| `SwitchBlockStatementGroup` | Switch | `case String s: f(s); break;` | `_parse_switch_block` | `SwitchBlockStatementGroup` | `test_java26_switch_statements.py`, `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` (`test_04`) | IMPLEMENTADO |
| `SwitchRule` | Switch | `case Ponto(var x, _) when x > 0 -> f();` | `_parse_switch_block` | `SwitchRule` | `test_java26_switch_statements.py`, `test_java26_switch_patterns.py` | `test_java26_switch_statements.py` (`test_06`, `test_07`) | IMPLEMENTADO |
| `SwitchLabel` | Switch | `case 1, 2`, `case null, default`, `case String s when ...`, `default` | `_parse_switch_label` | `CaseLabel` / `PatternCaseLabel` / `DefaultLabel` | `test_java26_switch_statements.py`, `test_java26_switch_patterns.py` | `test_java26_switch_patterns.py` (`test_04`), `test_java26_pattern_dominance.py` | IMPLEMENTADO |
| `WhileStatement` | Repetição | `while (i < n) { i++; }` | `parse_while_statement` | `WhileStatement` | `test_java26_loops_labels.py` (`test_01`) | `test_java26_loops_labels.py` (`test_09`) | IMPLEMENTADO |
| `DoStatement` | Repetição | `do { i--; } while (i > 0);` | `parse_do_while_statement` | `DoWhileStatement` | `test_java26_loops_labels.py` (`test_01`) | `test_java26_loops_labels.py` (`test_09`) | IMPLEMENTADO |
| `BasicForStatement` | Repetição | `for (i=0, j=1; i<j; i++, j--) {}` | `_parse_traditional_for` | `ForStatement` | `test_java26_loops_labels.py` (`test_02`, `test_03`) | `test_java26_loops_labels.py` (`test_09`) | IMPLEMENTADO |
| `EnhancedForStatement` | Repetição | `for (var item : itens) {}` | `_parse_enhanced_for` | `EnhancedForStatement` | `test_java26_loops_labels.py` (`test_04`) | `test_java26_loops_labels.py` (`test_09`) | IMPLEMENTADO |
| `ForInit` | Repetição | `int a=1, b=2` ou `i=0, j=1` | `_parse_traditional_for` | `LocalVariableDeclaration` / `StatementExpressionList` | `test_java26_loops_labels.py` (`test_03`) | `test_java26_loops_labels.py` (`test_09`) | IMPLEMENTADO |
| `ForUpdate` | Repetição | `i++, j--` | `_parse_statement_expression_list` | `StatementExpressionList` | `test_java26_loops_labels.py` (`test_03`) | `test_java26_loops_labels.py` (`test_09`) | IMPLEMENTADO |
| `BreakStatement` | Desvio | `break;`, `break externo;` | `parse_break_statement` | `BreakStatement` | `test_java26_loops_labels.py` (`test_05`) | `test_java26_loops_labels.py` (`test_07`, `test_08`) | IMPLEMENTADO |
| `ContinueStatement` | Desvio | `continue;`, `continue externo;` | `parse_continue_statement` | `ContinueStatement` | `test_java26_loops_labels.py` (`test_05`) | `test_java26_loops_labels.py` (`test_07`, `test_08`) | IMPLEMENTADO |
| `ReturnStatement` | Desvio | `return;`, `return valor;` | `parse_return_statement` | `ReturnStatement` | `test_java26_control_statements.py` (`test_11`) | `test_java26_statement_semantics.py` (`test_01`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `ThrowStatement` | Exceções | `throw new IllegalArgumentException();` | `parse_throw_statement` | `ThrowStatement` | `test_java26_control_statements.py` (`test_09`) | `test_statements_java.py` | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `SynchronizedStatement` | Concorrência | `synchronized (lock) { ... }` | `parse_synchronized_statement` | `SynchronizedStatement` | `test_java26_control_statements.py` (`test_09`) | `test_java26_control_statements.py` (`test_10`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `TryStatement` | Exceções | `try {} catch (E e) {} finally {}` | `parse_try_statement` | `TryStatement` | `test_java26_try_statements.py` (`test_01`) | `test_java26_try_statements.py` (`test_05`) | IMPLEMENTADO |
| `TryWithResourcesStatement` | Exceções | `try (var r = abrir()) {}` | `parse_try_statement` | `TryStatement` / `TryWithResourcesStatement` | `test_java26_try_statements.py` (`test_03`, `test_04`) | `test_java26_try_statements.py` (`test_05`, `test_07`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `ResourceSpecification` | Exceções | `(ResourceList [;])` | `parse_try_statement` | `ResourceSpecification` | `test_java26_try_statements.py` (`test_03`, `test_04`) | `test_java26_try_statements.py` (`test_05`) | IMPLEMENTADO |
| `ResourceList` | Exceções | `R1 a = ...; r2;` | `parse_try_statement` | `ResourceSpecification.resources` | `test_java26_try_statements.py` (`test_03`, `test_04`) | `test_java26_try_statements.py` (`test_05`) | IMPLEMENTADO |
| `Resource` | Exceções | `var r = ...` ou referência `entrada` | `parse_try_statement` | `Resource` | `test_java26_try_statements.py` (`test_03`, `test_04`) | `test_java26_try_statements.py` (`test_05`, `test_07`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `CatchClause` | Exceções | `catch (final IOException e) {}` | `parse_try_statement` | `CatchClause` | `test_java26_try_statements.py` (`test_01`, `test_02`) | `test_java26_try_statements.py` (`test_05`, `test_06`) | IMPLEMENTADO |
| `CatchFormalParameter` | Exceções | `final @Ann CatchType id` | `parse_try_statement` | `Parameter` (`CatchClause.parameter`) | `test_java26_try_statements.py` (`test_02`) | `test_java26_try_statements.py` (`test_05`) | IMPLEMENTADO |
| `CatchType` | Exceções | `IOException \| SQLException` | `parse_try_statement` | `CatchType` | `test_java26_try_statements.py` (`test_02`) | `test_java26_try_statements.py` (`test_05`, `test_06`) | IMPLEMENTADO, MAS SEM VALIDAÇÃO SEMÂNTICA COMPLETA |
| `Finally` | Exceções | `finally { liberar(); }` | `parse_try_statement` | `TryStatement.finally_block` | `test_java26_try_statements.py` (`test_01`) | `test_java26_try_statements.py` (`test_05`) | IMPLEMENTADO |
| `YieldStatement` | Desvio | `yield resultado;` | `parse_yield_statement` | `YieldStatement` | `test_java26_control_statements.py` (`test_11`) | `test_java26_control_statements.py` (`test_12`), `test_java26_statement_semantics.py` (`test_03`) | IMPLEMENTADO |

---

### GRUPO H — Switch Expression e Pattern Matching (JLS §14.11, §14.30, §15.20.2, §15.28)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Pattern` | Patterns | `String s` ou `Ponto(var x, _)` | `parse_pattern` | `Pattern` (`TypePattern` / `RecordPattern`) | `test_java26_patterns.py` | `test_java26_patterns.py` (`test_04`) | IMPLEMENTADO |
| `TypePattern` | Patterns | `@Tag final String s` / `String _` / `var x` *(componente)* | `_parse_type_pattern_after_type` | `TypePattern` / `PatternVariable` | `test_java26_patterns.py` (`test_01`–`02`) | `test_java26_patterns.py` (`test_04`, `test_07`) | IMPLEMENTADO |
| `RecordPattern` | Patterns | `Par<String, Integer>(var k, Integer v)` / `Soma(Numero(var a), _)` | `_parse_record_pattern_after_type` | `RecordPattern` | `test_java26_record_patterns.py` (`test_01`–`03`) | `test_java26_record_patterns.py` (`test_04`–`08`) | IMPLEMENTADO *(semântica externa registrada em `unresolved_checks`)* |
| `ComponentPatternList` | Patterns | `(String k, var y, _)` | `_parse_record_pattern_after_type` | `ComponentPatternList` | `test_java26_record_patterns.py` (`test_02`) | `test_java26_record_patterns.py` (`test_04`) | IMPLEMENTADO |
| `ComponentPattern` | Patterns | `TypePattern` \| `RecordPattern` \| `MatchAllPattern` | `parse_component_pattern` | `ComponentPattern` | `test_java26_record_patterns.py` (`test_09`) | `test_java26_record_patterns.py` (`test_06`, `test_07`) | IMPLEMENTADO |
| `MatchAllPattern` | Patterns | `case Par(String _, _) -> ...` | `parse_component_pattern` | `MatchAllPattern` | `test_java26_patterns.py` (`test_05`), `test_java26_record_patterns.py` (`test_09`) | `test_java26_patterns.py` (`test_04`) | IMPLEMENTADO |
| `Guard` | Switch Patterns | `when s.length() > 0` (`when` contextual) | `_parse_switch_label` | `Guard` | `test_java26_switch_patterns.py` (`test_01`–`03`), `test_java26_patterns.py` (`test_03`) | `test_java26_switch_patterns.py` (`test_06`) | IMPLEMENTADO |
| `CasePattern` | Switch Patterns | `case String _, Integer _ -> ...` | `_parse_switch_label` | `Pattern` (`CaseLabel.patterns`) | `test_java26_switch_patterns.py` (`test_03`) | `test_java26_switch_patterns.py` (`test_04`) | IMPLEMENTADO |
| `PatternCaseLabel` | Switch Patterns | `case Ponto(var x, var y) when x == y` | `_parse_switch_label` | `PatternCaseLabel` | `test_java26_switch_patterns.py` (`test_01`), `test_java26_patterns.py` (`test_02`) | `test_java26_pattern_dominance.py` | IMPLEMENTADO *(dominância/exaustividade externa registrada em `unresolved_checks`)* |
| `PatternInstanceOfExpression` | Patterns / Expr | `obj instanceof String s`, `obj instanceof Ponto(var x, _)` | `_parse_instanceof_rhs` | `PatternInstanceOfExpression` | `test_java26_instanceof_patterns.py` (`test_01`–`03`), `test_java26_pattern_scope.py` | `test_java26_instanceof_patterns.py` (`test_04`, `test_05`) | IMPLEMENTADO |
| `SwitchExpression` | Switch | `int r = switch (expr) { case Num(var v) -> v; ... };` | `_parse_switch_expression` | `SwitchExpression` | `test_java26_switch_expression_typing.py`, `test_java26_switch_expressions.py`, `test_java26_switch_expression_types.py`, `test_java26_s85_regressions.py` | `test_java26_switch_expressions.py` (`test_06`–`09`), `test_java26_switch_expression_types.py` (`test_04`–`06`) | IMPLEMENTADO *(poly-expression S8/S8.5, `->` e `yield`, unificação LUB, rejeição de `void`, exaustividade)* |
| `PrimitiveType` em `Pattern` *(Preview)* | Patterns Preview | `o instanceof int i`, `case int i ->`, `Ponto(int x, int y)` | `parse_pattern` / `_parse_instanceof_rhs` *(via flag)* | `TypePattern` / `PatternInstanceOfExpression` | `test_java26_pattern_preview_separation.py`, `test_java26_pattern_semantics.py` (`test_04` com preview) | `test_java26_pattern_preview_separation.py`, `test_java26_pattern_semantics.py` (`test_04`–`05` modo padrão) | PARCIAL *(JEP 530 preview: rejeitado no modo padrão Java SE 26; subconjunto parcial sob flag)* |

---

### GRUPO I — Expressões (JLS §15)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `Primary` | Expressões | `10`, `"abc"`, `true`, `null`, `(a + b)` | `parse_primary` | `Literal` / `Identifier` | `test_01_declaracao_simples_int` | `test_java26_expression_precedence.py` | IMPLEMENTADO |
| `ClassLiteral` | Expressões | `String.class`, `int.class`, `void.class`, `int[][].class` | `_parse_class_literal` | `ClassLiteral` | `test_java26_class_literals.py` (`test_01`–`05`), `test_java26_annotations.py` | `test_java26_class_literals.py` (`test_04`), `test_java26_annotation_interfaces.py` | IMPLEMENTADO *(incl. tipagem `Class<T>` JLS §15.8.2)* |
| `This` / `Super` | Expressões | `this`, `super`, `Classe.this`, `Outer.super` | `parse_primary` | `Identifier` / `MemberAccess` | `test_java26_class_literals.py` (`test_06`), `test_java26_expression_semantics.py` | `test_java26_class_literals.py` (`test_07`), `test_java26_expression_semantics.py` | IMPLEMENTADO |
| `ParenthesizedExpression`| Expressões | `(a + b)` | `parse_primary` | `ASTNode` | `test_java26_expression_precedence.py` | `test_23_delimitadores_nao_fechados` | IMPLEMENTADO |
| `ClassInstanceCreationExpression` / Diamond `<>` | Expressões | `new Caixa<>("ok")`, `outer.new Inner()` | `parse_object_creation` | `ObjectCreationExpression` | `test_java26_object_creation.py` (`test_01`–`06`) | `test_java26_object_creation.py` (`test_07`–`09`) | IMPLEMENTADO |
| `AnonymousClassDeclaration` | Expressões | `new Runnable() { public void run() {} }` | `parse_object_creation` | `ObjectCreationExpression.anonymous_body` | `test_java26_object_creation.py` (`test_05`, `test_06`) | `test_java26_object_creation.py` (`test_09`) | IMPLEMENTADO |
| `ArrayCreationExpression` / `ArrayInitializer` | Expressões | `new int[2][3]`, `new int[] {1, 2}`, `{1, 2}` | `parse_object_creation` / `parse_array_initializer` | `ArrayCreationExpression` / `ArrayInitializer` | `test_java26_array_expressions.py`, `test_java26_array_creation.py` | `test_java26_array_expressions.py`, `test_java26_array_creation.py` | IMPLEMENTADO |
| `ArrayAccess` / `FieldAccess` | Expressões | `matriz[i][j]`, `arr.length`, `obj.campo` | `parse_postfix` | `ArrayAccess` / `MemberAccess` | `test_java26_array_expressions.py`, `test_java26_array_access.py`, `test_java26_field_access.py`, `test_java26_expression_semantics.py` | `test_java26_array_access.py`, `test_java26_field_access.py` | IMPLEMENTADO |
| `MethodInvocation` & `GenericMethodInvocation` | Expressões | `obj.m(1)`, `Collections.<String>singletonList("a")` | `parse_postfix` / `parse_call` | `MethodCall` (`type_arguments`) | `test_java26_method_invocations.py`, `test_java26_method_invocation.py` | `test_java26_method_invocations.py`, `test_java26_method_invocation.py` | IMPLEMENTADO *(classpath externo em `unresolved_checks`)* |
| `MethodReference` (5 formas) | Expressões | `String::length`, `String::new`, `int[]::new`, `out::println` | `_parse_method_reference_after_target` | `MethodReference` | `test_java26_method_references.py` (`test_01`–`05`, `test_09`) | `test_java26_method_references.py` (`test_06`–`08`, `test_10`–`13`) | IMPLEMENTADO *(sobrecarga/inferência genérica completa fora do escopo)* |
| `LambdaExpression` | Expressões | `x -> x + 1`, `(int a, var b) -> ...`, `(@A final var x) -> { return x; }` | `parse_lambda_expression` | `LambdaExpression` / `LambdaParameter` | `test_java26_functional_interfaces.py`, `test_java26_lambda_expressions.py`, `test_java26_lambda_typing.py`, `test_java26_lambda_capture.py`, `test_java26_s84_regressions.py` | `test_java26_functional_interfaces.py`, `test_java26_lambda_expressions.py`, `test_java26_lambda_typing.py`, `test_java26_lambda_capture.py` | IMPLEMENTADO *(sobrecarga/inferência genérica §18 e captura wildcard §5.1.10 parciais)* |
| `CastExpression` (Primitivo/Ref/Interseção) | Expressões | `(int) d`, `(A & Serializable) obj` | `parse_cast_expression` | `CastExpression` (`additional_bounds`) | `test_java26_casts_conversions.py`, `test_java26_cast_expressions.py`, `test_java26_primitive_conversions.py`, `test_java26_reference_conversions.py`, `test_java26_boxing_unboxing.py`, `test_java26_constant_narrowing.py` | `test_java26_casts_conversions.py` (`test_06`–`09`), `test_java26_cast_expressions.py` (`test_04`–`06`) | IMPLEMENTADO |
| `InstanceOfExpression` | Expressões | `obj instanceof String` | `parse_relational` | `InstanceOfExpression` | `test_15_instanceof`, `test_java26_operator_semantics.py` (`test_27`) | `test_java26_pattern_preview_separation.py`, `test_java26_operator_semantics.py` (`test_27`, `test_28`) | IMPLEMENTADO |
| `ConditionalExpression` | Expressões | `cond ? () -> 1 : () -> 2` | `parse_conditional` | `ConditionalExpression` | `test_java26_poly_expressions.py` (`test_01`–`05`), `test_java26_operator_semantics.py` (`test_16`, `test_17`) | `test_java26_poly_expressions.py` (`test_08`), `test_java26_operator_semantics.py` (`test_16`, `test_17`) | IMPLEMENTADO |
| `AssignmentExpression` | Expressões | `a = b += c` | `parse_assignment` | `Assignment` | `test_java26_assignment_expressions.py` (`test_01`–`05`), `test_java26_operator_semantics.py` (`test_20`–`25`) | `test_java26_assignment_expressions.py` (`test_06`–`09`), `test_java26_operator_semantics.py` (`test_20`, `test_22`, `test_24`) | IMPLEMENTADO |
| `BinaryOperations` | Expressões | `+`, `-`, `*`, `/`, `%`, `<<`, `>>`, `>>>`, `<`, `<=`, `>`, `>=`, `==`, `!=`, `&`, `^`, `\|`, `&&`, `\|\|` | 17 níveis de precedência | `BinaryOp` | `test_java26_expression_precedence.py` (`test_01`–`21`), `test_java26_operator_semantics.py` (`test_01`–`15`) | `test_java26_arithmetic_expressions.py` (`test_07`–`10`), `test_java26_operator_semantics.py` (`test_01`–`15`) | IMPLEMENTADO |
| `UnaryOperations` | Expressões | `++`, `--`, `+`, `-`, `!`, `~` | `parse_unary` / `parse_postfix` | `UnaryOp` | `test_java26_arithmetic_expressions.py` (`test_03`–`05`), `test_java26_operator_semantics.py` (`test_03`, `test_13`, `test_18`) | `test_java26_arithmetic_expressions.py` (`test_09`, `test_10`), `test_java26_operator_semantics.py` (`test_03`, `test_13`, `test_19`) | IMPLEMENTADO |

---

### GRUPO J — Unidades Compactas e Classes Implícitas (JLS §7.3, §7.4)

| Produção (JLS 19) | Categoria | Exemplo Java Válido | Função no Parser | Nó AST | Teste Positivo | Teste Negativo | Estado |
|---|---|---|---|---|---|---|---|
| `CompactCompilationUnit` | Arquivo | `void main() { System.out.println("Olá"); }` | `parse_compact_compilation_unit` | `CompactCompilationUnit` | `test_java26_compilation_units.py`, `test_java26_class_members.py` | `test_java26_compilation_units.py`, `test_java26_class_members.py` | IMPLEMENTADO |
| `ImplicitlyDeclaredClass` | Classes | Arquivo sem `class` explícita contendo métodos de topo | `parse_compact_compilation_unit` | `ClassDeclaration (implicit_class)` | `test_java26_compilation_units.py`, `test_java26_class_members.py` | `test_java26_class_members.py` | IMPLEMENTADO |

---

## 3. Próximos Passos e Ordem de Implementação Normativa

1. **Etapa S1 — Nomes, Tipos e Generics** *(Concluída)*:
   - `TypeIdentifier` estrito;
   - Suporte completo a TypeParameters com bounds múltiplos (`T extends Number & Comparable<T>`);
   - Suporte completo a TypeArguments com Wildcards (`?`, `? extends T`, `? super T`);
   - Desambiguação de `>>` e `>>>` em tipos genéricos aninhados (`List<List<String>>`);
   - Suporte a Type Annotations no nó `TypeReference`.
2. **Etapa S2 — Unidades de Compilação, Pacotes e Módulos** *(Concluída)* (`module-info.java`, imports sob demanda e estáticos, unidades compactas).
3. **Etapa S3 & S3.1 — Classes, Membros, Construtores Flexíveis e Auditoria de Tipos** *(Concluída)* (`VariableDeclaratorList`, `ReceiverParameter`, `InstanceInitializer`, `StaticInitializer`, Flexible Constructor Bodies / JEP 513, JEP 456, early construction context).
4. **Etapa S4 — Interfaces Normais, Enums e Records** *(Concluída)* (`InterfaceDeclaration`, constantes/métodos `abstract`/`default`/`static`/`private`, `EnumDeclaration`/`EnumConstantBody`, `RecordDeclaration`/`RecordHeader`/`RecordComponent`/`VariableArityRecordComponent`, `NormalCanonicalConstructor`, `CompactConstructorDeclaration`, `NonCanonicalRecordConstructor`).
5. **Etapa S5 — Annotations e Annotation Interfaces** *(Concluída)* (`AnnotationInterfaceDeclaration`, `AnnotationInterfaceBody`, `AnnotationInterfaceElementDeclaration`, `AnnotationDefaultValue`, `MarkerAnnotation`, `SingleElementAnnotation`, `NormalAnnotation`, `ElementValue`, `ElementValuePair`, `ElementValueArrayInitializer`, `ClassLiteral`, *Type Annotations* em tipos/generics/arrays/casts/`instanceof`/`new`/`ReceiverParameter`/`TypeParameter`, meta-anotações `@Target`/`@Retention`/`@Repeatable` e auditoria S4 de enums/records).
6. **Etapa S6 — Blocos, Declarações Locais e Instruções Completas** *(Concluída, respeitando fronteiras S7/S8)* (`Block`, `BlockStatement`, `LocalClassOrInterfaceDeclaration`, `LocalVariableDeclaration`, `LocalVariableType` / `var` / `_`, `Statement` & `StatementNoShortIf` / *dangling else*, `StatementExpression` estrita, `LabeledStatement`, laços com `StatementExpressionList`, `TryStatement` / `CatchType` multi-catch / `ResourceSpecification` & `Resource` Java 9+, `SwitchBlock` / `SwitchBlockStatementGroup` / `SwitchRule` / `CaseLabel` / `DefaultLabel` / `case null` sem patterns S7, e `YieldStatement` com `SwitchExpression` auxiliar mínima).
7. **Etapa S7 & Auditoria S7.1 — Pattern Matching, Switch Moderno e Separação de Preview** *(Concluída)* (`Pattern`, `TypePattern`, `RecordPattern`, `ComponentPatternList`, `ComponentPattern`, `MatchAllPattern`, `Guard`/`when` contextual, `PatternCaseLabel`, `PatternInstanceOfExpression`, flow-scoping JLS §6.3, validação de record/aridade/genéricos, dominância JLS §14.30.3 / §14.11.1, exaustividade `sealed`/recursiva JLS §14.11.1.1 / §14.11.2 / §15.28.1 e separação estrita JEP 530 via `enable_preview_primitive_patterns=False`, rejeitando inclusive componentes primitivos de `RecordPattern` sem preview enquanto preserva `var` e `_`).
8. **Etapa S8 — Expressões Completas, Inferência de Tipos e Switch Expressions** *(Concluída)* (17 níveis de precedência JLS §15, promoções numéricas, estreitamento constante, l-values modificáveis, casts de interseção `(A & B)`, invocação com sobrecarga/herança/genéricos explícitos, diamond `<>`, `outer.new`, `AnonymousClassDeclaration`, criação e acesso a arrays JLS §15.10.1, `LambdaExpression` com `explicit`/`inferred`/`var` e captura efetivamente final, todas as 5 formas de `MethodReference` incluindo `int[]::new`, *poly-expressions* com target-typing e `SwitchExpression` integrada com `->` / `yield` / exaustividade).
9. **Etapa S9 — Integração Final e Auditoria**.
