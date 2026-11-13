import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import analyze_source, analyze_sources


class TestJava26InheritanceAccessS15(unittest.TestCase):
    """Testes abrangentes para a Etapa S15 — Controle de Acesso, Herança e Sobrescrita (JLS §§6.6, 8.1, 8.3, 8.4, 8.8, 9.4, 9.6.4.4)."""

    # ------------------------------------------------------------------
    # Exemplos obrigatórios + Controle de acesso private / package / public
    # ------------------------------------------------------------------
    def test_01_exemplo_obrigatorio_private_nao_acessivel_em_subclasse(self):
        source = """
        class A {
            private int valor = 10;
        }
        class B extends A {
            int ler(A objeto) {
                return objeto.valor;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(
            any("private" in str(e).lower() and "valor" in str(e) for e in res.semantic_errors),
            msg=res.semantic_errors,
        )

    def test_02_private_nao_herdado_por_subclasse_e_acessivel_em_nestmate(self):
        bad = """
        class A {
            private int valor = 10;
            private void segredo() {}
        }
        class B extends A {
            int ler() {
                segredo();
                return valor;
            }
        }
        """
        res_bad = analyze_source(bad)
        self.assertFalse(res_bad.success)

        good_nestmate = """
        class Externa {
            private int x = 42;
            class Interna {
                int ler(Externa e) {
                    return e.x;
                }
            }
        }
        """
        res_good = analyze_source(good_nestmate)
        self.assertTrue(res_good.success, msg=res_good.semantic_errors)

    def test_03_exemplo_obrigatorio_sobrescrever_metodo_final_erro(self):
        source = """
        class A {
            final void executar() {}
        }
        class B extends A {
            void executar() {}
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(
            any("final" in str(e).lower() and "executar" in str(e) for e in res.semantic_errors),
            msg=res.semantic_errors,
        )

    def test_04_exemplo_obrigatorio_retorno_covariante_valido_e_incompativel_erro(self):
        good = """
        class A {
            Number obter() { return 10; }
        }
        class B extends A {
            @Override
            Integer obter() { return 10; }
        }
        """
        res_good = analyze_source(good)
        self.assertTrue(res_good.success, msg=res_good.semantic_errors)

        bad_ref = """
        class A {
            Number obter() { return 10; }
        }
        class B extends A {
            @Override
            String obter() { return "x"; }
        }
        """
        res_bad_ref = analyze_source(bad_ref)
        self.assertFalse(res_bad_ref.success)

        bad_prim = """
        class A {
            int numero() { return 1; }
        }
        class B extends A {
            @Override
            long numero() { return 1L; }
        }
        """
        res_bad_prim = analyze_source(bad_prim)
        self.assertFalse(res_bad_prim.success)

    # ------------------------------------------------------------------
    # Multi-pacote, visibilidade de tipos, protected cross-package (JLS §6.6.2)
    # ------------------------------------------------------------------
    def test_05_controle_acesso_entre_pacotes_tipos_e_membros(self):
        pkg_a = """
        package pkgA;
        public class Publica {
            public int pub = 1;
            protected int prot = 2;
            int pkg = 3;
            private int priv = 4;
            public void mPub() {}
            protected void mProt() {}
            void mPkg() {}
            private void mPriv() {}
        }
        class Secreta {}
        """
        pkg_b_same_bad = """
        package pkgB;
        import pkgA.Publica;
        class Consumidor {
            void usar(Publica p) {
                int x = p.pkg;
                p.mPkg();
                p.mProt();
                p.mPriv();
            }
        }
        """
        res = analyze_sources([pkg_a, pkg_b_same_bad])
        self.assertFalse(res.success)
        msgs = " | ".join(str(e) for e in res.semantic_errors)
        self.assertIn("pkg", msgs)
        self.assertIn("mPkg", msgs)
        self.assertIn("mProt", msgs)
        self.assertIn("mPriv", msgs)

        pkg_b_inaccessible_type = """
        package pkgB;
        class Outra {
            pkgA.Secreta s;
        }
        """
        res_type = analyze_sources([pkg_a, pkg_b_inaccessible_type])
        self.assertFalse(res_type.success)

    def test_06_protected_entre_pacotes_regra_do_receptor_jls_6_6_2(self):
        pkg_a = """
        package pkgA;
        public class Base {
            protected int campo = 5;
            protected Base() {}
            protected void metodo() {}
        }
        """
        pkg_b_valid = """
        package pkgB;
        import pkgA.Base;
        public class Sub extends Base {
            public Sub() {
                super();
            }
            void valido(Sub s) {
                int a = campo;
                int b = this.campo;
                int c = super.campo;
                int d = s.campo;
                metodo();
                super.metodo();
                s.metodo();
                Base anon = new Base() {};
            }
        }
        """
        res_valid = analyze_sources([pkg_a, pkg_b_valid])
        self.assertTrue(res_valid.success, msg=res_valid.semantic_errors)

        pkg_b_invalid = """
        package pkgB;
        import pkgA.Base;
        public class SubRuim extends Base {
            void invalido(Base b) {
                int x = b.campo;
                b.metodo();
                Base outro = new Base();
            }
        }
        """
        res_invalid = analyze_sources([pkg_a, pkg_b_invalid])
        self.assertFalse(res_invalid.success)
        self.assertGreaterEqual(len(res_invalid.semantic_errors), 3, msg=res_invalid.semantic_errors)

    def test_07_mesmo_pacote_acessa_package_private_e_protected_livremente(self):
        u1 = """
        package app;
        class Helper {
            protected int prot = 7;
            int pkg = 8;
            void ajudar() {}
        }
        """
        u2 = """
        package app;
        public class Principal {
            int testar() {
                Helper h = new Helper();
                h.ajudar();
                return h.prot + h.pkg;
            }
        }
        """
        res = analyze_sources([u1, u2])
        self.assertTrue(res.success, msg=res.semantic_errors)

    # ------------------------------------------------------------------
    # Herança de tipos: final class, ciclos, class vs interface, fields hiding
    # ------------------------------------------------------------------
    def test_08_hierarquia_classe_final_ciclo_e_misuse_interface(self):
        res_final = analyze_source("""
        final class Imutavel {}
        class Tentativa extends Imutavel {}
        """)
        self.assertFalse(res_final.success)

        res_cycle = analyze_source("""
        class A extends B {}
        class B extends A {}
        """)
        self.assertFalse(res_cycle.success)

        res_iface_cycle = analyze_source("""
        interface I1 extends I2 {}
        interface I2 extends I1 {}
        """)
        self.assertFalse(res_iface_cycle.success)

        res_misuse = analyze_source("""
        interface Contrato {}
        class Normal {}
        class Err1 extends Contrato {}
        class Err2 implements Normal {}
        """)
        self.assertFalse(res_misuse.success)
        self.assertGreaterEqual(len(res_misuse.semantic_errors), 2)

    def test_09_acesso_campo_herdado_e_ocultacao_de_campos(self):
        source = """
        class Base {
            int valor = 100;
            String texto = "oi";
        }
        class Sub extends Base {
            String valor = "escondido";
            void testar() {
                int herdadoSuper = super.valor;
                String proprio = valor;
                String semQualif = texto;
                int viaCast = ((Base) this).valor;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    # ------------------------------------------------------------------
    # Ocultação estática vs sobrescrita, private/package cross-pkg, visibilidade
    # ------------------------------------------------------------------
    def test_10_ocultacao_metodos_estaticos_e_incompatibilidade_instancia(self):
        good = """
        class A {
            static int f() { return 1; }
        }
        class B extends A {
            static int f() { return 2; }
        }
        """
        self.assertTrue(analyze_source(good).success)

        bad_inst_over_static = """
        class A {
            static void f() {}
        }
        class B extends A {
            void f() {}
        }
        """
        self.assertFalse(analyze_source(bad_inst_over_static).success)

        bad_static_over_inst = """
        class A {
            void f() {}
        }
        class B extends A {
            static void f() {}
        }
        """
        self.assertFalse(analyze_source(bad_static_over_inst).success)

        bad_override_on_static = """
        class A {
            static void f() {}
        }
        class B extends A {
            @Override
            static void f() {}
        }
        """
        self.assertFalse(analyze_source(bad_override_on_static).success)

    def test_11_visibilidade_na_sobrescrita_e_nao_sobrescrita_cross_package(self):
        narrowing = """
        class A {
            public void p() {}
            protected void r() {}
        }
        class B extends A {
            protected void p() {}
            void r() {}
        }
        """
        res_nar = analyze_source(narrowing)
        self.assertFalse(res_nar.success)
        self.assertGreaterEqual(len(res_nar.semantic_errors), 2)

        widening = """
        class A {
            void pkg() {}
            protected void prot() {}
        }
        class B extends A {
            @Override
            protected void pkg() {}
            @Override
            public void prot() {}
        }
        """
        res_wid = analyze_source(widening)
        self.assertTrue(res_wid.success, msg=res_wid.semantic_errors)

        # Em pacotes distintos, método package-private de A não é sobrescrito por B
        pkg_a = """
        package pkgA;
        public class A {
            int f() { return 1; }
        }
        """
        pkg_b = """
        package pkgB;
        import pkgA.A;
        public class B extends A {
            String f() { return "nao sobrescreve"; }
        }
        """
        self.assertTrue(analyze_sources([pkg_a, pkg_b]).success)

        # Porém com @Override em B falha pois f() de pkgA.A não foi herdado
        pkg_b_ovr = """
        package pkgB;
        import pkgA.A;
        public class B extends A {
            @Override
            int f() { return 2; }
        }
        """
        self.assertFalse(analyze_sources([pkg_a, pkg_b_ovr]).success)

    # ------------------------------------------------------------------
    # Abstract methods/classes e implementação obrigatória de contratos
    # ------------------------------------------------------------------
    def test_12_validacao_metodos_abstratos_e_implementacao_obrigatoria(self):
        bad_mods = """
        abstract class A {
            abstract private void m1();
            abstract static void m2();
            abstract final void m3();
            abstract void m4() {}
        }
        class Concreta {
            abstract void proibido();
        }
        """
        res_mods = analyze_source(bad_mods)
        self.assertFalse(res_mods.success)
        self.assertGreaterEqual(len(res_mods.semantic_errors), 5)

        bad_unimpl = """
        interface Tarefa {
            void executar();
        }
        class Executor implements Tarefa {
        }
        """
        self.assertFalse(analyze_source(bad_unimpl).success)

        bad_anon = """
        interface Tarefa {
            void executar();
        }
        class Uso {
            void rodar() {
                Tarefa t = new Tarefa() {};
            }
        }
        """
        self.assertFalse(analyze_source(bad_anon).success)

        bad_enum = """
        interface Tarefa {
            void executar();
        }
        enum Estado implements Tarefa {
            ATIVO, INATIVO;
        }
        """
        self.assertFalse(analyze_source(bad_enum).success)

        good_enum_const_impl = """
        interface Tarefa {
            void executar();
        }
        enum Estado implements Tarefa {
            ATIVO {
                @Override
                public void executar() {}
            },
            INATIVO {
                @Override
                public void executar() {}
            };
        }
        """
        res_enum = analyze_source(good_enum_const_impl)
        self.assertTrue(res_enum.success, msg=res_enum.semantic_errors)

    # ------------------------------------------------------------------
    # Conflitos de interfaces, métodos default, Object & Interface.super.m()
    # ------------------------------------------------------------------
    def test_13_conflitos_default_abstract_e_resolucao_interface_super(self):
        diamond_conflict = """
        interface I1 {
            default String nome() { return "I1"; }
        }
        interface I2 {
            default String nome() { return "I2"; }
        }
        class Impl implements I1, I2 {}
        """
        res_diam = analyze_source(diamond_conflict)
        self.assertFalse(res_diam.success)

        default_vs_abstract = """
        interface I1 {
            default void acao() {}
        }
        interface I2 {
            void acao();
        }
        class Impl implements I1, I2 {}
        """
        res_da = analyze_source(default_vs_abstract)
        self.assertFalse(res_da.success)

        resolved_via_super = """
        interface I1 {
            default String nome() { return "I1"; }
        }
        interface I2 {
            default String nome() { return "I2"; }
        }
        class Impl implements I1, I2 {
            @Override
            public String nome() {
                return I1.super.nome();
            }
        }
        """
        res_ok = analyze_source(resolved_via_super)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_default_object = """
        interface Ruim {
            default String toString() { return "x"; }
        }
        """
        self.assertFalse(analyze_source(bad_default_object).success)

        bad_non_direct_super = """
        interface A {
            default void f() {}
        }
        interface B extends A {}
        class C implements B {
            void g() {
                A.super.f();
            }
        }
        """
        self.assertFalse(analyze_source(bad_non_direct_super).success)

        bad_iface_class_non_public = """
        interface I {
            void m();
        }
        class Pai {
            void m() {}
        }
        class Filho extends Pai implements I {}
        """
        self.assertFalse(analyze_source(bad_iface_class_non_public).success)

    def test_14_interface_static_nao_herdada(self):
        source = """
        interface Util {
            static int somar(int a, int b) { return a + b; }
        }
        class Cliente implements Util {
            int usar() {
                return Util.somar(1, 2);
            }
        }
        """
        self.assertTrue(analyze_source(source).success)

        bad_via_sub = """
        interface Util {
            static int somar(int a, int b) { return a + b; }
        }
        class Cliente implements Util {
            int usar() {
                return Cliente.somar(1, 2);
            }
        }
        """
        self.assertFalse(analyze_source(bad_via_sub).success)

    # ------------------------------------------------------------------
    # @Override e regras de construtores / this() / super() / MethodRef
    # ------------------------------------------------------------------
    def test_15_override_validacoes_interface_object_e_externos(self):
        good_iface_obj = """
        interface Entidade {
            @Override
            String toString();
        }
        """
        self.assertTrue(analyze_source(good_iface_obj).success)

        bad_override_missing = """
        class A {
            @Override
            void inexistente() {}
        }
        """
        self.assertFalse(analyze_source(bad_override_missing).success)

        bad_override_private = """
        class A {
            private void p() {}
        }
        class B extends A {
            @Override
            private void p() {}
        }
        """
        self.assertFalse(analyze_source(bad_override_private).success)

    def test_16_construtores_modificadores_acesso_e_ciclos_this(self):
        bad_mods = """
        class A {
            static A() {}
            final A(int x) {}
            abstract A(String s) {}
        }
        """
        res_mods = analyze_source(bad_mods)
        self.assertFalse(res_mods.success)
        self.assertGreaterEqual(len(res_mods.semantic_errors), 3)

        bad_private_ctor = """
        class Singleton {
            private Singleton() {}
        }
        class Uso extends Singleton {
            void criar() {
                Singleton s = new Singleton();
            }
        }
        """
        res_priv_ctor = analyze_source(bad_private_ctor)
        self.assertFalse(res_priv_ctor.success)
        self.assertGreaterEqual(len(res_priv_ctor.semantic_errors), 2)

        bad_cycle = """
        class Ciclo {
            Ciclo() { this(1); }
            Ciclo(int x) { this(); }
        }
        """
        res_cycle = analyze_source(bad_cycle)
        self.assertFalse(res_cycle.success)
        self.assertTrue(
            any("recursiv" in str(e).lower() for e in res_cycle.semantic_errors),
            msg=res_cycle.semantic_errors,
        )

    def test_17_acesso_membros_em_method_reference_e_object_final_methods(self):
        bad_obj_final = """
        class Sub extends Object {
            void notifyAll() {}
        }
        """
        self.assertFalse(analyze_source(bad_obj_final).success)

        bad_mref_private = """
        import java.util.function.Supplier;
        class Segredo {
            private String ler() { return "x"; }
        }
        class Outro {
            void testar(Segredo s) {
                Supplier<String> sup = s::ler;
            }
        }
        """
        self.assertFalse(analyze_source(bad_mref_private).success)


if __name__ == "__main__":
    unittest.main()

