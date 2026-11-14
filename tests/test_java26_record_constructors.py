"""
Suíte de Testes Automatizados para a Etapa S4 da Gramática Java SE 26:
Construtores de Records: Implícito, Canônico Normal, Compacto e Não Canônico.
Referência Normativa: JLS Java SE 26, Capítulos 8 (§8.10.4, §8.10.4.1, §8.10.4.2), §8.8.7 (JEP 513) e 19.
"""

import unittest
from src.compiler.lexer import Lexer
from src.compiler.parser import Parser, SyntacticError
from src.main import analyze_source
from src.compiler.ast_nodes import (
    CompilationUnit, RecordDeclaration, RecordBody,
    NormalCanonicalConstructor, CompactConstructorDeclaration, NonCanonicalRecordConstructor,
    ConstructorBody, AlternateConstructorInvocation
)


def parse_code(source: str, mode: str = None) -> CompilationUnit:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse(mode=mode)


class TestJava26RecordConstructorsS4(unittest.TestCase):
    """Testes formais da Etapa S4 para Construtores de Records (JLS §8.10.4)."""

    def test_01_construtor_canonico_implicito(self):
        source = "public record Ponto(int x, int y) {}"
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertIsInstance(rec, RecordDeclaration)
        self.assertTrue(rec.has_implicit_canonical_constructor)
        self.assertFalse(rec.has_explicit_canonical_constructor)
        self.assertIsNone(rec.canonical_constructor)
        self.assertEqual(rec.constructors, [])

    def test_02_construtor_canonico_normal_valido(self):
        source = """
        public record Ponto(int x, int y) {
            public Ponto(int x, int y) {
                this.x = x;
                this.y = y;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertFalse(rec.has_implicit_canonical_constructor)
        self.assertTrue(rec.has_explicit_canonical_constructor)
        ctor = rec.canonical_constructor
        self.assertIsInstance(ctor, NormalCanonicalConstructor)
        self.assertEqual([p.name for p in ctor.parameters], ["x", "y"])

    def test_03_construtor_compacto_valido_com_reatribuicao_parametro(self):
        source = """
        public record Pessoa(String nome, int idade) {
            public Pessoa {
                if (idade < 0) {
                    throw new IllegalArgumentException("Idade negativa");
                }
                nome = nome.trim();
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertFalse(rec.has_implicit_canonical_constructor)
        self.assertTrue(rec.has_explicit_canonical_constructor)
        ctor = rec.canonical_constructor
        self.assertIsInstance(ctor, CompactConstructorDeclaration)
        self.assertFalse(ctor.has_formal_parameter_list)
        self.assertEqual([c.name for c in ctor.derived_parameters], ["nome", "idade"])

    def test_04_construtor_compacto_com_lambda_contendo_return_valido(self):
        # Usa interface funcional como tipo alvo em vez de 'var', pois JLS §14.4.1 proíbe 'var' com lambda sem target type (S6).
        source = """
        import java.util.function.IntUnaryOperator;
        record Filtro(int limite) {
            Filtro {
                IntUnaryOperator fn = (x) -> { return x + limite; };
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_05_construtor_compacto_com_anotacoes_e_modificador(self):
        source = """
        public record Id(int valor) {
            @Deprecated
            public Id {
                if (valor <= 0) valor = 1;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        ctor = res.ast.type_declarations[0].canonical_constructor
        self.assertIsInstance(ctor, CompactConstructorDeclaration)
        self.assertEqual(ctor.annotations[0].name, "Deprecated")
        self.assertIn("public", ctor.modifiers)

    def test_06_construtor_canonico_e_compacto_com_componente_varargs(self):
        src_norm = """
        record Tags(String... items) {
            Tags(String... items) {
                this.items = items;
            }
        }
        """
        res1 = analyze_source(src_norm)
        self.assertTrue(res1.success, msg=res1.semantic_errors)
        self.assertIsInstance(res1.ast.type_declarations[0].canonical_constructor, NormalCanonicalConstructor)

        src_comp = """
        record Tags(String... items) {
            Tags {
                int qtd = items.length;
            }
        }
        """
        res2 = analyze_source(src_comp)
        self.assertTrue(res2.success, msg=res2.semantic_errors)
        self.assertIsInstance(res2.ast.type_declarations[0].canonical_constructor, CompactConstructorDeclaration)

    def test_07_construtor_nao_canonico_delegando_com_this(self):
        source = """
        public record Ponto(int x, int y) {
            public Ponto {
                if (x < 0) x = 0;
            }
            public Ponto(int unico) {
                this(unico, unico);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertIsInstance(rec.members[0], CompactConstructorDeclaration)
        non_can = rec.members[1]
        self.assertIsInstance(non_can, NonCanonicalRecordConstructor)
        self.assertIsInstance(non_can.body, ConstructorBody)
        self.assertIsInstance(non_can.body.constructor_invocation, AlternateConstructorInvocation)

    def test_08_cadeia_construtores_nao_canonicos(self):
        source = """
        public record Retangulo(int x, int y) {
            public Retangulo() {
                this(1);
            }
            private Retangulo(int lado) {
                this(lado, lado);
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        rec = res.ast.type_declarations[0]
        self.assertTrue(rec.has_implicit_canonical_constructor)
        self.assertEqual(len(rec.constructors), 2)
        self.assertTrue(all(isinstance(c, NonCanonicalRecordConstructor) for c in rec.constructors))

    def test_09_construtor_nao_canonico_com_flexible_prologue(self):
        source = """
        public record Intervalo(int inicio, int fim) {
            public Intervalo(int tamanho) {
                int inicioCalc = 0;
                int fimCalc = tamanho > 0 ? tamanho : 1;
                this(inicioCalc, fimCalc);
                int ok = fimCalc;
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        ctor = res.ast.type_declarations[0].constructors[0]
        self.assertIsInstance(ctor, NonCanonicalRecordConstructor)
        self.assertEqual(len(ctor.body.prologue), 2)
        self.assertEqual(len(ctor.body.epilogue), 1)

    def test_10_erro_semantico_early_context_em_nao_canonico(self):
        source = """
        record Ponto(int x, int y) {
            Ponto(int v) {
                int ilegal = this.x;
                this(v, v);
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("early construction" in str(e).lower() and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_11_serializacao_to_dict_e_pretty_construtores_record(self):
        source = """
        record Par(int a, int b) {
            Par { a = a + 1; }
            Par() { this(0, 0); }
        }
        """
        rec = parse_code(source).type_declarations[0]
        d = rec.to_dict()
        self.assertFalse(d["has_implicit_canonical_constructor"])
        self.assertEqual(d["body"]["declarations"][0]["node"], "CompactConstructorDeclaration")
        self.assertFalse(d["body"]["declarations"][0]["has_formal_parameter_list"])
        self.assertEqual(d["body"]["declarations"][1]["node"], "NonCanonicalRecordConstructor")
        pretty = rec.pretty()
        self.assertIn("CompactConstructorDeclaration", pretty)
        self.assertIn("NonCanonicalRecordConstructor", pretty)

    def test_12_erro_semantico_return_em_construtor_compacto(self):
        source = """
        record Pessoa(String nome) {
            Pessoa {
                if (nome == null) {
                    return;
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("return" in str(e).lower() and e.line == 5 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_13_erro_semantico_atribuicao_this_em_construtor_compacto(self):
        source = """
        record Pessoa(String nome) {
            Pessoa {
                this.nome = nome;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("this." in str(e).lower() and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_14_erro_semantico_this_ou_super_explicito_em_construtor_compacto(self):
        for inv in ("this(1);", "super();"):
            source = f"""
            record Num(int v) {{
                Num {{
                    {inv}
                }}
            }}
            """
            res = analyze_source(source)
            self.assertFalse(res.success, msg=f"Deveria falhar {inv}")
            self.assertTrue(any("compacto" in str(e).lower() and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_15_erro_sintatico_construtor_compacto_com_throws_ou_type_params(self):
        for bad in (
            "record R(int x) { R throws Exception {} }",
            "record R(int x) { <T> R {} }",
        ):
            with self.assertRaises(SyntacticError):
                parse_code(bad)

    def test_16_erro_semantico_multiplos_construtores_canonicos(self):
        source = """
        record R(int x) {
            R { x = x + 1; }
            R(int x) { this.x = x; }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("múltiplos construtores canônicos" in str(e).lower() and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_17_erro_semantico_visibilidade_mais_restrita_que_record(self):
        for ctor_vis in ("private", "protected", ""):
            source = f"""
            public record Publico(int x) {{
                {ctor_vis} Publico {{}}
            }}
            """
            res = analyze_source(source)
            self.assertFalse(res.success, msg=f"Visibilidade '{ctor_vis}' deveria falhar em public record")
            self.assertTrue(any("visibilidade" in str(e).lower() for e in res.semantic_errors), msg=res.semantic_errors)

    def test_18_erro_semantico_nomes_parametros_diferentes_no_canonico_normal(self):
        source = """
        record Ponto(int x, int y) {
            Ponto(int a, int y) {
                this.x = a;
                this.y = y;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("'a'" in str(e) and "'x'" in str(e) and e.line == 3 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_19_erro_semantico_canonico_normal_com_throws_type_params_receiver_ou_this(self):
        casos = [
            "record R(int x) { <T> R(int x) { this.x = x; } }",
            "record R(int x) { R(int x) throws Exception { this.x = x; } }",
            "record R(int x) { R(R this, int x) { this.x = x; } }",
            "record R(int x) { R(int x) { this(); this.x = x; } }",
            "record R(int x) { R(int x) { super(); this.x = x; } }",
        ]
        for src in casos:
            res = analyze_source(src)
            self.assertFalse(res.success, msg=f"Deveria falhar: {src}")

    def test_20_erro_semantico_nao_canonico_sem_invocacao_this(self):
        casos = [
            "record Ponto(int x, int y) { Ponto() {} }",
            "record Ponto(int x, int y) { Ponto(int x) {} }",
            "record Par(String a, int b) { Par(int b, String a) {} }",
        ]
        for src in casos:
            res = analyze_source(src)
            self.assertFalse(res.success, msg=f"Deveria exigir this(...): {src}")
            self.assertTrue(any("this(...)" in str(e) for e in res.semantic_errors), msg=res.semantic_errors)

    def test_21_erro_semantico_nao_canonico_invocando_super(self):
        source = """
        record Ponto(int x, int y) {
            Ponto(int v) {
                super();
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("super(...)" in str(e) and e.line == 4 for e in res.semantic_errors), msg=res.semantic_errors)

    def test_22_erro_semantico_varargs_incompativel_com_array_no_canonico(self):
        source = """
        record Tags(String... items) {
            Tags(String[] items) {
                this.items = items;
            }
        }
        """
        res = analyze_source(source)
        self.assertFalse(res.success)
        self.assertTrue(any("this(...)" in str(e) or "varargs" in str(e).lower() for e in res.semantic_errors), msg=res.semantic_errors)


if __name__ == "__main__":
    unittest.main()

