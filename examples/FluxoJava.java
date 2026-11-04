package br.com.exemplo.fluxo;

import java.util.List;

public class FluxoJava {
    private int contador = 0;
    private final String autor = "Compilador AV3";

    public FluxoJava(int inicio) {
        this.contador = inicio;
    }

    public void demonstrarControle(int limite) {
        // Declaração de variável local com e sem inicializador
        int soma = 0;
        String status;

        // Estrutura Condicional: if / else if / else
        if (limite >= 10) {
            status = "Alto";
        } else if (limite >= 5) {
            status = "Medio";
        } else {
            status = "Baixo";
        }

        // Chamada de método como instrução
        System.out.println(status);

        // Laço while e controle com break/continue
        while (this.contador < limite) {
            this.contador++;
            if (this.contador == 3) {
                continue;
            }
            if (this.contador > 8) {
                break;
            }
        }

        // Laço do/while
        do {
            this.contador--;
        } while (this.contador > 0);

        // Laço for tradicional
        for (int i = 0; i < limite; i++) {
            soma += i;
        }

        // Bloco aninhado
        {
            int blocoLocal = 100;
            soma += blocoLocal;
        }

        // Asserção
        assert soma >= 0 : "Soma deve ser positiva";

        // Instrução vazia
        ;

        return;
    }

    public void demonstrarExcecoes(Object lock) {
        // Bloco sincronizado
        synchronized (lock) {
            this.contador = 42;
        }

        // Tratamento de exceções try/catch/finally e try-with-resources
        try (var recurso = abrirRecurso()) {
            recurso.executar();
        } catch (IllegalArgumentException e) {
            System.out.println(e.getMessage());
        } catch (Exception e) {
            throw new RuntimeException(e);
        } finally {
            this.contador = 0;
        }
    }
}
