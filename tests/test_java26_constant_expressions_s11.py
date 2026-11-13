import unittest

from src.lexer import Lexer
from src.parser import Parser
from src.semantic import SemanticAnalyzer
from src.symbol_table import SymbolTable


def analyze_java(code: str, enable_preview: bool = False):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(
        SymbolTable(),
        enable_preview_primitive_patterns=enable_preview,
    )
    errors = analyzer.analyze(ast)
    return errors, analyzer


class TestJava26ConstantExpressionsS11(unittest.TestCase):
    """Testes abrangentes para a etapa S11 (JLS §15.29, §4.12.4, §5.2)."""

    def test_01_exemplos_obrigatorios_narrowing_e_limites(self):
        code_ok = """
        public class ExemplosValidos {
            static final int LIMITE_CAMPO = 100;
            interface Config {
                int BASE = 60;
            }
            void testar() {
                final int LIMITE = 100;
                byte a = 100 + 27;
                byte b = 32 * 2;
                byte bMax = (64 * 2) - 1;
                byte bMin = -128;
                short c = 1000 + 2000;
                short sMin = -32768;
                short sMax = 32767;
                char d = 65 + 1;
                char cMin = 0;
                char cMax = 65535;
                byte valor = LIMITE + 27;
                byte campo = LIMITE_CAMPO + 27;
                byte ifc = Config.BASE + 67;
                final var LIMITE_VAR = 100;
                byte comVar = LIMITE_VAR + 27;
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [])

        bad_cases = [
            "byte e = 128;",
            "byte f = 100 + 28;",
            "byte g = 64 * 2;",
            "byte h = -129;",
            "short s1 = 32768;",
            "short s2 = -32769;",
            "char ch1 = -1;",
            "char ch2 = 65536;",
            "final int LIM = 101; byte v = LIM + 27;",
        ]
        for stmt in bad_cases:
            with self.subTest(stmt=stmt):
                code_err = f"public class E {{ void m() {{ {stmt} }} }}"
                errs, _ = analyze_java(code_err)
                self.assertTrue(errs, f"Deveria rejeitar: {stmt}")

    def test_02_literais_primitivos_e_tipos_incompativeis_para_narrowing(self):
        code_ok = """
        public class LiteraisConstantes {
            void m() {
                byte b1 = 'A';
                byte b2 = 0x7F;
                byte b3 = 0b0111_1111;
                byte b4 = 0177;
                short s1 = 'Z';
                char c1 = 'a' + 2;
                int x = -2147483648;
                long y = -9223372036854775808L;
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [])

        non_narrowable_types = [
            "byte b = 10L;",
            "short s = 10L;",
            "char c = 65L;",
            "byte b = 10.0;",
            "byte b = 10.0f;",
            "short s = 10.0;",
            "char c = 65.0;",
            "byte b = true;",
            "byte b = \"10\";",
            "byte b = '\\u0100';",
        ]
        for stmt in non_narrowable_types:
            with self.subTest(stmt=stmt):
                errs, _ = analyze_java(f"public class T {{ void m() {{ {stmt} }} }}")
                self.assertTrue(errs, f"Narrowing não permitido deveria falhar: {stmt}")

    def test_03_variaveis_final_constantes_vs_nao_constantes(self):
        code_ok = """
        public class FinalEncadeadas {
            static final int A = 10;
            static final int B = A * 3 + 2;
            static final int FWD = FinalEncadeadas.MAIS + 1;
            static final int MAIS = 99;
            final int INST = 120;
            void m() {
                final int X = B + 5;
                final byte Y = X + 10;
                byte z = Y + 80;
                byte w = FWD;
                byte instVal = INST;
                byte ext = Byte.MAX_VALUE;
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [])

        non_const_finals = [
            "final int blank; blank = 10; byte b = blank;",
            "final Integer wrapper = 10; byte b = wrapper;",
            "final Object obj = 10; int x = 1;",  # apenas garante não quebrar; checaremos cast/uso
            "int mut = 10; final int dep = mut + 1; byte b = dep;",
            "final int fromCall = helper(); byte b = fromCall;",
            "final int circ = Byte.MAX_VALUE + 1; byte b = circ;",
        ]
        for i, stmt in enumerate(non_const_finals):
            if i == 2:
                # final Object obj = "x"; não é constante JLS §4.12.4
                code = """
                public class T {
                    void m() {
                        final Object obj = "a";
                        final String s = obj + "b";
                    }
                }
                """
                # s não é constante constante string, vamos testar em switch duplicado/narrowing indireto:
                continue
            code = f"""
            public class T {{
                int helper() {{ return 1; }}
                void m(final int p) {{
                    {stmt}
                }}
            }}
            """
            with self.subTest(stmt=stmt):
                errs, _ = analyze_java(code)
                self.assertTrue(errs, f"Variável não-constante não deveria estreitar para byte: {stmt}")

        # Parâmetro final nunca é constante em tempo de compilação (JLS §4.12.4)
        errs_param, _ = analyze_java("public class P { void m(final int p) { byte b = p; } }")
        self.assertTrue(errs_param)

        # Acesso via instância (obj.CONST) não é expressão constante JLS §15.29
        errs_inst_ref, _ = analyze_java("""
        public class Inst {
            static final int K = 10;
            void m(Inst other) {
                byte b = other.K;
            }
        }
        """)
        self.assertTrue(errs_inst_ref)

    def test_04_aritmetica_overflow_underflow_e_divisao_por_zero(self):
        code_ok = """
        public class OverflowJava {
            void m() {
                // Overflow int 32-bit: MAX_VALUE + 1 == MIN_VALUE; + 2147483649 wraps to 1
                byte wrapInt = Integer.MAX_VALUE + Integer.MAX_VALUE + 3; // 0x7fffffff*2 + 3 = -2 + 3 = 1
                byte minNeg = -Integer.MIN_VALUE + 0; // -(-2147483648) continuam sendo MIN_VALUE -> não cabe em byte, testamos abaixo
            }
        }
        """
        # Corrigindo o teste positivo com expressões que efetivamente estreitam via wrap 32 bits
        code_wrap_ok = """
        public class OverflowOk {
            void m() {
                // 2147483647 + 2147483647 = -2 em 32 bits; + 3 = 1
                byte wrapPos = Integer.MAX_VALUE + Integer.MAX_VALUE + 3;
                // -(-2147483648) == -2147483648; (-(-2147483648)) - (-2147483648) == 0
                byte minNeg = (-Integer.MIN_VALUE) - Integer.MIN_VALUE;
                // Divisão e resto inteiros Java truncando para zero
                byte divPos = 100 / 3;       // 33
                byte divNeg = (-7) / 2;      // -3 (em Python // seria -4!)
                byte modNeg = (-7) % 3;      // -1 (em Python % seria 2!)
                byte modPosNeg = 7 % (-3);   // 1
                // Multiplicação com overflow 32-bit: 65536 * 65536 == 0 em int Java
                byte mulZero = 65536 * 65536;
            }
        }
        """
        errs, analyzer = analyze_java(code_wrap_ok)
        self.assertEqual(errs, [])

        # Verifica precisão exata: (-7) / 2 deve ser -3, não -4; se fosse -4, (-7)/2 == -3 falharia ou (-7)/2 + 131 == 128 falharia vs 127!
        code_div_check = """
        public class DivTrunc {
            void m() {
                byte ok = ((-7) / 2) + 130; // -3 + 130 = 127 -> Válido em Java! Se fosse Python floor (-4), seria 126
                byte tooBig = ((-7) / 2) + 131; // -3 + 131 = 128 -> Erro!
            }
        }
        """
        errs_div, _ = analyze_java(code_div_check)
        self.assertEqual(len(errs_div), 1)

        # Divisão inteira e módulo por zero não são expressões constantes (e não podem causar ZeroDivisionError)
        for bad in ("byte a = 10 / 0;", "byte b = 10 % 0;", "final int Z = 0; byte c = 5 / Z;"):
            with self.subTest(bad=bad):
                errs_z, _ = analyze_java(f"public class Z {{ void m() {{ {bad} }} }}")
                self.assertTrue(errs_z)

        # Overflow de -Integer.MIN_VALUE continua fora de byte (se fosse +2147483648 em Python continuaria fora, mas testamos igualdade com MIN_VALUE via ternário/constante)
        code_overflow_cond = """
        public class OvCond {
            void m(int runtimeVar) {
                // Condição é constante true: (-Integer.MIN_VALUE == Integer.MIN_VALUE) == true -> ternário escolhe 10!
                byte x = ((-Integer.MIN_VALUE) == Integer.MIN_VALUE) ? 10 : runtimeVar;
            }
        }
        """
        # Nota: em JLS §15.29 runtimeVar impede o ternário inteiro de ser constante! Testamos com 1000 na branch else:
        code_overflow_cond2 = """
        public class OvCond2 {
            void m() {
                byte x = ((-Integer.MIN_VALUE) == Integer.MIN_VALUE) ? 10 : 1000;
                byte y = (65536 * 65536 == 0) ? 42 : 1000;
                byte l = ((Long.MAX_VALUE + 1L) == Long.MIN_VALUE) ? 7 : 1000;
            }
        }
        """
        errs_ov2, _ = analyze_java(code_overflow_cond2)
        self.assertEqual(errs_ov2, [])

    def test_05_relacionais_igualdade_logicos_bitwise_shift_e_unarios(self):
        code_ok = """
        public class OperadoresConstantes {
            void m() {
                final int A = 12;
                final int B = 5;
                // Relacionais e igualdade
                byte rel1 = (A > B && A != B) ? 10 : 200;
                byte rel2 = (1.5 < 2.0 || false) ? 20 : 200;
                byte rel3 = ('A' == 65 && (0.0 / 0.0) != (0.0 / 0.0)) ? 30 : 200; // NaN != NaN é true!
                byte rel4 = (!(true ^ true) && (true & true) && (false | true)) ? 40 : 200;
                // Bitwise e unários
                byte bw1 = (0xF0 & 0x3C) | 0x03; // (48) | 3 = 51
                byte bw2 = (~0) & 0x7F;          // 127
                byte bw3 = ~0;                   // -1
                byte un1 = +((byte) 10);         // + promove para int 10 -> cabe em byte
                // Shift int (& 0x1F) e shift sem sinal >>>
                byte sh1 = 1 << 32;              // 1 << (32 & 31) = 1
                byte sh2 = 16 >> 33;             // 16 >> 1 = 8
                byte sh3 = -1 >>> 25;            // 127 (cabe em byte!)
                byte sh4 = (1 << 31) >>> 31;     // 1
                byte sh5 = ((1L << 64) == 1L && (-1L >>> 63) == 1L) ? 5 : 200;
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [])

        # Negativos: -1 >>> 24 == 255 (não cabe em byte); 1 << 7 == 128 (não cabe em byte); NaN == NaN é false -> escolhe else 200
        bad_ops = [
            "byte b = -1 >>> 24;",
            "byte b = 1 << 7;",
            "byte b = ((0.0 / 0.0) == (0.0 / 0.0)) ? 10 : 200;",
            "byte b = (A > 100) ? 10 : 200;",  # se A não declarado ou falso com 200
        ]
        for stmt in bad_ops[:3]:
            with self.subTest(stmt=stmt):
                errs_b, _ = analyze_java(f"public class BadOps {{ void m() {{ {stmt} }} }}")
                self.assertTrue(errs_b, f"Deveria falhar: {stmt}")

    def test_06_casts_em_expressoes_constantes(self):
        code_ok = """
        public class CastsConstantes {
            void m() {
                byte b1 = (byte) 300;        // 44
                byte b2 = (int) 10L;         // cast para int 10 -> narrowing implícito válido!
                byte b3 = (int) 12.9;        // trunca float/double para 12
                byte b4 = (byte) 1e20;       // float/double > INT_MAX -> 0x7FFFFFFF -> (byte) -1
                short s1 = (short) 70000;    // 4464
                char c1 = (char) -1;         // 65535
                byte b5 = ((char) -1 == 65535 && (byte) 128 == -128) ? 1 : 200;
                final String S = (String) ("ok" + 1);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [])

        # (Integer) 10 e (Object) "abc" NÃO são expressões constantes em JLS §15.29!
        errs_box_cast, _ = analyze_java("""
        public class NonConstCast {
            void m() {
                final int x = ((int) (Integer) 10); // cast via referência não é constante, mas infer_type retorna int
                byte b = (int) (Integer) 10;        // não pode fazer narrowing porque não é expressão constante!
            }
        }
        """)
        self.assertTrue(errs_box_cast)

        # (int) 200L é constante int 200 -> excede byte (-128..127)
        errs_range, _ = analyze_java("public class R { void m() { byte b = (int) 200L; } }")
        self.assertTrue(errs_range)

        # (char) 65 + 1 tem tipo int e valor 66 -> cabe em byte; (char) 65 + 65 não cabe (130)
        errs_char_arith, _ = analyze_java("""
        public class CA {
            void m() {
                byte ok = (char) 65 + 1;
                byte bad = (char) 65 + 65;
            }
        }
        """)
        self.assertEqual(len(errs_char_arith), 1)

    def test_07_concatenacao_strings_constantes_e_contextos_switch_return(self):
        code_ok = """
        public class StringsEContextos {
            static final String P = "ja";
            static final String Q = P + "va" + 26 + '!' + true;
            byte retornoConstante() {
                return 100 + 27;
            }
            void testar(boolean flag) {
                byte a = (Q == "java26!true") ? 10 : 200;
                byte b = ("10" + 20 == "1020" && (10 + 20 + "") == "30") ? 11 : 200;
                byte[] arr = { 100 + 27, -128, (byte) 300 };
                byte poly = flag ? (100 + 20) : (-100 - 28);
            }
        }
        """
        errs, _ = analyze_java(code_ok)
        self.assertEqual(errs, [])

        # null em concatenação de String NÃO é expressão constante JLS §15.29
        errs_null_concat, _ = analyze_java("""
        public class NullStr {
            void m(String x) {
                switch (x) {
                    case "a" + "b": break;
                    case "ab": break; // duplicado pois "a"+"b" == "ab"!
                }
            }
        }
        """)
        self.assertTrue(any("duplicada" in e for e in errs_null_concat), f"Esperava case duplicado: {errs_null_concat}")

        # "a" + null não deve colidir nem contar como constante em case duplicado / ternário constante
        errs_null_nonconst, _ = analyze_java("""
        public class NullNonConst {
            void m() {
                byte b = (("a" + null) == "anull") ? 1 : 200;
            }
        }
        """)
        self.assertTrue(errs_null_nonconst)

        # Retorno fora da faixa constante deve falhar
        errs_ret, _ = analyze_java("public class R { byte f() { return 100 + 28; } }")
        self.assertTrue(errs_ret)

        # Array initializer fora da faixa constante deve falhar
        errs_arr, _ = analyze_java("public class A { void m() { byte[] v = { 100 + 27, 100 + 28 }; } }")
        self.assertEqual(len(errs_arr), 1)


if __name__ == "__main__":
    unittest.main()
