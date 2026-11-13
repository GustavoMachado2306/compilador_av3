import unittest

from src.main import analyze_source


class TestJava26UnreachableCodeD6(unittest.TestCase):
    def _assert_ok(self, source: str):
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros inesperados: {res.semantic_errors} | {res.syntactic_error}")

    def _assert_unreachable(self, source: str):
        res = analyze_source(source)
        self.assertFalse(res.success, msg="Era esperado erro de código inalcançável.")
        self.assertTrue(
            any("inalcançável" in e and "JLS §14.22" in e for e in res.semantic_errors),
            msg=f"Erro esperado com JLS §14.22 não encontrado em: {res.semantic_errors}",
        )

    def test_01_return_throw_break_continue_sequenciais(self):
        self._assert_unreachable(
            """
            class A {
                int m() {
                    return 1;
                    int x = 2;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m() {
                    throw new RuntimeException();
                    int x = 1;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m(boolean c) {
                    while (c) {
                        break;
                        int x = 1;
                    }
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m(boolean c) {
                    for (int i = 0; i < 10; i++) {
                        continue;
                        System.out.println(i);
                    }
                }
            }
            """
        )

    def test_02_excecao_if_compilacao_condicional_jls_14_22(self):
        # JLS §14.22: if (false) { ... } e if (true) return; stmt; SÃO alcançáveis
        self._assert_ok(
            """
            class A {
                int m() {
                    if (false) {
                        return 0;
                    }
                    if (true) {
                        return 1;
                    }
                    return 2;
                }
            }
            """
        )
        self._assert_ok(
            """
            class A {
                int m() {
                    final boolean DEBUG = false;
                    if (DEBUG) {
                        System.out.println("debug");
                    }
                    if (true) return 10; else { int z = 0; }
                    return 20;
                }
            }
            """
        )
        # Ambos os ramos completando abruptamente -> código após if-else é inalcançável
        self._assert_unreachable(
            """
            class A {
                int m(boolean c) {
                    if (c) return 1;
                    else return 2;
                    return 3;
                }
            }
            """
        )

    def test_03_lacos_com_condicoes_constantes_e_break_continue(self):
        self._assert_unreachable(
            """
            class A {
                void m() {
                    while (false) {
                        int x = 1;
                    }
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m() {
                    for (; false; ) {
                        int x = 1;
                    }
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m() {
                    final boolean NEVER = false;
                    while (NEVER) {
                        System.out.println("dead");
                    }
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m() {
                    while (true) {
                        System.out.println("loop");
                    }
                    System.out.println("after");
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m() {
                    for (;;) {
                    }
                    int x = 1;
                }
            }
            """
        )
        # Com break alcançável, o código após while(true) / for(;;) é alcançável
        self._assert_ok(
            """
            class A {
                void m(boolean c) {
                    while (true) {
                        if (c) break;
                    }
                    System.out.println("reachable");
                }
            }
            """
        )
        # Break dentro de trecho inalcançável não torna while(true) alcançável após o laço
        self._assert_unreachable(
            """
            class A {
                void m() {
                    while (true) {
                        return;
                        break;
                    }
                }
            }
            """
        )
        # do-while(true): sem break não completa normalmente (mesmo com continue)
        self._assert_unreachable(
            """
            class A {
                void m(boolean c) {
                    do {
                        if (c) continue;
                    } while (true);
                    int x = 1;
                }
            }
            """
        )
        # do-while(false): válido e corpo alcançável
        self._assert_ok(
            """
            class A {
                void m() {
                    do {
                        int x = 1;
                    } while (false);
                    int y = 2;
                }
            }
            """
        )
        # Label com break externo
        self._assert_ok(
            """
            class A {
                void m(boolean c) {
                    externo:
                    while (true) {
                        while (true) {
                            if (c) break externo;
                        }
                    }
                    int ok = 1;
                }
            }
            """
        )

    def test_04_try_catch_finally_switch_lambda_e_inicializadores(self):
        self._assert_unreachable(
            """
            class A {
                int m() {
                    try {
                        return 1;
                    } catch (RuntimeException e) {
                        return 2;
                    }
                    return 3;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                int m(boolean c) {
                    try {
                        if (c) System.out.println("ok");
                    } finally {
                        return 9;
                    }
                    return 0;
                }
            }
            """
        )
        self._assert_ok(
            """
            class A {
                int m() {
                    try {
                        return 1;
                    } catch (RuntimeException e) {
                        int ok = 2;
                    }
                    return 3;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m(int x) {
                    switch (x) {
                        case 1:
                            return;
                            x = 2;
                        default:
                            return;
                    }
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                void m(int x) {
                    switch (x) {
                        case 1 -> { return; }
                        default -> { return; }
                    }
                    int after = 1;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                Runnable r = () -> {
                    return;
                    int x = 1;
                };
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                int m(int x) {
                    return switch (x) {
                        case 1 -> {
                            yield 10;
                            int dead = 2;
                        }
                        default -> 0;
                    };
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                static {
                    if (true) {
                        throw new RuntimeException();
                    } else {
                        throw new IllegalStateException();
                    }
                    int dead = 1;
                }
            }
            """
        )

    def test_05_enhanced_switch_vs_traditional_switch_jls_14_11_2_e_14_22(self):
        # 1. Enhanced com pattern incondicional sem guard (-> e :)
        self._assert_unreachable(
            """
            class A {
                int m(Object o) {
                    switch (o) {
                        case Object x -> { return 1; }
                    }
                    return 2;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            class A {
                int m(Object o) {
                    switch (o) {
                        case Object x:
                            return 1;
                    }
                    return 2;
                }
            }
            """
        )

        # 2 & 3. Enhanced exaustivo sobre hierarquia sealed SEM default (-> e :)
        self._assert_unreachable(
            """
            sealed interface S permits X, Y {}
            final class X implements S {}
            final class Y implements S {}
            class A {
                int m(S s) {
                    switch (s) {
                        case X x -> { return 1; }
                        case Y y -> { return 2; }
                    }
                    return 3;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            sealed interface S permits X, Y {}
            final class X implements S {}
            final class Y implements S {}
            class A {
                int m(S s) {
                    switch (s) {
                        case X x:
                            return 1;
                        case Y y:
                            return 2;
                    }
                    return 3;
                }
            }
            """
        )

        # 4. Enhanced com pattern guardado por 'when' e ramo complementar completando normalmente -> alcançável
        self._assert_ok(
            """
            class A {
                int m(Object o) {
                    switch (o) {
                        case Object x when o.hashCode() > 0 -> { return 1; }
                        case Object _ -> {}
                    }
                    return 2;
                }
            }
            """
        )

        # 5. Enhanced com pattern e default -> inalcançável quando todos os ramos abortam
        self._assert_unreachable(
            """
            class A {
                int m(Object o) {
                    switch (o) {
                        case String s -> { return 1; }
                        default -> { return 2; }
                    }
                    return 3;
                }
            }
            """
        )

        # 6 & 7. Contraste entre switch tradicional sem/com default e enum com/sem 'case null'
        self._assert_ok(
            """
            class A {
                int m(int x) {
                    switch (x) {
                        case 1 -> { return 1; }
                        case 2 -> { return 2; }
                    }
                    return 3;
                }
            }
            """
        )
        self._assert_ok(
            """
            enum E { A, B }
            class Test {
                int m(E e) {
                    switch (e) {
                        case A -> { return 1; }
                        case B -> { return 2; }
                    }
                    return 3;
                }
            }
            """
        )
        self._assert_unreachable(
            """
            enum E { A, B }
            class Test {
                int m(E e) {
                    switch (e) {
                        case null -> { return 0; }
                        case A -> { return 1; }
                        case B -> { return 2; }
                    }
                    return 3;
                }
            }
            """
        )

        # 8 & 9. Regras com throw, expressão e break alcançável
        self._assert_unreachable(
            """
            sealed interface S permits X {}
            final class X implements S {}
            class A {
                int m(S s) {
                    switch (s) {
                        case X x -> throw new RuntimeException();
                    }
                    return 1;
                }
            }
            """
        )
        self._assert_ok(
            """
            sealed interface S permits X {}
            final class X implements S {}
            class A {
                int m(S s) {
                    int y = 0;
                    switch (s) {
                        case X x -> y = 1;
                    }
                    return y;
                }
            }
            """
        )
        self._assert_ok(
            """
            sealed interface S permits X, Y {}
            final class X implements S {}
            final class Y implements S {}
            class A {
                int m(S s) {
                    switch (s) {
                        case X x -> { return 1; }
                        case Y y -> { break; }
                    }
                    return 2;
                }
            }
            """
        )


if __name__ == "__main__":
    unittest.main()
