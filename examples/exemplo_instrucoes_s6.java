package exemplos.s6;

import java.io.IOException;
import java.sql.SQLException;

class CanalRecurso implements AutoCloseable {
    public void registrar(String evento) {}

    @Override
    public void close() {}
}

public class ExemploInstrucoesS6 {
    private final Object trava = new Object();

    private void operacaoArriscada(int codigo) throws IOException, SQLException {
        if (codigo < -100) {
            throw new IOException("Codigo invalido");
        }
        if (codigo == -200) {
            throw new SQLException("Falha SQL");
        }
    }

    public int executarFluxo(int codigo, boolean ativo, int[] itens) {
        // 1. Bloco vazio e declarações locais variadas (arrays, final, anotação, var, '_')
        {}
        int acumulado = 0;
        int a = 1, b = 2;
        int matriz[][], vetor[];
        final int FATOR = 3;
        @SuppressWarnings("unused")
        int _ = 999;
        var yield = 5;
        acumulado += a + b + FATOR + yield;

        // 2. Tipos locais: interface, classe, enum e record locais (JLS §14.3)
        interface RegraLocal {
            int aplicar(int x);
        }

        class DobradorLocal implements RegraLocal {
            public int aplicar(int x) {
                return x * 2;
            }
        }

        enum Nivel {
            BAIXO,
            ALTO
        }

        record ResumoLocal(String rotulo, int total) {}

        RegraLocal regra = new DobradorLocal();
        acumulado += regra.aplicar(codigo);

        // 3. Condicionais aninhadas com resolução normativa do dangling else (StatementNoShortIf)
        if (ativo)
            if (codigo > 0)
                acumulado += 10;
            else
                acumulado -= 1;

        assert acumulado >= 0 : "Acumulado nao pode ser negativo neste ponto";

        // 4. Laços tradicionais, múltiplos, aprimorados (com var e '_') e labels
        int idx;
        int lim;
        for (idx = 0, lim = 3; idx < lim; idx++, lim--) {
            acumulado++;
        }

        int j = 0;
        while (j < 2) {
            j++;
        }

        do {
            j--;
        } while (j > 0);

        for (var item : itens) {
            acumulado += item;
        }
        for (var _ : itens) {
            acumulado++;
        }

        externo:
        for (int p = 0; p < 3; p++) {
            for (int q = 0; q < 3; q++) {
                if (q == 1) {
                    continue externo;
                }
                if (p == 2) {
                    break externo;
                }
            }
        }

        blocoRotulado: {
            if (codigo < 0) {
                break blocoRotulado;
            }
            acumulado++;
        }

        // 5. Switch tradicional com fall-through (:) e switch com rules (->) e case null
        switch (codigo) {
            case 1:
                acumulado += 5;
                break;
            case 2:
            case 3:
                acumulado += 7;
                break;
            default:
                acumulado += 1;
        }

        Object marcador = ativo ? "OK" : null;
        switch (marcador) {
            case null -> acumulado += 0;
            default -> acumulado += 2;
        }

        Nivel nivel = codigo > 5 ? Nivel.ALTO : Nivel.BAIXO;
        int bonus = switch (nivel) {
            case ALTO -> 20;
            case BAIXO -> {
                int parcial = 4;
                yield parcial;
            }
        };
        acumulado += bonus;

        // 6. Try/catch/multicatch/finally, try-with-resources (var + referência) e synchronized
        try {
            operacaoArriscada(codigo);
        } catch (IOException | SQLException ex) {
            acumulado = 0;
        } finally {
            acumulado++;
        }

        final CanalRecurso existente = new CanalRecurso();
        try (var aberto = new CanalRecurso(); existente;) {
            aberto.registrar("inicio");
            existente.registrar("fim");
        }

        synchronized (trava) {
            ResumoLocal resumo = new ResumoLocal("ok", acumulado);
            acumulado = resumo.total();
        }

        return acumulado;
    }
}
