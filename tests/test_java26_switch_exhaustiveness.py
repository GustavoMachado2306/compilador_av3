"""
Suíte S7.7 — Exaustividade de Switch Expressions e Enhanced Switch Statements (JLS §14.11.1.1 / §14.11.2 / §15.28.1).
Cobre sealed hierarchies (explícitas e implícitas, multinível), records aninhados, enums, guards e fallback clássico.
"""

import unittest
from src.main import analyze_source


class TestJava26SwitchExhaustiveness(unittest.TestCase):
    """Testes de exaustividade para switch com patterns e hierarquias fechadas."""

    def test_01_sealed_com_permits_explicito_exaustivo_e_incompleto(self):
        ok = """
        sealed interface Forma permits Circulo, Retangulo {}
        record Circulo(double raio) implements Forma {}
        final class Retangulo implements Forma {}
        class Demo {
            double area(Forma f) {
                return switch (f) {
                    case Circulo(var r) -> 3.14 * r * r;
                    case Retangulo _ -> 10.0;
                };
            }
            void stmt(Forma f) {
                switch (f) {
                    case Circulo c -> System.out.println(c);
                    case Retangulo r -> System.out.println(r);
                }
            }
        }
        """
        res_ok = analyze_source(ok)
        self.assertTrue(res_ok.success, msg=f"Erros: {res_ok.semantic_errors}")

        missing_case = """
        sealed interface Forma permits Circulo, Retangulo {}
        record Circulo(double raio) implements Forma {}
        final class Retangulo implements Forma {}
        class Demo {
            double area(Forma f) {
                return switch (f) {
                    case Circulo(var r) -> r;
                };
            }
        }
        """
        res_bad = analyze_source(missing_case)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("exaustiv" in str(e).lower() for e in res_bad.semantic_errors))

    def test_02_sealed_multinivel_e_sem_permits_implicito(self):
        multilevel_ok = """
        sealed interface Expr permits Num, Op {}
        record Num(int v) implements Expr {}
        sealed interface Op extends Expr permits Soma, Sub {}
        record Soma(Expr e, Expr d) implements Op {}
        record Sub(Expr e, Expr d) implements Op {}
        class Demo {
            int eval(Expr e) {
                return switch (e) {
                    case Num(var v) -> v;
                    case Soma(var a, var b) -> 1;
                    case Sub(var a, var b) -> 2;
                };
            }
        }
        """
        self.assertTrue(analyze_source(multilevel_ok).success)

        multilevel_missing = """
        sealed interface Expr permits Num, Op {}
        record Num(int v) implements Expr {}
        sealed interface Op extends Expr permits Soma, Sub {}
        record Soma(Expr e, Expr d) implements Op {}
        record Sub(Expr e, Expr d) implements Op {}
        class Demo {
            void eval(Expr e) {
                switch (e) {
                    case Num(var v) -> {}
                    case Soma(var a, var b) -> {}
                }
            }
        }
        """
        res_missing = analyze_source(multilevel_missing)
        self.assertFalse(res_missing.success)
        self.assertTrue(any("exaustiv" in str(e).lower() for e in res_missing.semantic_errors))

        implicit_permits_ok = """
        sealed interface Sinal {}
        record Verde() implements Sinal {}
        record Vermelho() implements Sinal {}
        class Demo {
            String cor(Sinal s) {
                return switch (s) {
                    case Verde() -> "ir";
                    case Vermelho() -> "parar";
                };
            }
        }
        """
        self.assertTrue(analyze_source(implicit_permits_ok).success)

    def test_03_exaustividade_recursiva_em_record_patterns_sobre_sealed(self):
        complete_par = """
        sealed interface Cor permits Vermelho, Azul {}
        record Vermelho() implements Cor {}
        record Azul() implements Cor {}
        record Par(Cor a, Cor b) {}
        class Demo {
            int codigo(Par p) {
                return switch (p) {
                    case Par(Vermelho _, _) -> 1;
                    case Par(Azul _, Vermelho _) -> 2;
                    case Par(Azul _, Azul _) -> 3;
                };
            }
        }
        """
        res_ok = analyze_source(complete_par)
        self.assertTrue(res_ok.success, msg=f"Erros: {res_ok.semantic_errors}")

        incomplete_par = """
        sealed interface Cor permits Vermelho, Azul {}
        record Vermelho() implements Cor {}
        record Azul() implements Cor {}
        record Par(Cor a, Cor b) {}
        class Demo {
            int codigo(Par p) {
                return switch (p) {
                    case Par(Vermelho _, Vermelho _) -> 1;
                    case Par(Azul _, _) -> 2;
                };
            }
        }
        """
        res_bad = analyze_source(incomplete_par)
        self.assertFalse(res_bad.success, msg="Falta Par(Vermelho, Azul)!")

    def test_04_guards_nao_garantem_exaustividade_e_enum_com_patterns(self):
        guarded_not_exhaustive = """
        class Demo {
            int testar(Object o) {
                return switch (o) {
                    case Object x when x != null -> 1;
                };
            }
        }
        """
        self.assertFalse(analyze_source(guarded_not_exhaustive).success)

        enum_exhaustive = """
        enum Dia { SEG, TER }
        class Demo {
            int num(Dia d) {
                return switch (d) {
                    case SEG -> 1;
                    case TER -> 2;
                };
            }
            int numComPattern(Dia d) {
                return switch (d) {
                    case SEG -> 1;
                    case Dia outro -> 2;
                };
            }
        }
        """
        self.assertTrue(analyze_source(enum_exhaustive).success)

    def test_05_switch_statement_tradicional_nao_exige_exaustividade_vs_enhanced(self):
        classic_stmt_ok = """
        enum Dia { SEG, TER }
        class Demo {
            void tradicional(Dia d) {
                switch (d) {
                    case SEG -> System.out.println("segunda");
                }
            }
        }
        """
        self.assertTrue(analyze_source(classic_stmt_ok).success)

        enhanced_stmt_missing = """
        class Demo {
            void enhanced(Object o) {
                switch (o) {
                    case String s -> System.out.println(s);
                }
            }
        }
        """
        self.assertFalse(analyze_source(enhanced_stmt_missing).success)

    def test_06_tipos_locais_records_e_atribuicao_subtipo_sealed(self):
        # Record local (JLS §14.3 / §16) com desconstrução e atribuição polimórfica de interface sealed
        source = """
        sealed interface Estado permits Ativo, Inativo {}
        record Ativo(int n) implements Estado {}
        record Inativo() implements Estado {}
        class Demo {
            int testar(int k) {
                record ParLocal(Estado e, int peso) {}
                Estado atual = new Ativo(k);
                Object caixa = new ParLocal(atual, 2);
                if (caixa instanceof ParLocal(Ativo(var n), var p)) {
                    return n * p;
                }
                return switch (atual) {
                    case Ativo(var n) -> n;
                    case Inativo() -> 0;
                };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors}")

        # Interface local não pode ser sealed segundo JLS §14.3
        local_sealed = """
        class Demo {
            int testar() {
                sealed interface Estado permits Ativo {}
                record Ativo(int n) implements Estado {}
                return 0;
            }
        }
        """
        self.assertFalse(analyze_source(local_sealed).success)


if __name__ == "__main__":
    unittest.main()
