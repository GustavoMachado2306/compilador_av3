"""Suíte de Testes para a Correção D3 — Inner Classes e Contexto Estático (JLS §15.9 / §15.9.2)."""

import unittest

from src.main import analyze_source


class TestJava26InnerClassesD3(unittest.TestCase):
    def test_01_valid_inner_and_static_nested_instantiations(self):
        code = """
        interface ComMembro {
            class MembroIface {}
        }
        class Outer {
            class Inner {
                class Deep {}
                void mkDeep() {
                    new Deep();
                }
            }
            static class Nested {
                class InnerOfStatic {}
                void mkOwn() {
                    new InnerOfStatic();
                }
            }
            static class SubNested extends Outer {
                void mkInheritedInner() {
                    new Inner();
                }
            }
            void inst() {
                new Inner();
                new Outer.Inner();
                new Nested();
                new Outer.Nested();
                new Inner().new Deep();
                new ComMembro.MembroIface();
            }
            static void stat() {
                new Nested();
                new Outer.Nested();
                new Outer().new Inner();
                new Outer().new Inner().new Deep();
                new ComMembro.MembroIface();
                Outer o = new Outer();
                o.new Inner();
            }
        }
        class Main {
            void run() {
                new Outer().new Inner();
                new Outer.Nested();
            }
        }
        """
        res = analyze_source(code)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_inner_class_without_enclosing_instance_rejected(self):
        defs = """
        class Outer {
            class Inner {
                class Deep {}
            }
            static class Nested {
                void badInStaticNested() {
                    new Inner();
                }
            }
            static Inner badStaticField = new Inner();
            static {
                new Inner();
            }
            static void stat1() {
                new Inner();
            }
            static void stat2() {
                new Outer.Inner();
            }
            static void stat3() {
                Runnable r = new Runnable() {
                    public void run() {
                        new Inner();
                    }
                };
            }
            static void stat4() {
                class LocalInStatic {
                    void m() {
                        new Inner();
                    }
                }
            }
            void instBadDeep() {
                new Inner.Deep();
            }
        }
        class Unrelated {
            void m() {
                new Outer.Inner();
            }
        }
        """
        snippets = [
            ("Nested -> Inner", "class Outer { class Inner {} static class Nested { void m() { new Inner(); } } }"),
            ("static field -> Inner", "class Outer { class Inner {} static Inner f = new Inner(); }"),
            ("static block -> Inner", "class Outer { class Inner {} static { new Inner(); } }"),
            ("static method -> Inner", "class Outer { class Inner {} static void m() { new Inner(); } }"),
            ("static method -> Outer.Inner", "class Outer { class Inner {} static void m() { new Outer.Inner(); } }"),
            (
                "anon in static -> Inner",
                "class Outer { class Inner {} static void m() { Object o = new Object() { void r() { new Inner(); } }; } }",
            ),
            (
                "local in static -> Inner",
                "class Outer { class Inner {} static void m() { class L { void r() { new Inner(); } } } }",
            ),
            (
                "Outer.inst -> Deep",
                "class Outer { class Inner { class Deep {} } void m() { new Inner.Deep(); } }",
            ),
            (
                "Unrelated -> Outer.Inner",
                "class Outer { class Inner {} } class Unrelated { void m() { new Outer.Inner(); } }",
            ),
            (
                "Outer.stat -> anon Inner subclass",
                "class Outer { class Inner {} static void m() { Object o = new Inner() {}; } }",
            ),
        ]
        for label, src in snippets:
            with self.subTest(case=label):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Esperado erro para: {label}")
        self.assertFalse(analyze_source(defs).success)

    def test_03_inherited_enclosing_and_qualified_static_nested_rejected(self):
        ok_sub = """
        class Outer {
            class Inner {}
        }
        class Sub extends Outer {
            void okInst() {
                new Inner();
            }
            static void okQual() {
                new Sub().new Inner();
            }
        }
        """
        res_ok = analyze_source(ok_sub)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_sub_static = """
        class Outer {
            class Inner {}
        }
        class Sub extends Outer {
            static void bad() {
                new Inner();
            }
        }
        """
        self.assertFalse(analyze_source(bad_sub_static).success)

        bad_qual_static = """
        interface ComI { class M {} }
        class Outer {
            static class Nested {}
            static void bad1() {
                new Outer().new Nested();
            }
            static void bad2(ComI ci) {
                ci.new M();
            }
        }
        """
        self.assertFalse(analyze_source(bad_qual_static).success)

    def test_04_local_and_anon_in_instance_context_plus_visibility(self):
        ok_inst = """
        class Outer {
            private class PrivInner {}
            class Inner {}
            void inst() {
                new PrivInner();
                class Local {
                    void ok() { new Inner(); }
                }
                Runnable r = new Runnable() {
                    public void run() { new Inner(); }
                };
            }
            static void statLocal() {
                class LocalOnly {}
                new LocalOnly();
            }
        }
        """
        res_ok = analyze_source(ok_inst)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        bad_priv = """
        class Outer {
            private class PrivInner {}
        }
        class Other {
            void m(Outer o) {
                o.new PrivInner();
            }
        }
        """
        self.assertFalse(analyze_source(bad_priv).success)


if __name__ == "__main__":
    unittest.main()
