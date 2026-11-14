import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.main import analyze_source


class TestSemanticCore(unittest.TestCase):
    """Grupo B: Suíte de validação do analisador semântico simplificado e tabela de símbolos."""

    def test_01_variavel_declarada(self):
        source = "int x = 10;\nint y = x + 5;\nString msg = \"ok\";\n"
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        self.assertEqual(len(res.semantic_errors), 0)
        self.assertTrue(res.symbol_table.exists("x"))
        self.assertTrue(res.symbol_table.exists("y"))
        self.assertTrue(res.symbol_table.exists("msg"))

    def test_02_variavel_nao_declarada_nao_entra_na_tabela(self):
        source = "int x = 10;\ny = x + 1;\nint z = w;\n"
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = "\n".join(str(e) for e in res.semantic_errors)
        self.assertIn("Variável 'y' não foi declarada", msgs)
        self.assertIn("Variável 'w' não foi declarada", msgs)
        self.assertIsNone(res.symbol_table.get_symbol("y"))
        self.assertIsNone(res.symbol_table.get_symbol("w"))

    def test_03_declaracao_duplicada_no_mesmo_escopo(self):
        source = (
            "class A {\n"
            "    void f(int p) {\n"
            "        int x = 1;\n"
            "        int x = 2;\n"
            "        int p = 3;\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertFalse(res.success)
        msgs = "\n".join(str(e) for e in res.semantic_errors)
        self.assertIn("Variável 'x' declarada novamente", msgs)
        self.assertIn("Variável 'p' declarada novamente", msgs)

    def test_04_escopo_de_blocos_e_lacos(self):
        valid = (
            "class Escopo {\n"
            "    void testar() {\n"
            "        int externa = 10;\n"
            "        if (externa > 0) {\n"
            "            int interna = externa + 5;\n"
            "            externa = interna;\n"
            "        }\n"
            "        for (int i = 0; i < 3; i++) {\n"
            "            int aux = i * 2;\n"
            "        }\n"
            "        {\n"
            "            int bloco = 1;\n"
            "        }\n"
            "        {\n"
            "            int bloco = 2;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        res_ok = analyze_source(valid)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        invalid = (
            "class EscopoErro {\n"
            "    void testar() {\n"
            "        if (true) {\n"
            "            int segredo = 7;\n"
            "        }\n"
            "        int fora = segredo;\n"
            "        for (int k = 0; k < 2; k++) {}\n"
            "        k = 10;\n"
            "    }\n"
            "}\n"
        )
        res_err = analyze_source(invalid)
        self.assertFalse(res_err.success)
        msgs = "\n".join(str(e) for e in res_err.semantic_errors)
        self.assertIn("Variável 'segredo' não foi declarada", msgs)
        self.assertIn("Variável 'k' não foi declarada", msgs)

    def test_05_atribuicao_compativel(self):
        source = (
            "int a = 1;\n"
            "a += 5;\n"
            "double d = a;\n"
            "String s = null;\n"
            "s = \"abc\";\n"
            "boolean flag = false;\n"
            "flag = (a == 6);\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_06_atribuicao_incompativel(self):
        casos = [
            'int x = "texto";',
            "int x = true;",
            "double d = 3.5;\nint i = d;",
            "int p = null;",
            "String s = 42;",
        ]
        for code in casos:
            with self.subTest(code=code):
                res = analyze_source(code)
                self.assertFalse(res.success, msg=f"Deveria rejeitar: {code}")
                self.assertTrue(
                    any("Incompatibilidade de tipos" in str(e) for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_07_widening_numerico(self):
        source = (
            "byte b = 10;\n"
            "short s = b;\n"
            "int i = s;\n"
            "long l = i;\n"
            "float f = l;\n"
            "double d = f;\n"
            "double soma = i + l + 2.5;\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_08_concatenacao_e_aritmetica_string(self):
        ok = (
            'String a = "Java ";\n'
            'String b = a + 26 + " " + true;\n'
            "b += 3.14;\n"
        )
        res_ok = analyze_source(ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        err = 'String s = "abc";\nint x = s - 1;\ns *= 2;\n'
        res_err = analyze_source(err)
        self.assertFalse(res_err.success)
        msgs = "\n".join(str(e) for e in res_err.semantic_errors)
        self.assertIn("não é suportado em operações aritméticas", msgs)

    def test_09_condicao_booleana(self):
        ok = (
            "class Cond {\n"
            "    void testar() {\n"
            "        boolean ativo = true;\n"
            "        int n = 3;\n"
            "        if (ativo && n > 0) {\n"
            "            while (n > 0) { n = n - 1; }\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        res_ok = analyze_source(ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        err = (
            "class CondErro {\n"
            "    void testar() {\n"
            "        int n = 1;\n"
            "        if (n) { n = 2; }\n"
            '        while ("sim") { break; }\n'
            "    }\n"
            "}\n"
        )
        res_err = analyze_source(err)
        self.assertFalse(res_err.success)
        self.assertGreaterEqual(len(res_err.semantic_errors), 2)

    def test_10_retorno_basico(self):
        ok = (
            "class Calculadora {\n"
            "    int dobro(int v) { return v * 2; }\n"
            "    double metade(int v) { return v / 2.0; }\n"
            "    void avisar() { return; }\n"
            "}\n"
        )
        res_ok = analyze_source(ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        err = (
            "class RetornoErrado {\n"
            "    int f() { return \"errado\"; }\n"
            "    int g() { return; }\n"
            "    void h() { return 10; }\n"
            "}\n"
        )
        res_err = analyze_source(err)
        self.assertFalse(res_err.success)
        self.assertGreaterEqual(len(res_err.semantic_errors), 3)

    def test_11_chamada_simples_de_metodo_e_construtor(self):
        ok = (
            "class Servico {\n"
            "    int somar(int a, int b) { return a + b; }\n"
            "    void usar() {\n"
            "        int r = somar(2, 3);\n"
            "        Servico s = new Servico();\n"
            "        int r2 = s.somar(r, 1);\n"
            "    }\n"
            "}\n"
        )
        res_ok = analyze_source(ok)
        self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

        err = (
            "class ServicoErro {\n"
            "    int somar(int a, int b) { return a + b; }\n"
            "    void usar() {\n"
            "        int r = somar(1);\n"
            "        int z = inexistente(1, 2);\n"
            "    }\n"
            "}\n"
        )
        res_err = analyze_source(err)
        self.assertFalse(res_err.success)
        self.assertGreaterEqual(len(res_err.semantic_errors), 2)

    def test_12_ausencia_falsos_erros_system_out_println(self):
        source = (
            "public class Ola {\n"
            "    public static void main(String[] args) {\n"
            '        String nome = "AV3";\n'
            '        System.out.println("Compilador " + nome);\n'
            "        double raiz = Math.sqrt(16.0);\n"
            "        int tam = nome.length();\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)
        self.assertEqual(len(res.semantic_errors), 0)

    def test_13_construcoes_modernas_sem_falsos_erros(self):
        source = (
            "import java.util.List;\n"
            "import java.util.ArrayList;\n"
            "public record Ponto(int x, int y) {}\n"
            "enum Cor { VERMELHO, AZUL }\n"
            "interface Operacao { int aplicar(int v); }\n"
            "public class Moderno {\n"
            "    public static void demo(Object obj, List<String> itens) {\n"
            "        Operacao op = v -> v * 2;\n"
            "        var p = new Ponto(3, 4);\n"
            "        if (obj instanceof String s) {\n"
            "            System.out.println(s.toUpperCase());\n"
            "        }\n"
            "        String rotulo = switch (p.x()) {\n"
            '            case 3 -> "tres";\n'
            '            default -> "outro";\n'
            "        };\n"
            "        int total = op.aplicar(p.y());\n"
            "        System.out.println(rotulo + total);\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertIsNotNone(res.ast)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_14_auditoria_obrigatoria_tabela_de_simbolos(self):
        source = (
            "public class Escola {\n"
            "    public static int alunos = 0;\n"
            "    private double media = 8.5;\n"
            "    public boolean aberta = true;\n"
            "\n"
            "    public static void registrar(String curso, int vagas, double nota, boolean ativa) {\n"
            "        int inscritos = vagas;\n"
            "        double taxa = nota + 1.0;\n"
            '        String status = "ok";\n'
            "        boolean pronto = ativa;\n"
            "        if (pronto) {\n"
            "            inscritos = inscritos + 1;\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        res = analyze_source(source)
        self.assertTrue(res.success, msg=res.semantic_errors)

        syms = res.symbol_table.all()
        names = [s["name"] for s in syms]
        by_name = {s["name"]: s for s in syms}

        # Ordem de inserção monotônica 1..N
        self.assertEqual([s["order"] for s in syms], list(range(1, len(syms) + 1)))

        # Palavras reservadas reconhecidas pelo Lexer e sem duplicação
        for kw in ("public", "class", "static", "private", "void", "int", "double", "boolean", "if"):
            self.assertIn(kw, by_name, msg=f"Palavra reservada '{kw}' ausente da tabela")
            self.assertEqual(names.count(kw), 1, msg=f"Palavra reservada '{kw}' duplicada na tabela")
            self.assertEqual(by_name[kw]["category"], "palavra_reservada")

        # Tipos primitivos e void têm tipo='tipo'; demais palavras reservadas não são identificadores comuns
        for kw_tipo in ("int", "double", "boolean", "void"):
            self.assertEqual(by_name[kw_tipo]["type"], "tipo")
        self.assertEqual(by_name["String"]["category"], "tipo")

        # Identificadores declarados diferenciados por categoria
        self.assertEqual(by_name["Escola"]["category"], "classe")
        self.assertEqual(by_name["alunos"]["category"], "campo")
        self.assertEqual(by_name["media"]["category"], "campo")
        self.assertEqual(by_name["aberta"]["category"], "campo")
        self.assertEqual(by_name["registrar"]["category"], "metodo")
        self.assertEqual(by_name["registrar"]["type"], "void")
        for param_name in ("curso", "vagas", "nota", "ativa"):
            self.assertEqual(by_name[param_name]["category"], "parametro")
        for var_name in ("inscritos", "taxa", "status", "pronto"):
            self.assertEqual(by_name[var_name]["category"], "variavel")


if __name__ == "__main__":
    unittest.main()
