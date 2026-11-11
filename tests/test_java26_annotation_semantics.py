"""
Suíte de Testes Automatizados para a Etapa S5 (e Auditoria Semântica S4 Herdada):
Validações semânticas de Annotations (@Target, @Repeatable, constantes, tipos, chaves, @interface)
e validações herdadas da Etapa S4 (Enum com métodos abstratos e Records com accessors explícitos).
Referência Normativa: JLS Java SE 26, Capítulos 8 (§8.9, §8.10), 9 (§9.6, §9.7).
"""

import unittest
from src.main import analyze_source


class TestJava26AnnotationSemanticsS5(unittest.TestCase):
    """Testes formais semânticos para Etapa S5 e auditoria S4 herdada."""

    # --- 1. @Target (JLS §9.6.4.1 / §9.7.4) ---

    def test_01_target_valido_em_alvos_corretos(self):
        source = """
        import java.lang.annotation.ElementType;
        import java.lang.annotation.Target;

        @Target({ElementType.FIELD, ElementType.METHOD})
        @interface Membro {}

        @Target(ElementType.TYPE)
        @interface SomenteTipo {}

        @Target(ElementType.PARAMETER)
        @interface ParamAnno {}

        @Target(ElementType.LOCAL_VARIABLE)
        @interface LocalAnno {}

        @Target(ElementType.TYPE_USE)
        @interface TypeUse {}

        @SomenteTipo
        @interface MetaSub {}

        @SomenteTipo
        class Exemplo {
            @Membro
            private int x;

            @Membro
            public @TypeUse String processar(@ParamAnno int n) {
                @LocalAnno int soma = n + 1;
                return (@TypeUse String) "ok";
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_erro_semantico_target_incompativel_declaracoes(self):
        casos = [
            (
                """
                @Target(ElementType.METHOD)
                @interface OnlyMethod {}
                @OnlyMethod
                class Ruim {}
                """,
                4,
                "OnlyMethod",
            ),
            (
                """
                @Target(ElementType.FIELD)
                @interface OnlyField {}
                class C {
                    @OnlyField
                    void m() {}
                }
                """,
                5,
                "OnlyField",
            ),
            (
                """
                @Target(ElementType.CONSTRUCTOR)
                @interface OnlyCtor {}
                class C {
                    @OnlyCtor
                    void m() {}
                }
                """,
                5,
                "OnlyCtor",
            ),
            (
                """
                @Target(ElementType.ANNOTATION_TYPE)
                @interface OnlyAnnType {}
                @OnlyAnnType
                class NotAnAnn {}
                """,
                4,
                "OnlyAnnType",
            ),
            (
                """
                @Target({})
                @interface NuncaPermitida {}
                class C {
                    @NuncaPermitida int x;
                }
                """,
                5,
                "NuncaPermitida",
            ),
        ]
        for src, linha, nome in casos:
            with self.subTest(nome=nome):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Deveria falhar: {nome}")
                self.assertTrue(
                    any(nome in e.message and e.line == linha for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_03_erro_semantico_type_use_em_void_ou_antes_de_modificador(self):
        src_void = """
        @Target(ElementType.TYPE_USE)
        @interface NonNull {}
        class A {
            @NonNull public void falha() {}
        }
        """
        res1 = analyze_source(src_void)
        self.assertFalse(res1.success)
        self.assertTrue(any("NonNull" in e.message and e.line == 5 for e in res1.semantic_errors), msg=res1.semantic_errors)

        src_pre_mod = """
        @Target(ElementType.TYPE_USE)
        @interface NonNull {}
        class B {
            @NonNull public String texto;
        }
        """
        res2 = analyze_source(src_pre_mod)
        self.assertFalse(res2.success)
        self.assertTrue(any("NonNull" in e.message and e.line == 5 for e in res2.semantic_errors), msg=res2.semantic_errors)

    def test_04_erro_semantico_declaration_only_em_contexto_type_use(self):
        casos = [
            """
            @Target(ElementType.FIELD)
            @interface FieldOnly {}
            class A {
                java.util.List<@FieldOnly String> xs;
            }
            """,
            """
            @Target(ElementType.FIELD)
            @interface FieldOnly {}
            class B {
                void f(Object o) {
                    String s = (@FieldOnly String) o;
                }
            }
            """,
            """
            @Target(ElementType.METHOD)
            @interface MethodOnly {}
            class C {
                void f() {
                    Object o = new @MethodOnly java.util.ArrayList<>();
                }
            }
            """,
            """
            @Target(ElementType.FIELD)
            @interface FieldOnly {}
            class D {
                int @FieldOnly [] arr;
            }
            """,
            """
            @Target(ElementType.PARAMETER)
            @interface ParamOnly {}
            class E {
                void f(int[] ns) {
                    for (@ParamOnly int n : ns) {}
                }
            }
            """,
            """
            @Target(ElementType.FIELD)
            @interface FieldOnly {}
            class F {
                java.util.List<? extends @FieldOnly Number> nums;
            }
            """,
        ]
        # Nota: ParamOnly em enhanced-for variable (LOCAL_VARIABLE) e FieldOnly em contextos TYPE_USE
        for src in casos:
            with self.subTest(src=src):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Deveria falhar:\n{src}")
                self.assertGreater(len(res.semantic_errors), 0)

    def test_05_enhanced_for_type_use_invalido_e_valido(self):
        src_ok = """
        @Target(ElementType.LOCAL_VARIABLE)
        @interface LoopVar {}
        @Target(ElementType.TYPE_USE)
        @interface NonZero {}
        class Ok {
            void f(int[] xs) {
                for (@LoopVar @NonZero int x : xs) {}
            }
        }
        """
        res_ok = analyze_source(src_ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        src_bad = """
        @Target(ElementType.METHOD)
        @interface OnlyMethod {}
        class Ruim {
            void f(int[] xs) {
                for (@OnlyMethod int x : xs) {}
            }
        }
        """
        res_bad = analyze_source(src_bad)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("OnlyMethod" in e.message and e.line == 6 for e in res_bad.semantic_errors), msg=res_bad.semantic_errors)

    # --- 2. @Repeatable (JLS §9.6.3 & §9.7.5) ---

    def test_06_repeatable_valido_e_erros_de_repeticao_ou_mistura(self):
        src_ok = """
        import java.lang.annotation.Repeatable;
        @Target({ElementType.TYPE, ElementType.METHOD})
        @interface Roles {
            Role[] value();
        }
        @Target({ElementType.TYPE, ElementType.METHOD})
        @Repeatable(Roles.class)
        @interface Role {
            String value();
        }
        @Role("ADMIN")
        @Role("AUDITOR")
        class Conta {}

        @Roles({ @Role("MANUAL") })
        class ContaManual {}
        """
        res_ok = analyze_source(src_ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        src_nao_repetivel = """
        @interface Tag { String value(); }
        @Tag("a")
        @Tag("b")
        class Ruim {}
        """
        res_nr = analyze_source(src_nao_repetivel)
        self.assertFalse(res_nr.success)
        self.assertTrue(any("Tag" in e.message for e in res_nr.semantic_errors), msg=res_nr.semantic_errors)

        src_override_dup = """
        class Sub {
            @Override
            @Override
            public String toString() { return "x"; }
        }
        """
        res_ov = analyze_source(src_override_dup)
        self.assertFalse(res_ov.success)
        self.assertTrue(any("Override" in e.message for e in res_ov.semantic_errors), msg=res_ov.semantic_errors)

        src_mistura = """
        @interface Roles { Role[] value(); }
        @Repeatable(Roles.class)
        @interface Role { String value(); }
        @Role("ADMIN")
        @Roles({ @Role("USER") })
        class Mistura {}
        """
        res_mix = analyze_source(src_mistura)
        self.assertFalse(res_mix.success)
        self.assertTrue(any("Role" in e.message for e in res_mix.semantic_errors), msg=res_mix.semantic_errors)

    def test_07_erro_semantico_container_repeatable_invalido(self):
        casos = [
            # Container sem metodo value()
            """
            @interface Roles { Role[] items(); }
            @Repeatable(Roles.class)
            @interface Role { String value(); }
            """,
            # Container com value() de tipo errado
            """
            @interface Roles { String[] value(); }
            @Repeatable(Roles.class)
            @interface Role { String value(); }
            """,
            # Container com elemento obrigatorio adicional sem default
            """
            @interface Roles { Role[] value(); String extra(); }
            @Repeatable(Roles.class)
            @interface Role { String value(); }
            """,
            # Retention menor no container (SOURCE < RUNTIME)
            """
            @Retention(RetentionPolicy.SOURCE)
            @interface Roles { Role[] value(); }
            @Retention(RetentionPolicy.RUNTIME)
            @Repeatable(Roles.class)
            @interface Role { String value(); }
            """,
            # Target mais amplo no container que na repetivel
            """
            @Target({ElementType.TYPE, ElementType.METHOD})
            @interface Roles { Role[] value(); }
            @Target(ElementType.METHOD)
            @Repeatable(Roles.class)
            @interface Role { String value(); }
            """,
        ]
        for src in casos:
            with self.subTest(src=src):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Container inválido deveria falhar:\n{src}")
                self.assertGreater(len(res.semantic_errors), 0)

    # --- 3. Chaves, Elementos Obrigatórios, Constantes e Tipos (JLS §9.7.1–§9.7.3) ---

    def test_08_erro_semantico_elemento_obrigatorio_desconhecido_duplicado_e_value(self):
        src_falta = """
        @interface Autor { String nome(); int ano() default 2026; }
        @Autor(ano = 2025)
        class Livro {}
        """
        res1 = analyze_source(src_falta)
        self.assertFalse(res1.success)
        self.assertTrue(any("nome" in e.message and e.line == 3 for e in res1.semantic_errors), msg=res1.semantic_errors)

        src_desc = """
        @interface Autor { String nome(); }
        @Autor(nome = "Ana", desconhecido = 1)
        class Livro {}
        """
        res2 = analyze_source(src_desc)
        self.assertFalse(res2.success)
        self.assertTrue(any("desconhecido" in e.message for e in res2.semantic_errors), msg=res2.semantic_errors)

        src_dup_chave = """
        @interface Autor { String nome(); }
        @Autor(nome = "A", nome = "B")
        class Livro {}
        """
        res3 = analyze_source(src_dup_chave)
        self.assertFalse(res3.success)
        self.assertTrue(any("nome" in e.message for e in res3.semantic_errors), msg=res3.semantic_errors)

        src_sem_value = """
        @interface Autor { String nome(); }
        @Autor("Ana")
        class Livro {}
        """
        res4 = analyze_source(src_sem_value)
        self.assertFalse(res4.success)
        self.assertTrue(any("value" in e.message for e in res4.semantic_errors), msg=res4.semantic_errors)

    def test_09_erro_semantico_valores_nao_constantes_e_tipos_incompativeis(self):
        src_nao_const = """
        @interface Info { String value(); }
        class Dados {
            static String gerar() { return "x"; }
            static String naoFinal = "y";
            String campoMutavel = "z";
            static final String CONST_OK = "ok";

            @Info(gerar()) int a;
            @Info(naoFinal) int b;
            @Info(new String("x")) int c;
            @Info(null) int d;
            @Info(CONST_OK) int e;
        }
        """
        res_nc = analyze_source(src_nao_const)
        self.assertFalse(res_nc.success)
        linhas_erradas = {e.line for e in res_nc.semantic_errors}
        self.assertEqual(linhas_erradas, {9, 10, 11, 12}, msg=res_nc.semantic_errors)

        src_tipos = """
        enum A { X }
        enum B { Y }
        @interface Cfg {
            String texto() default "a";
            int numero() default 0;
            boolean flag() default true;
            Class<? extends Number> numCls() default Integer.class;
            A enumerado() default A.X;
        }
        @Cfg(texto = 1, numero = "errado", flag = 1, numCls = String.class, enumerado = B.Y)
        class Alvo {}
        """
        res_t = analyze_source(src_tipos)
        self.assertFalse(res_t.success)
        self.assertGreaterEqual(len(res_t.semantic_errors), 5, msg=res_t.semantic_errors)

    def test_10_shorthand_elemento_unico_para_array_valido(self):
        source = """
        @interface Tags {
            String[] value();
        }
        @Tags("unico")
        class Artigo {}
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    # --- 4. AUDITORIA SEMÂNTICA HERDADA DA ETAPA S4 (ENUM & RECORD) ---

    def test_11_audit_s4_enum_metodo_abstrato_exige_constantes_e_implementacao(self):
        # 1. Enum com metodo abstrato sem constantes -> erro semantico
        src_sem_const = """
        enum Vazio {
            ;
            abstract int calcular();
        }
        """
        res1 = analyze_source(src_sem_const)
        self.assertFalse(res1.success)
        self.assertTrue(any("abstrato" in e.message.lower() for e in res1.semantic_errors), msg=res1.semantic_errors)

        # 2. Constante sem corpo quando enum declara metodo abstrato -> erro semantico
        src_sem_corpo = """
        enum Operacao {
            SOMA { int aplicar(int a, int b) { return a + b; } },
            SUB;
            abstract int aplicar(int a, int b);
        }
        """
        res2 = analyze_source(src_sem_corpo)
        self.assertFalse(res2.success)
        self.assertTrue(any("SUB" in e.message for e in res2.semantic_errors), msg=res2.semantic_errors)

        # 3. Constante com corpo que nao implementa metodo abstrato -> erro semantico
        src_corpo_incompleto = """
        enum Operacao {
            SOMA { int outro() { return 0; } };
            abstract int aplicar(int a, int b);
        }
        """
        res3 = analyze_source(src_corpo_incompleto)
        self.assertFalse(res3.success)
        self.assertTrue(any("aplicar" in e.message for e in res3.semantic_errors), msg=res3.semantic_errors)

        # 4. Caso valido completo
        src_ok = """
        enum Operacao {
            SOMA { public int aplicar(int a, int b) { return a + b; } },
            SUB  { public int aplicar(int a, int b) { return a - b; } };
            abstract int aplicar(int a, int b);
        }
        """
        res4 = analyze_source(src_ok)
        self.assertTrue(res4.success, msg=res4.semantic_errors)

    def test_12_audit_s4_record_accessor_explicito_validacoes(self):
        # 1. Accessor explicito deve ser public
        src_priv = """
        record Ponto(int x, int y) {
            private int x() { return x; }
        }
        """
        res1 = analyze_source(src_priv)
        self.assertFalse(res1.success)
        self.assertTrue(any("public" in e.message.lower() and e.line == 3 for e in res1.semantic_errors), msg=res1.semantic_errors)

        # 2. Accessor explicito nao pode ser static
        src_stat = """
        record Ponto(int x, int y) {
            public static int x() { return 0; }
        }
        """
        res2 = analyze_source(src_stat)
        self.assertFalse(res2.success)
        self.assertTrue(any("static" in e.message.lower() and e.line == 3 for e in res2.semantic_errors), msg=res2.semantic_errors)

        # 3. Accessor explicito nao pode ter throws
        src_throws = """
        record Ponto(int x, int y) {
            public int x() throws Exception { return x; }
        }
        """
        res3 = analyze_source(src_throws)
        self.assertFalse(res3.success)
        self.assertTrue(any("throws" in e.message.lower() and e.line == 3 for e in res3.semantic_errors), msg=res3.semantic_errors)

        # 4. Accessor explicito nao pode declarar type parameters
        src_tp = """
        record Ponto(int x, int y) {
            public <T> int x() { return x; }
        }
        """
        res4 = analyze_source(src_tp)
        self.assertFalse(res4.success)
        self.assertTrue(any("tipo" in e.message.lower() and e.line == 3 for e in res4.semantic_errors), msg=res4.semantic_errors)

        # 5. Accessor explicito deve ter o mesmo tipo de retorno do componente
        src_ret = """
        record Ponto(int x, int y) {
            public String x() { return ""; }
        }
        """
        res5 = analyze_source(src_ret)
        self.assertFalse(res5.success)
        self.assertTrue(any("retornar" in e.message.lower() and e.line == 3 for e in res5.semantic_errors), msg=res5.semantic_errors)

        # 6. Accessor explicito valido
        src_ok = """
        record Ponto(int x, int y) {
            @Override
            public int x() { return x; }
        }
        """
        res6 = analyze_source(src_ok)
        self.assertTrue(res6.success, msg=res6.semantic_errors)


if __name__ == "__main__":
    unittest.main()
