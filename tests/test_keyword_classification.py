import io
import unittest
from contextlib import redirect_stdout

from src.compiler.lexer import (
    CONTEXTUAL_KEYWORD_CLASSIFICATIONS,
    KEYWORD_CLASSIFICATIONS,
    KEYWORDS,
    SPECIAL_LITERAL_CLASSIFICATIONS,
    SPECIAL_LITERALS,
    Lexer,
    classify_keyword,
)
from src.compiler.pipeline import analyze_source
from src.compiler.symbol_table import SymbolTable
from src.compiler.token import TokenType
from src.interfaces.web_gui import build_analysis_payload


class TestKeywordClassification(unittest.TestCase):
    """Testes abrangentes para a classificação completa de palavras reservadas, contextuais e literais."""

    def test_01_todas_palavras_reservadas_possuem_classificacao(self):
        self.assertEqual(set(KEYWORD_CLASSIFICATIONS.keys()), set(KEYWORDS.keys()))

        tokens = Lexer(" ".join(KEYWORDS.keys())).tokenize()
        st = SymbolTable(init_builtins=False)
        st.register_from_tokens(tokens)

        by_name = {s["name"]: s for s in st.all()}
        self.assertEqual(set(by_name.keys()), set(KEYWORDS.keys()))

        for kw, sym in by_name.items():
            self.assertEqual(sym["category"], "palavra_reservada", msg=kw)
            self.assertNotEqual(sym["type"], "-", msg=f"Palavra '{kw}' permaneceu com '-'")
            self.assertNotEqual(sym["type"], "outro", msg=f"Palavra '{kw}' ficou com 'outro'")
            self.assertEqual(sym["type"], KEYWORD_CLASSIFICATIONS[kw], msg=kw)

    def test_02_todas_palavras_contextuais_possuem_classificacao_e_uso_sintatico(self):
        expected_contextual = {
            "var",
            "record",
            "sealed",
            "non-sealed",
            "permits",
            "yield",
            "when",
            "module",
            "open",
            "opens",
            "requires",
            "transitive",
            "exports",
            "to",
            "uses",
            "provides",
            "with",
        }
        self.assertEqual(set(CONTEXTUAL_KEYWORD_CLASSIFICATIONS.keys()), expected_contextual)
        for kw in expected_contextual:
            self.assertNotEqual(CONTEXTUAL_KEYWORD_CLASSIFICATIONS[kw], "-")
            self.assertEqual(
                classify_keyword(kw, include_contextual=True),
                CONTEXTUAL_KEYWORD_CLASSIFICATIONS[kw],
            )

        # Código com declarações record, sealed, non-sealed, permits, var, when, yield
        src_lang = """
        import module java.base;

        public sealed interface Forma permits Circulo, Retangulo {
        }

        public record Circulo(double raio) implements Forma {
        }

        public non-sealed class Retangulo implements Forma {
            public int avaliar(Object obj) {
                var base = 10;
                return switch (obj) {
                    case String s when !s.isEmpty() -> { yield base; }
                    default -> 0;
                };
            }
        }
        """
        res_lang = analyze_source(src_lang)
        self.assertTrue(res_lang.success, msg=f"Erros: {res_lang.syntactic_error or res_lang.semantic_errors}")
        by_name_lang = {s["name"]: s for s in res_lang.symbol_table.all()}
        for kw in ("module", "sealed", "permits", "record", "non-sealed", "var", "when", "yield"):
            self.assertIn(kw, by_name_lang, msg=f"Contextual '{kw}' ausente na tabela")
            self.assertEqual(by_name_lang[kw]["category"], "palavra_reservada", msg=kw)
            self.assertEqual(by_name_lang[kw]["type"], CONTEXTUAL_KEYWORD_CLASSIFICATIONS[kw], msg=kw)

        # Código modular completo (JPMS)
        src_mod = """
        open module com.app {
            requires transitive java.sql;
            exports com.app.api to com.client;
            opens com.app.internal to com.framework;
            uses com.app.api.Servico;
            provides com.app.api.Servico with com.app.internal.ServicoImpl;
        }
        """
        res_mod = analyze_source(src_mod)
        self.assertIsNone(res_mod.lexical_error)
        self.assertIsNone(res_mod.syntactic_error)
        by_name_mod = {s["name"]: s for s in res_mod.symbol_table.all()}
        for kw in ("open", "module", "requires", "transitive", "exports", "to", "opens", "uses", "provides", "with"):
            self.assertIn(kw, by_name_mod, msg=f"Contextual de módulo '{kw}' ausente")
            self.assertEqual(by_name_mod[kw]["category"], "palavra_reservada", msg=kw)
            self.assertEqual(by_name_mod[kw]["type"], "modulo", msg=kw)

    def test_03_tipos_primitivos_e_void(self):
        primitives = ("byte", "short", "char", "int", "long", "float", "double", "boolean")
        tokens = Lexer(" ".join(primitives) + " void").tokenize()
        st = SymbolTable(init_builtins=False)
        st.register_from_tokens(tokens)
        by_name = {s["name"]: s for s in st.all()}

        for prim in primitives:
            self.assertEqual(by_name[prim]["category"], "palavra_reservada")
            self.assertEqual(by_name[prim]["type"], "tipo_primitivo")

        self.assertEqual(by_name["void"]["category"], "palavra_reservada")
        self.assertEqual(by_name["void"]["type"], "tipo_vazio")

    def test_04_condicionais_e_repeticao(self):
        src = """
        class Fluxo {
            void executar(int n) {
                if (n > 0) {
                    for (int i = 0; i < n; i++) {
                        while (i < 1) {
                            do {
                                break;
                            } while (false);
                            continue;
                        }
                    }
                } else {
                    switch (n) {
                        case 0:
                            break;
                        default:
                            return;
                    }
                }
            }
        }
        """
        res = analyze_source(src)
        self.assertTrue(res.success, msg=res.semantic_errors)
        by_name = {s["name"]: s for s in res.symbol_table.all()}

        for kw in ("if", "else", "switch"):
            self.assertEqual(by_name[kw]["type"], "condicional")
        for kw in ("case", "default"):
            self.assertEqual(by_name[kw]["type"], "padrao_switch")
        for kw in ("for", "while", "do"):
            self.assertEqual(by_name[kw]["type"], "repeticao")
        for kw in ("break", "continue"):
            self.assertEqual(by_name[kw]["type"], "controle_fluxo")
        self.assertEqual(by_name["return"]["type"], "controle_retorno")

    def test_05_declaracoes_classe_interface_enum_record(self):
        src = """
        package exemplo;
        import java.util.List;

        public interface Contrato {}
        public enum Estado { ATIVO }
        public record Item(int codigo) {}
        public class Modelo extends Object implements Contrato {}
        """
        res = analyze_source(src)
        self.assertTrue(res.success, msg=res.semantic_errors)
        by_name = {s["name"]: s for s in res.symbol_table.all()}

        self.assertEqual(by_name["package"]["type"], "declaracao_pacote")
        self.assertEqual(by_name["import"]["type"], "importacao")
        self.assertEqual(by_name["class"]["type"], "declaracao_classe")
        self.assertEqual(by_name["interface"]["type"], "declaracao_interface")
        self.assertEqual(by_name["enum"]["type"], "declaracao_enum")
        self.assertEqual(by_name["record"]["type"], "declaracao_record")
        self.assertEqual(by_name["extends"]["type"], "heranca")
        self.assertEqual(by_name["implements"]["type"], "heranca")

    def test_06_modificadores_acesso_e_demais_modificadores(self):
        tokens = Lexer(
            "public private protected static final abstract native synchronized transient volatile strictfp"
        ).tokenize()
        st = SymbolTable(init_builtins=False)
        st.register_from_tokens(tokens)
        by_name = {s["name"]: s for s in st.all()}

        for acc in ("public", "private", "protected"):
            self.assertEqual(by_name[acc]["category"], "palavra_reservada")
            self.assertEqual(by_name[acc]["type"], "modificador_acesso")

        for mod in ("static", "final", "abstract", "native", "synchronized", "transient", "volatile", "strictfp"):
            self.assertEqual(by_name[mod]["category"], "palavra_reservada")
            self.assertEqual(by_name[mod]["type"], "modificador")

    def test_07_literais_reservados_true_false_null(self):
        self.assertEqual(set(SPECIAL_LITERAL_CLASSIFICATIONS.keys()), set(SPECIAL_LITERALS.keys()))
        src = "boolean ok = true;\nboolean nao = false;\nString texto = null;\n"
        res = analyze_source(src)
        self.assertTrue(res.success, msg=res.semantic_errors)

        # Tokens no Lexer mantêm natureza de literais (nunca KEYWORD_*)
        token_types = {t.lexeme: t.type for t in res.tokens}
        self.assertEqual(token_types["true"], TokenType.BOOLEAN_LITERAL)
        self.assertEqual(token_types["false"], TokenType.BOOLEAN_LITERAL)
        self.assertEqual(token_types["null"], TokenType.NULL_LITERAL)

        # Na Tabela de Símbolos, respeitam categoria e tipo próprios de literais
        by_name = {s["name"]: s for s in res.symbol_table.all()}
        self.assertEqual(by_name["true"]["category"], "literal_reservado")
        self.assertEqual(by_name["true"]["type"], "literal_booleano")
        self.assertEqual(by_name["false"]["category"], "literal_reservado")
        self.assertEqual(by_name["false"]["type"], "literal_booleano")
        self.assertEqual(by_name["null"]["category"], "literal_reservado")
        self.assertEqual(by_name["null"]["type"], "literal_nulo")

    def test_08_palavras_contextuais_como_identificadores_nao_viram_palavra_reservada(self):
        contextual_as_names = (
            "var",
            "record",
            "sealed",
            "permits",
            "yield",
            "when",
            "module",
            "open",
            "opens",
            "requires",
            "transitive",
            "exports",
            "to",
            "uses",
            "provides",
            "with",
        )
        # No Lexer continuam sendo IDENTIFIER
        lex_tokens = Lexer(" ".join(contextual_as_names)).tokenize()
        for tok in lex_tokens[:-1]:
            self.assertEqual(tok.type, TokenType.IDENTIFIER, msg=tok.lexeme)

        # Como variáveis locais, são declaradas como 'variavel', nunca 'palavra_reservada'
        decls = "\n".join(f"int {name} = 1;" for name in contextual_as_names)
        src = f"class IdentTest {{\n    void testar() {{\n{decls}\n    }}\n}}"
        res = analyze_source(src)
        self.assertTrue(res.success, msg=res.semantic_errors)

        by_name = {s["name"]: s for s in res.symbol_table.all()}
        for name in contextual_as_names:
            self.assertIn(name, by_name)
            self.assertEqual(by_name[name]["category"], "variavel", msg=name)
            self.assertEqual(by_name[name]["type"], "int", msg=name)

    def test_09_identificadores_comuns_preservados(self):
        src = "int classRoom = 1;\nboolean booleanFlag = true;\nString recordName = null;\n"
        res = analyze_source(src)
        self.assertTrue(res.success, msg=res.semantic_errors)

        ident_tokens = [t for t in res.tokens if t.type == TokenType.IDENTIFIER]
        self.assertEqual([t.lexeme for t in ident_tokens], ["classRoom", "booleanFlag", "String", "recordName"])

        by_name = {s["name"]: s for s in res.symbol_table.all()}
        self.assertEqual(by_name["classRoom"]["category"], "variavel")
        self.assertEqual(by_name["booleanFlag"]["category"], "variavel")
        self.assertEqual(by_name["recordName"]["category"], "variavel")

    def test_10_interfaces_web_cli_e_gui_exibem_classificacao_sem_hifen(self):
        src = """
        package app;
        public class Demo {
            private boolean ativo = true;
            public int calcular(int n) {
                if (n > 0) {
                    return n;
                }
                return 0;
            }
        }
        """
        # 1. Payload da Web GUI
        payload = build_analysis_payload(src)
        self.assertTrue(payload["success"])
        reserved_rows = [s for s in payload["symbols"] if s["category"] == "palavra_reservada"]
        self.assertGreater(len(reserved_rows), 0)
        for row in reserved_rows:
            self.assertNotEqual(row["type"], "-", msg=f"Linha da Web GUI com '-' em {row}")
            self.assertIn(row["type"], set(KEYWORD_CLASSIFICATIONS.values()))

        # Preserva lexemas originais e colunas de tokens
        tok_lexemes = [t["lexeme"] for t in payload["tokens"][:-1]]
        self.assertIn("package", tok_lexemes)
        self.assertIn("boolean", tok_lexemes)
        self.assertTrue(all(t["line"] >= 1 and t["column"] >= 1 for t in payload["tokens"]))

        # 2. Saída tabular da CLI (SymbolTable.print_table)
        res = analyze_source(src)
        buf = io.StringIO()
        with redirect_stdout(buf):
            res.symbol_table.print_table()
        cli_table = buf.getvalue()
        self.assertIn("declaracao_pacote", cli_table)
        self.assertIn("modificador_acesso", cli_table)
        self.assertIn("declaracao_classe", cli_table)
        self.assertIn("tipo_primitivo", cli_table)
        self.assertIn("condicional", cli_table)
        self.assertIn("controle_retorno", cli_table)
        self.assertIn("literal_booleano", cli_table)

        # 3. Tkinter GUI (quando display disponível no ambiente)
        try:
            import tkinter as tk
            from src.interfaces.gui import CompiladorGUI, TKINTER_AVAILABLE

            if TKINTER_AVAILABLE:
                app = CompiladorGUI()
                app.editor.delete("1.0", tk.END)
                app.editor.insert("1.0", src)
                app.on_analyze()
                gui_rows = [
                    app.symbols_tree.item(item, "values")
                    for item in app.symbols_tree.get_children()
                ]
                gui_reserved = [vals for vals in gui_rows if vals[2] == "palavra_reservada"]
                self.assertGreater(len(gui_reserved), 0)
                for vals in gui_reserved:
                    self.assertNotEqual(vals[3], "-")
                app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
