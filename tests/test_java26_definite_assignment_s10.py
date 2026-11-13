import unittest
from src.main import analyze_source


class TestJava26DefiniteAssignmentS10(unittest.TestCase):
    """Valida Análise de Atribuição Definitiva (DA/DU) e Fluxo de Controle conforme JLS §16 (S10)."""

    def _ok(self, source: str):
        res = analyze_source(source)
        self.assertTrue(
            res.success,
            msg=f"Esperado sucesso, mas houve erros: sint={res.syntactic_error} sem={res.semantic_errors}",
        )
        return res

    def _bad(self, source: str, expected_substr: str = None):
        res = analyze_source(source)
        self.assertFalse(res.success, msg="Esperava-se erro semântico, mas a análise foi bem-sucedida.")
        if expected_substr:
            joined = "\n".join(str(e) for e in res.semantic_errors)
            self.assertIn(expected_substr.lower(), joined.lower(), msg=res.semantic_errors)
        return res

    # ------------------------------------------------------------------
    # Exemplos obrigatórios do enunciado S10
    # ------------------------------------------------------------------
    def test_01_exemplos_obrigatorios_enunciado(self):
        self._bad(
            """
            class Exemplo {
                void exemplo(boolean condicao) {
                    int x;
                    System.out.println(x);
                }
            }
            """,
            "não ter sido inicializada",
        )
        self._ok(
            """
            class Exemplo {
                void exemplo(boolean condicao) {
                    int x;
                    if (condicao) {
                        x = 10;
                    } else {
                        x = 20;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        self._ok(
            """
            class Exemplo {
                void exemplo(boolean condicao) {
                    final int x;
                    if (condicao) {
                        x = 10;
                    } else {
                        x = 20;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        self._bad(
            """
            class Exemplo {
                void exemplo() {
                    final int x = 10;
                    x = 20;
                }
            }
            """,
            "final",
        )

    # ------------------------------------------------------------------
    # 1. Leituras de variáveis locais não inicializadas (todos contextos)
    # ------------------------------------------------------------------
    def test_02_leitura_variavel_local_nao_inicializada(self):
        self._bad("class A { int m() { int x; return x; } }", "inicializada")
        self._bad("class A { void m() { int x; x = x + 1; } }", "inicializada")
        self._bad("class A { void m() { int x; x += 1; } }", "inicializada")
        self._bad("class A { void m() { int x; x++; } }", "inicializada")
        self._bad("class A { void m() { int[] a; a[0] = 1; } }", "inicializada")
        self._bad("class A { void m(int[] a) { int i; a[i] = 1; } }", "inicializada")
        self._bad("class A { void f(int k) {} void m() { int x; f(x); } }", "inicializada")
        # Avaliação esquerda-para-direita e atribuição encadeada válidos
        self._ok("class A { void m() { int a; int b; a = b = 10; System.out.println(a + b); } }")

    # ------------------------------------------------------------------
    # 2. Variáveis 'final' (DA e DU)
    # ------------------------------------------------------------------
    def test_03_atribuicao_definitiva_e_unassignment_final(self):
        # Blank final inicializada uma única vez antes do uso
        self._ok(
            """
            class F {
                void m() {
                    final int x;
                    x = 42;
                    System.out.println(x);
                }
            }
            """
        )
        # Reatribuição de blank final após atribuição condicional parcial
        self._bad(
            """
            class F {
                void m(boolean c) {
                    final int x;
                    if (c) {
                        x = 1;
                    }
                    x = 2;
                }
            }
            """,
            "final",
        )
        # Reatribuição de blank final já atribuída nos dois ramos
        self._bad(
            """
            class F {
                void m(boolean c) {
                    final int x;
                    if (c) x = 1;
                    else x = 2;
                    x = 3;
                }
            }
            """,
            "final",
        )
        # Leitura de blank final antes de inicializar
        self._bad("class F { void m() { final int x; System.out.println(x); } }", "inicializada")
        # Operador composto em blank final
        self._bad("class F { void m() { final int x; x += 1; } }")
        # Auto-atribuição dupla de final no mesmo comando: x = (x = 1)
        self._bad("class F { void m() { final int x; x = (x = 1); } }", "final")
        # Captura lambda efetivamente final com inicialização em if/else
        self._ok(
            """
            class F {
                void m(boolean c) {
                    int x;
                    if (c) {
                        x = 10;
                    } else {
                        x = 20;
                    }
                    Runnable r = () -> System.out.println(x);
                }
            }
            """
        )

    # ------------------------------------------------------------------
    # 3. Caminhos if / else, constantes e curto-circuito booleano
    # ------------------------------------------------------------------
    def test_04_caminhos_if_else_e_curto_circuito(self):
        # Atribuição em apenas alguns caminhos (sem else)
        self._bad(
            """
            class B {
                void m(boolean c) {
                    int x;
                    if (c) {
                        x = 10;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # Condição constante true
        self._ok(
            """
            class B {
                void m() {
                    int x;
                    if (true) {
                        x = 10;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # Condição constante false
        self._bad(
            """
            class B {
                void m() {
                    int x;
                    if (false) {
                        x = 10;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # Curto-circuito booleano && e || e ternário ?:
        self._ok(
            """
            class B {
                void m(boolean c) {
                    int x;
                    if (c && (x = 5) > 0) {
                        System.out.println(x);
                    }
                    int y;
                    if (c || (y = 7) > 0) {
                    } else {
                        System.out.println(y);
                    }
                    int z = c ? 1 : 2;
                    System.out.println(z);
                }
            }
            """
        )
        self._bad(
            """
            class B {
                void m(boolean c) {
                    int x;
                    if (c && (x = 5) > 0) {
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )

    # ------------------------------------------------------------------
    # 4. Retornos e caminhos que não completam normalmente
    # ------------------------------------------------------------------
    def test_05_return_throw_caminhos_abruptos(self):
        self._ok(
            """
            class R {
                int m(boolean c) {
                    int x;
                    if (c) {
                        return 0;
                    } else {
                        x = 10;
                    }
                    return x;
                }
            }
            """
        )
        self._ok(
            """
            class R {
                void m(boolean c) {
                    final int x;
                    if (c) {
                        throw new RuntimeException();
                    }
                    x = 99;
                    System.out.println(x);
                }
            }
            """
        )
        self._ok(
            """
            class R {
                int m(boolean c) {
                    int x;
                    if (c) {
                        x = 1;
                    } else {
                        return -1;
                    }
                    return x;
                }
            }
            """
        )

    # ------------------------------------------------------------------
    # 5. Switch statements e switch expressions
    # ------------------------------------------------------------------
    def test_06_switch_statements_e_expressions(self):
        # Switch statement tradicional com default inicializando em todos caminhos
        self._ok(
            """
            class SW {
                void m(int op) {
                    int x;
                    switch (op) {
                        case 1:
                            x = 10;
                            break;
                        case 2:
                        default:
                            x = 20;
                            break;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # Switch statement sem default não garante atribuição após o switch
        self._bad(
            """
            class SW {
                void m(int op) {
                    int x;
                    switch (op) {
                        case 1: x = 10; break;
                        case 2: x = 20; break;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # Fall-through para outro case violando DU de variável final
        self._bad(
            """
            class SW {
                void m(int op) {
                    final int x;
                    switch (op) {
                        case 1:
                            x = 10;
                        case 2:
                            x = 20;
                            break;
                        default:
                            x = 30;
                    }
                }
            }
            """,
            "final",
        )
        # Switch statement com setas (->) e default que lança exceção
        self._ok(
            """
            class SW {
                void m(int op) {
                    int x;
                    switch (op) {
                        case 1 -> x = 1;
                        case 2 -> { x = 2; }
                        default -> throw new IllegalStateException();
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # Switch expression com yield atribuindo variável externa em todos os ramos
        self._ok(
            """
            class SW {
                int m(int op) {
                    final int x;
                    int r = switch (op) {
                        case 1 -> { x = 10; yield 1; }
                        default -> { x = 20; yield 2; }
                    };
                    return x + r;
                }
            }
            """
        )
        # Switch expression em que falta atribuir em um dos ramos
        self._bad(
            """
            class SW {
                int m(int op) {
                    int x;
                    int r = switch (op) {
                        case 1 -> { x = 10; yield 1; }
                        default -> 2;
                    };
                    return x + r;
                }
            }
            """,
            "inicializada",
        )

    # ------------------------------------------------------------------
    # 6. Laços while, do-while, for, for-each (0+ iterações, final, declarações internas)
    # ------------------------------------------------------------------
    def test_07_lacos_zero_ou_mais_iteracoes_e_final(self):
        # while com 0 ou mais iterações: não garante inicialização após o laço
        self._bad(
            """
            class L {
                void m(boolean cond) {
                    int x;
                    while (cond) {
                        x = 1;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # for tradicional com 0 ou mais iterações
        self._bad(
            """
            class L {
                void m(int n) {
                    int x;
                    for (int i = 0; i < n; i++) {
                        x = i;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # enhanced-for com 0 ou mais iterações
        self._bad(
            """
            class L {
                void m(int[] arr) {
                    int x;
                    for (int v : arr) {
                        x = v;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # do-while executa pelo menos 1 vez -> válido ler após o laço
        self._ok(
            """
            class L {
                void m(boolean cond) {
                    int x;
                    do {
                        x = 5;
                    } while (cond);
                    System.out.println(x);
                }
            }
            """
        )
        # Variável final declarada FORA de laço não pode ser atribuída dentro de while/for/do-while(cond)
        self._bad(
            """
            class L {
                void m(boolean cond) {
                    final int x;
                    while (cond) {
                        x = 1;
                    }
                }
            }
            """,
            "final",
        )
        self._bad(
            """
            class L {
                void m(boolean cond) {
                    final int x;
                    do {
                        x = 1;
                    } while (cond);
                }
            }
            """,
            "final",
        )
        # do { x = 1; } while (false); executa exatamente uma vez -> final válida!
        self._ok(
            """
            class L {
                void m() {
                    final int x;
                    do {
                        x = 1;
                    } while (false);
                    System.out.println(x);
                }
            }
            """
        )
        # Variável final declarada DENTRO do laço é redeclarada a cada iteração -> válida!
        self._ok(
            """
            class L {
                void m(int n) {
                    for (int i = 0; i < n; i++) {
                        final int localNoLaco;
                        localNoLaco = i * 2;
                        System.out.println(localNoLaco);
                    }
                }
            }
            """
        )

    # ------------------------------------------------------------------
    # 7. break e continue (simples e com rótulos)
    # ------------------------------------------------------------------
    def test_08_break_e_continue_simples_e_rotulados(self):
        # while(true) com atribuição antes do break -> válido
        self._ok(
            """
            class BC {
                void m() {
                    int x;
                    while (true) {
                        x = 42;
                        break;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # while(true) com break antes da atribuição -> erro
        self._bad(
            """
            class BC {
                void m(boolean c) {
                    int x;
                    while (true) {
                        if (c) break;
                        x = 42;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # continue em do-while pula atribuição -> erro após laço
        self._bad(
            """
            class BC {
                void m(boolean c) {
                    int x;
                    do {
                        if (c) continue;
                        x = 10;
                    } while (false);
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # continue rotulado + break rotulado em laços aninhados
        self._ok(
            """
            class BC {
                void m() {
                    int x;
                    externo:
                    while (true) {
                        while (true) {
                            x = 7;
                            break externo;
                        }
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # Bloco rotulado com break
        self._ok(
            """
            class BC {
                void m(boolean c) {
                    int x;
                    bloco: {
                        x = 1;
                        if (c) break bloco;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        self._bad(
            """
            class BC {
                void m(boolean c) {
                    int x;
                    bloco: {
                        if (c) break bloco;
                        x = 1;
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )

    # ------------------------------------------------------------------
    # 8. try / catch / finally
    # ------------------------------------------------------------------
    def test_09_try_catch_e_finally(self):
        # try + catch ambos atribuem -> válido
        self._ok(
            """
            class TC {
                void m() {
                    int x;
                    try {
                        x = 10;
                    } catch (Exception e) {
                        x = 20;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # try atribui, catch não -> erro
        self._bad(
            """
            class TC {
                void m() {
                    int x;
                    try {
                        x = 10;
                    } catch (Exception e) {
                    }
                    System.out.println(x);
                }
            }
            """,
            "inicializada",
        )
        # Leitura dentro de catch de variável atribuída apenas dentro de try -> erro
        self._bad(
            """
            class TC {
                void f() {}
                void m() {
                    int x;
                    try {
                        x = 10;
                        f();
                    } catch (Exception e) {
                        System.out.println(x);
                    }
                }
            }
            """,
            "inicializada",
        )
        # Blank final atribuída em try e novamente em catch -> erro (not DU no catch)
        self._bad(
            """
            class TC {
                void f() {}
                void m() {
                    final int x;
                    try {
                        x = 1;
                        f();
                    } catch (Exception e) {
                        x = 2;
                    }
                }
            }
            """,
            "final",
        )
        # finally inicializa variável -> válido após try/finally
        self._ok(
            """
            class TC {
                void m() {
                    int x;
                    try {
                        System.out.println("ok");
                    } finally {
                        x = 99;
                    }
                    System.out.println(x);
                }
            }
            """
        )
        # finally não garante inicialização antes do 'return x' dentro do try!
        self._bad(
            """
            class TC {
                int m() {
                    int x;
                    try {
                        return x;
                    } finally {
                        x = 99;
                    }
                }
            }
            """,
            "inicializada",
        )
        # Blank final atribuída no try e no finally -> erro
        self._bad(
            """
            class TC {
                void m() {
                    final int x;
                    try {
                        x = 1;
                    } finally {
                        x = 2;
                    }
                }
            }
            """
        )
        # break passando por finally que inicializa x -> válido após laço
        self._ok(
            """
            class TC {
                void m() {
                    int x;
                    while (true) {
                        try {
                            break;
                        } finally {
                            x = 5;
                        }
                    }
                    System.out.println(x);
                }
            }
            """
        )

    # ------------------------------------------------------------------
    # 9. Inicialização de campos vs variáveis locais
    # ------------------------------------------------------------------
    def test_10_campos_vs_variaveis_locais(self):
        # Campos não-finais possuem valor padrão -> leitura sem inicialização explícita é válida
        self._ok(
            """
            class Campos {
                int campoInstancia;
                static String campoEstatico;
                int lerCampos() {
                    return campoInstancia + (campoEstatico == null ? 0 : 1);
                }
            }
            """
        )
        # Blank final de instância inicializado em todos caminhos do construtor -> válido
        self._ok(
            """
            class Campos {
                final int codigo;
                Campos(boolean ok) {
                    if (ok) {
                        this.codigo = 1;
                    } else {
                        this.codigo = 2;
                    }
                }
            }
            """
        )
        # Blank final de instância NÃO inicializado em construtor -> erro
        self._bad(
            """
            class Campos {
                final int codigo;
                Campos() {
                }
            }
            """,
            "final",
        )
        # Blank final de instância não inicializado em algum ramo do construtor -> erro
        self._bad(
            """
            class Campos {
                final int codigo;
                Campos(boolean ok) {
                    if (ok) {
                        this.codigo = 1;
                    }
                }
            }
            """,
            "final",
        )
        # Blank static final inicializado via bloco static -> válido
        self._ok(
            """
            class Campos {
                static final int LIMITE;
                static {
                    LIMITE = 100;
                }
            }
            """
        )
        # Blank static final sem inicialização -> erro
        self._bad(
            """
            class Campos {
                static final int LIMITE;
            }
            """,
            "final",
        )

    # ------------------------------------------------------------------
    # 10. Variáveis em blocos aninhados e escopos isolados
    # ------------------------------------------------------------------
    def test_11_blocos_aninhados(self):
        # Dois blocos disjuntos declarando variável de mesmo nome: segundo bloco não herda DA do primeiro!
        self._bad(
            """
            class Blocos {
                void m() {
                    {
                        int x;
                        x = 10;
                    }
                    {
                        int x;
                        System.out.println(x);
                    }
                }
            }
            """,
            "inicializada",
        )
        # Variável declarada fora é atribuída dentro de bloco aninhado -> válido após bloco
        self._ok(
            """
            class Blocos {
                void m() {
                    int x;
                    {
                        final int interno = 42;
                        x = interno;
                    }
                    System.out.println(x);
                }
            }
            """
        )


if __name__ == "__main__":
    unittest.main()

