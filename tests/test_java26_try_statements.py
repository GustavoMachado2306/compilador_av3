"""
Suíte de Testes Automatizados para Etapa S6 — Try, Catch, Multicatch, Finally e Try-with-Resources (JLS §14.20).
Cobre: try/catch, múltiplos catch, multicatch (CatchType), try/finally, try/catch/finally,
try-with-resources (declaração, múltiplos recursos, var, resource reference Java 9+, ';' final opcional),
além de erros sintáticos e validações semânticas (multicatch incompatível, catch inalcançável, escopo de recurso).
"""

import unittest
from src.main import analyze_source
from src.ast_nodes import (
    TryStatement, CatchClause, CatchType, ResourceSpecification,
    Resource, LocalVariableDeclaration, Identifier
)


class TestJava26TryStatementsS6(unittest.TestCase):
    """Testes sintáticos e semânticos para TryStatement e TryWithResourcesStatement (JLS §14.20)."""

    def test_01_try_catch_e_multiplos_catch_e_finally(self):
        source = """
        class IOException extends Exception {}
        class SQLException extends Exception {}
        class Demo {
            void executar() throws IOException, SQLException {}
            void tratar(Object e) {}
            void tratarBanco(Object e) {}
            void liberar() {}
            void run() throws IOException, SQLException {
                try {
                    executar();
                } catch (IOException e) {
                    tratar(e);
                } catch (SQLException e) {
                    tratarBanco(e);
                } finally {
                    liberar();
                }
                try {
                    executar();
                } finally {
                    liberar();
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[2].members[4].body.statements
        t1, t2 = stmts[0], stmts[1]
        self.assertIsInstance(t1, TryStatement)
        self.assertEqual(len(t1.catches), 2)
        self.assertIsNotNone(t1.finally_block)
        self.assertIsInstance(t2, TryStatement)
        self.assertEqual(len(t2.catches), 0)
        self.assertIsNotNone(t2.finally_block)

    def test_02_multicatch_preserva_tipos_alternativos_na_ast(self):
        source = """
        class IOException extends Exception {}
        class SQLException extends Exception {}
        class Demo {
            void executar() throws IOException, SQLException {}
            void tratar(Object e) {}
            void run() {
                try {
                    executar();
                } catch (IOException | SQLException e) {
                    tratar(e);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        try_stmt = res.ast.type_declarations[2].members[2].body.statements[0]
        catch_clause = try_stmt.catches[0]
        self.assertIsInstance(catch_clause, CatchClause)
        self.assertIsInstance(catch_clause.catch_type, CatchType)
        self.assertEqual([t.full_name for t in catch_clause.catch_types], ["IOException", "SQLException"])
        self.assertEqual(catch_clause.parameter.name, "e")

    def test_03_try_with_resources_var_multiplos_e_ponto_virgula_opcional(self):
        source = """
        class InputStream implements AutoCloseable { public void close() {} }
        class OutputStream implements AutoCloseable { public void close() {} }
        class Demo {
            InputStream abrirEntrada() { return null; }
            OutputStream abrirSaida() { return null; }
            void copiar(InputStream a, OutputStream b) {}
            void processar(InputStream r) {}
            void run() {
                try (var recurso = abrirEntrada()) {
                    processar(recurso);
                }
                try (
                    InputStream entrada = abrirEntrada();
                    OutputStream saida = abrirSaida();
                ) {
                    copiar(entrada, saida);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        stmts = res.ast.type_declarations[2].members[4].body.statements
        t1, t2 = stmts[0], stmts[1]
        self.assertIsInstance(t1.resource_specification, ResourceSpecification)
        self.assertFalse(t1.resource_specification.has_trailing_semicolon)
        self.assertEqual(len(t1.resource_specification.resources), 1)
        self.assertIsInstance(t1.resource_specification.resources[0], Resource)
        self.assertFalse(t1.resource_specification.resources[0].is_reference)
        self.assertTrue(t1.resource_specification.resources[0].declaration.is_var)

        self.assertTrue(t2.resource_specification.has_trailing_semicolon)
        self.assertEqual(len(t2.resource_specification.resources), 2)
        self.assertTrue(isinstance(t2.resources[0], LocalVariableDeclaration))

    def test_04_try_with_resources_java9_variable_reference(self):
        source = """
        class InputStream implements AutoCloseable { public void close() {} }
        class Demo {
            InputStream abrir() { return null; }
            void processar(InputStream e) {}
            void run() {
                final InputStream entrada = abrir();
                InputStream efetivamenteFinal = abrir();
                try (entrada; efetivamenteFinal;) {
                    processar(entrada);
                    processar(efetivamenteFinal);
                }
            }
        }
        """
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        try_stmt = res.ast.type_declarations[1].members[2].body.statements[2]
        spec = try_stmt.resource_specification
        self.assertTrue(spec.has_trailing_semicolon)
        self.assertEqual(len(spec.resources), 2)
        self.assertTrue(all(r.is_reference for r in spec.resources))
        self.assertIsInstance(spec.resources[0].variable_access, Identifier)
        self.assertEqual(spec.resources[0].variable_access.name, "entrada")

    def test_05_erros_sintaticos_try_catch_e_resource(self):
        bad_cases = [
            "try { executar(); }",
            "try { executar(); } catch () {}",
            "try { executar(); } catch (IOException | e) {}",
            "try { executar(); } catch (| IOException e) {}",
            "try () { executar(); }",
            "try (var x) { executar(); }",
            "try (a + b) { executar(); }",
        ]
        for code in bad_cases:
            with self.subTest(code=code):
                source = f"""
                class Demo {{
                    void executar() {{}}
                    void m(int a, int b) {{
                        {code}
                    }}
                }}
                """
                res = analyze_source(source)
                self.assertFalse(res.success, msg=f"Esperava erro para: {code}")
                self.assertIsNotNone(res.syntactic_error)

    def test_06_multicatch_incompativel_e_catch_inalcancavel(self):
        incompat_src = """
        class Demo {
            void executar() {}
            void m() {
                try {
                    executar();
                } catch (IOException | Exception e) {
                }
            }
        }
        """
        res1 = analyze_source(incompat_src)
        self.assertFalse(res1.success)
        self.assertTrue(any("multicatch" in e for e in res1.semantic_errors), msg=res1.semantic_errors)

        unreach_src = """
        class Demo {
            void executar() {}
            void m() {
                try {
                    executar();
                } catch (Exception e) {
                } catch (IOException e) {
                }
            }
        }
        """
        res2 = analyze_source(unreach_src)
        self.assertFalse(res2.success)
        self.assertTrue(any("inalcançável" in e for e in res2.semantic_errors), msg=res2.semantic_errors)

    def test_07_recurso_nao_efetivamente_final_e_escopo_do_recurso(self):
        non_eff_final = """
        class InputStream {}
        class Demo {
            InputStream abrir() { return null; }
            void m() {
                InputStream r = abrir();
                r = abrir();
                try (r) {
                }
            }
        }
        """
        res1 = analyze_source(non_eff_final)
        self.assertFalse(res1.success)
        self.assertTrue(any("efetivamente final" in e and e.line == 8 for e in res1.semantic_errors), msg=res1.semantic_errors)

        out_of_scope = """
        class InputStream {}
        class Demo {
            InputStream abrir() { return null; }
            void usar(InputStream x) {}
            void m() {
                try (var res = abrir()) {
                    usar(res);
                } finally {
                    usar(res);
                }
            }
        }
        """
        res2 = analyze_source(out_of_scope)
        self.assertFalse(res2.success)
        self.assertTrue(any("res" in e and "não foi declarada" in e and e.line == 10 for e in res2.semantic_errors), msg=res2.semantic_errors)


if __name__ == "__main__":
    unittest.main()

