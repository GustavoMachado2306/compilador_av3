package br.compilador.s8;

import java.io.Serializable;
import java.util.*;
import java.util.function.*;

public class ExemploExpressoesS8 {

    sealed interface Resultado permits Ok, Erro {}
    record Ok<T>(T valor) implements Resultado {}
    record Erro(String mensagem) implements Resultado {}

    static class Caixa<T> {
        private final T conteudo;

        Caixa(T conteudo) {
            this.conteudo = conteudo;
        }

        T obter() {
            return conteudo;
        }
    }

    static class CalculadoraBase {
        protected int fator = 2;

        Number combinar(int a, int b) {
            return a + b;
        }
    }

    static class CalculadoraAvancada extends CalculadoraBase {
        @Override
        Integer combinar(int a, int b) {
            return (a + b) * super.fator;
        }

        double combinar(double a, double b) {
            return a * b;
        }
    }

    static String formatarComPrefixo(String prefixo, int n) {
        return prefixo + ":" + n;
    }

    public static void executar() {
        // 1. Aritmética, precedência e promoção numérica binária
        byte b = 10;
        short s = 20;
        int somaPromovida = b + s * 2;
        long total = somaPromovida + 100L;
        double escala = total / 2.5d;

        // 2. Atribuições simples, compostas, incremento/decremento e ternário
        int contador = 0;
        contador += 5;
        contador++;
        String estado = (contador > 5) ? "alto" : "baixo";

        // 3. Casts (primitivo, referência e interseção)
        int truncado = (int) escala;
        Object texto = "java26";
        var serializavel = (CharSequence & Serializable) texto;

        // 4. Sobrecarga, superclasse, genéricos e diamond <>
        CalculadoraAvancada calc = new CalculadoraAvancada();
        Integer r1 = calc.combinar(3, 4);
        double r2 = calc.combinar(3.0, 4.0);
        Caixa<String> caixa = new Caixa<>(estado);
        List<String> listaSingleton = Collections.singletonList(caixa.obter());

        // 5. Arrays (1D, multidimensional e JLS §15.10.1 com inicializador)
        int[] matrizLinha = new int[] { 1, 2, 3, truncado };
        int[][] grade = new int[2][3];
        grade[0][1] = matrizLinha.length;

        // 6. Lambdas, captura efetivamente final e poly expressions
        final int offset = 10;
        IntUnaryOperator ajustar = x -> x + offset;
        BiFunction<String, Integer, String> fmt = (var p, var n) -> formatarComPrefixo(p, ajustar.applyAsInt(n));

        // 7. Method references (estática, unbound, bound, construtor e criação de array)
        Function<String, Integer> tamanho = String::length;
        Supplier<String> fabricaVazia = String::new;
        IntFunction<int[]> fabricaArray = int[]::new;
        int[] alocado = fabricaArray.apply(tamanho.apply(fmt.apply(fabricaVazia.get(), r1)));

        // 8. Switch expression com ->, yield e pattern matching estável (Java 26)
        Resultado res = (r2 > 0.0 && alocado.length > 0 && serializavel.length() > 0)
            ? new Ok<String>(listaSingleton.get(0))
            : new Erro("vazio");

        int codigo = switch (res) {
            case Ok(var msg) when msg.length() > 0 -> 200;
            case Ok(var msg) -> {
                yield msg.length();
            }
            case Erro(String err) -> err.length() > 0 ? 500 : 400;
        };
    }
}

