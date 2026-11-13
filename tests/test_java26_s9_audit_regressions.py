import unittest
from src.main import analyze_source


class TestJava26S9AuditRegressions(unittest.TestCase):
    """Regressões da Auditoria Final S9: synchronized, throw, var void e verificações cruzadas."""

    def test_01_synchronized_requires_reference_type_not_primitive_or_void(self):
        ok_src = """
        class Sync {
            void m(Object lock) {
                synchronized (lock) {}
                synchronized (this) {}
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_int = "class Sync { void m() { synchronized (123) {} } }"
        bad_bool = "class Sync { void m() { synchronized (true) {} } }"
        bad_void = "class Sync { void p() {} void m() { synchronized (p()) {} } }"
        self.assertFalse(analyze_source(bad_int).success)
        self.assertFalse(analyze_source(bad_bool).success)
        self.assertFalse(analyze_source(bad_void).success)

    def test_02_throw_requires_throwable_subtype(self):
        ok_src = """
        class CustomEx extends RuntimeException {}
        class Thr {
            void m() {
                if (false) throw new IllegalArgumentException("x");
                throw new CustomEx();
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)

        bad_int = "class Thr { void m() { throw 42; } }"
        bad_str = 'class Thr { void m() { throw "erro"; } }'
        bad_cls = "class NaoExcecao {} class Thr { void m() { throw new NaoExcecao(); } }"
        self.assertFalse(analyze_source(bad_int).success)
        self.assertFalse(analyze_source(bad_str).success)
        self.assertFalse(analyze_source(bad_cls).success)

    def test_03_var_local_with_void_initializer_rejected(self):
        bad = """
        class V {
            void ping() {}
            void m() {
                var x = ping();
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_04_anonymous_class_return_and_break_isolation(self):
        ok_src = """
        class Iso {
            void m() {
                Runnable r = new Runnable() {
                    public void run() {
                        return;
                    }
                };
            }
        }
        """
        bad_ret = """
        class Iso {
            void m() {
                Runnable r = new Runnable() {
                    public void run() {
                        return 1;
                    }
                };
            }
        }
        """
        bad_break = """
        class Iso {
            void m() {
                for (;;) {
                    Runnable r = new Runnable() {
                        public void run() {
                            break;
                        }
                    };
                }
            }
        }
        """
        self.assertTrue(analyze_source(ok_src).success)
        self.assertFalse(analyze_source(bad_ret).success)
        self.assertFalse(analyze_source(bad_break).success)

    def test_05_pattern_variable_does_not_leak_outside_if(self):
        bad = """
        class Pat {
            void m(Object o) {
                if (o instanceof String s) {}
                int n = s.length();
            }
        }
        """
        self.assertFalse(analyze_source(bad).success)

    def test_06_preview_isolation_remains_strict_by_default(self):
        src_prim = "class P { boolean f(Object o) { return o instanceof int i; } }"
        src_rec_prim = "record R(int x) {} class P { boolean f(Object o) { return o instanceof R(int x); } }"
        src_rec_conv = "record R(int x) {} class P { boolean f(Object o) { return o instanceof R(long x); } }"
        src_rec_var = "record R(int x) {} class P { boolean f(Object o) { return o instanceof R(var x); } }"
        self.assertFalse(analyze_source(src_prim, enable_preview_primitive_patterns=False).success)
        self.assertFalse(analyze_source(src_rec_prim, enable_preview_primitive_patterns=False).success)
        self.assertFalse(analyze_source(src_rec_conv, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src_rec_var, enable_preview_primitive_patterns=False).success)
        self.assertTrue(analyze_source(src_prim, enable_preview_primitive_patterns=True).success)
        self.assertTrue(analyze_source(src_rec_prim, enable_preview_primitive_patterns=True).success)
        self.assertTrue(analyze_source(src_rec_conv, enable_preview_primitive_patterns=True).success)


if __name__ == "__main__":
    unittest.main()

