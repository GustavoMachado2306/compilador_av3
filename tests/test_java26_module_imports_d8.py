import struct
import tempfile
import unittest
from pathlib import Path

from src.compiler.lexer import Lexer
from src.main import analyze_source
from src.compiler.parser import Parser
from src.compiler.semantic import SemanticAnalyzer
from src.compiler.symbol_table import SymbolTable
from src.compiler.ast_nodes import SingleTypeImport, TypeImportOnDemand, SingleModuleImport


def _build_synthetic_module_info(mod_name: str, exported_pkgs, transitive_reqs=()):
    """Constrói um arquivo module-info.class mínimo válido segundo JVMS §4.7.25 para testes."""
    cp = [None]

    def add_utf8(s: str) -> int:
        cp.append(("utf8", s))
        return len(cp) - 1

    def add_u2_ref(tag: int, utf8_idx: int) -> int:
        cp.append(("ref", tag, utf8_idx))
        return len(cp) - 1

    this_u = add_utf8("module-info")
    this_c = add_u2_ref(7, this_u)
    mod_attr_u = add_utf8("Module")
    mod_u = add_utf8(mod_name)
    mod_idx = add_u2_ref(19, mod_u)  # CONSTANT_Module

    req_entries = []
    for r in transitive_reqs:
        ru = add_utf8(r)
        r_idx = add_u2_ref(19, ru)
        req_entries.append((r_idx, 0x0020, 0))  # ACC_TRANSITIVE

    exp_entries = []
    for p in exported_pkgs:
        pu = add_utf8(p.replace(".", "/"))
        p_idx = add_u2_ref(20, pu)  # CONSTANT_Package
        exp_entries.append((p_idx, 0, []))

    mod_buf = bytearray()
    mod_buf.extend(struct.pack(">HHH", mod_idx, 0, 0))
    mod_buf.extend(struct.pack(">H", len(req_entries)))
    for r_idx, r_flags, r_ver in req_entries:
        mod_buf.extend(struct.pack(">HHH", r_idx, r_flags, r_ver))
    mod_buf.extend(struct.pack(">H", len(exp_entries)))
    for p_idx, e_flags, to_list in exp_entries:
        mod_buf.extend(struct.pack(">HHH", p_idx, e_flags, len(to_list)))
    mod_buf.extend(struct.pack(">HHH", 0, 0, 0))  # opens, uses, provides

    out = bytearray()
    out.extend(struct.pack(">IHH", 0xCAFEBABE, 0, 55))
    out.extend(struct.pack(">H", len(cp)))
    for item in cp[1:]:
        if item[0] == "utf8":
            b = item[1].encode("utf-8")
            out.extend(struct.pack(">BH", 1, len(b)))
            out.extend(b)
        else:
            out.extend(struct.pack(">BH", item[1], item[2]))
    out.extend(struct.pack(">HHHH", 0x8000, this_c, 0, 0))  # ACC_MODULE, this, super=0, ifaces=0
    out.extend(struct.pack(">HH", 0, 0))  # fields=0, methods=0
    out.extend(struct.pack(">HHI", 1, mod_attr_u, len(mod_buf)))
    out.extend(mod_buf)
    return bytes(out)


class TestJava26ModuleImportsD8(unittest.TestCase):
    """D8 — Reconhecimento semântico de import module, precedência e limites honestos em Java SE 26."""

    def test_01_import_module_java_base_resolve_tipos_e_aridade(self):
        ok_src = """
        import module java.base;
        class Demo {
            Instant t = Instant.now();
            BigDecimal valor = BigDecimal.ZERO;
            Path p = null;
            FileSystem fs = null;
            List<String> lista = new ArrayList<>();
            Map.Entry<String, Integer> par = null;
        }
        """
        res = analyze_source(ok_src)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors} | {res.syntactic_error}")
        self.assertEqual(res.unresolved_checks, [], msg=f"Não deve emitir unresolved para java.base: {res.unresolved_checks}")

        bad_arity = """
        import module java.base;
        class Demo {
            BigDecimal<String> errado;
        }
        """
        res_bad = analyze_source(bad_arity)
        self.assertFalse(res_bad.success)
        self.assertTrue(any("não é genérico" in e for e in res_bad.semantic_errors), msg=res_bad.semantic_errors)

    def test_02_precedencia_e_palavra_contextual_module(self):
        # Import explícito único prevalece sobre import module java.base (java.util.Date vs java.sql.Date)
        prec_src = """
        import module java.base;
        import java.sql.Date;
        class Demo {
            Date sqlDate = Date.valueOf("2026-01-01");
        }
        """
        res = analyze_source(prec_src)
        self.assertTrue(res.success, msg=f"Erros: {res.semantic_errors}")
        self.assertEqual(res.unresolved_checks, [])

        # Declaração local na unidade prevalece sobre módulo importado
        shadow_src = """
        import module java.base;
        class Path {}
        class Demo {
            Path p = new Path();
        }
        """
        res_shadow = analyze_source(shadow_src)
        self.assertTrue(res_shadow.success, msg=res_shadow.semantic_errors)

        # Pacote ou variável chamados 'module' preservados sem colisão com 'import module ...;'
        pkg_named_module = """
        import module.Foo;
        import module.*;
        class Demo {
            int module = 42;
            void f(int module) {}
        }
        """
        unit = Parser(Lexer(pkg_named_module).tokenize()).parse()
        self.assertIsInstance(unit.imports[0], SingleTypeImport)
        self.assertEqual(unit.imports[0].name, "module.Foo")
        self.assertIsInstance(unit.imports[1], TypeImportOnDemand)
        self.assertEqual(unit.imports[1].name, "module.*")

    def test_03_import_module_transitivo_sql_e_descritor_module_info_sintetico(self):
        sql_src = """
        import module java.sql;
        class Demo {
            Connection conn = null;
            Logger log = null;
        }
        """
        res_sql = analyze_source(sql_src)
        self.assertTrue(res_sql.success, msg=res_sql.semantic_errors)
        self.assertEqual(res_sql.unresolved_checks, [])

        # Descritor module-info.class real em diretório no classpath + classe no mesmo diretório
        with tempfile.TemporaryDirectory() as tmp:
            tpath = Path(tmp)
            mod_bytes = _build_synthetic_module_info("com.acme.mod", ["com.acme.api"])
            (tpath / "module-info.class").write_bytes(mod_bytes)

            src = """
            import module com.acme.mod;
            class Cliente {
                int x = 1;
            }
            """
            ast = Parser(Lexer(src).tokenize()).parse()
            analyzer = SemanticAnalyzer(SymbolTable(), classpath=[str(tpath)], include_stdlib=True)
            errs = analyzer.analyze(ast)
            self.assertEqual(errs, [])
            self.assertEqual(analyzer.unresolved_checks, [])

    def test_04_multi_unidade_modular_interna_e_fronteira_honesta_modulo_ausente(self):
        u_mod = Parser(Lexer("module app.core { exports app.core.api; }").tokenize()).parse()
        u_api = Parser(Lexer("package app.core.api; public class Servico { public int ping() { return 1; } }").tokenize()).parse()
        u_cli = Parser(Lexer("import module app.core; class Cliente { int ok(Servico s) { return s.ping(); } }").tokenize()).parse()

        analyzer = SemanticAnalyzer(SymbolTable(), include_stdlib=True)
        errs = analyzer.analyze_units([u_mod, u_api, u_cli])
        self.assertEqual(errs, [], msg=errs)
        self.assertEqual(analyzer.unresolved_checks, [])

        # Módulo externo ausente não é confundido com classe nem gera falso erro semântico
        res_unknown = analyze_source("import module externo.nao.mapeado; class Demo {}")
        self.assertTrue(res_unknown.success, msg=res_unknown.semantic_errors)
        self.assertTrue(
            any("Módulo 'externo.nao.mapeado'" in u for u in res_unknown.unresolved_checks),
            msg=res_unknown.unresolved_checks,
        )
        self.assertFalse(
            any("Classe ou interface importada" in u for u in res_unknown.unresolved_checks),
            msg=res_unknown.unresolved_checks,
        )

    def test_05_ambiguidade_module_imports_jls_7_5_5_e_resolucao(self):
        # 1. Ambiguidade java.base + java.desktop (List) em campo, parâmetro, retorno, herança e instanciação
        for src in (
            "import module java.base;\nimport module java.desktop;\nclass C { List xs; }",
            "import module java.base;\nimport module java.desktop;\nclass C { void f(List xs) {} }",
            "import module java.base;\nimport module java.desktop;\nclass C { List f() { return null; } }",
            "import module java.base;\nimport module java.desktop;\nabstract class C implements List {}",
            "import module java.base;\nimport module java.desktop;\nclass C { void f() { new List(); } }",
        ):
            res = analyze_source(src)
            self.assertFalse(res.success, msg=src)
            self.assertTrue(
                any("Referência ambígua ao tipo 'List'" in e and "JLS §7.5.5" in e for e in res.semantic_errors),
                msg=f"Esperada ambiguidade de List em: {res.semantic_errors}",
            )

        # 2. Único módulo exportando múltiplos pacotes com o mesmo tipo público (Element em java.desktop)
        res_el = analyze_source("import module java.desktop;\nclass C { Element el; }")
        self.assertFalse(res_el.success)
        self.assertTrue(
            any("Referência ambígua ao tipo 'Element'" in e for e in res_el.semantic_errors),
            msg=res_el.semantic_errors,
        )

        # 3. Ambiguidade entre import module e import pacote.*
        res_mix = analyze_source("import module java.base;\nimport java.sql.*;\nclass C { Date d; }")
        self.assertFalse(res_mix.success)
        self.assertTrue(
            any("Referência ambígua ao tipo 'Date'" in e for e in res_mix.semantic_errors),
            msg=res_mix.semantic_errors,
        )

        # 4. Resolução por import explícito, FQN, shadowing local e import redundante do mesmo módulo
        for ok_src in (
            "import module java.base;\nimport module java.desktop;\nimport java.util.List;\nclass C { List xs; }",
            "import module java.base;\nimport module java.desktop;\nclass C { java.util.List xs; java.awt.List awt; }",
            "import module java.base;\nimport module java.desktop;\nclass List {}\nclass C { List xs = new List(); }",
            "import module java.base;\nimport module java.base;\nclass C { List xs = null; }",
        ):
            res_ok = analyze_source(ok_src)
            self.assertTrue(res_ok.success, msg=f"{ok_src} -> {res_ok.semantic_errors}")

        # 5. Módulos sintéticos multi-unidade: módulo exportando dois pacotes com classe pública 'Element'
        u_mod = Parser(Lexer("module app.multi { exports p1; exports p2; }").tokenize()).parse()
        u_p1 = Parser(Lexer("package p1; public class Element { public int a() { return 1; } }").tokenize()).parse()
        u_p2 = Parser(Lexer("package p2; public class Element { public int b() { return 2; } }").tokenize()).parse()
        u_amb = Parser(
            Lexer("package cli; import module app.multi; class C extends Element { Element f; Element g(Element p) { return new Element(); } }").tokenize()
        ).parse()

        sa_amb = SemanticAnalyzer(SymbolTable(), include_stdlib=True)
        errs_amb = sa_amb.analyze_units([u_mod, u_p1, u_p2, u_amb])
        self.assertTrue(
            any("Referência ambígua ao tipo 'Element'" in e for e in errs_amb),
            msg=errs_amb,
        )

        u_resolved = Parser(
            Lexer("package cli; import module app.multi; import p1.Element; class C extends Element { Element f; Element g(Element p) { return new Element(); } }").tokenize()
        ).parse()
        sa_ok = SemanticAnalyzer(SymbolTable(), include_stdlib=True)
        errs_ok = sa_ok.analyze_units([u_mod, u_p1, u_p2, u_resolved])
        self.assertEqual(errs_ok, [], msg=errs_ok)


if __name__ == "__main__":
    unittest.main()
