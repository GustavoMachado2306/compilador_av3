package com.exemplo.java26.s4;

import java.util.List;
import java.io.Serializable;

@Deprecated
public sealed interface Forma permits Circulo, Retangulo, Quadrilatero {
    double PI = 3.141592653589793;
    int DIMENSAO_PADRAO = 2;

    double area();

    default String descricao() {
        return formatarResumo("Forma", area());
    }

    static double dobroDaArea(Forma f) {
        return f.area() * 2.0;
    }

    private String formatarResumo(String titulo, double valor) {
        return titulo + ": area=" + valor;
    }

    interface Metrica<T extends Number> {
        T medir();
    }

    enum Unidade {
        METRO("m", 1.0) {
            @Override
            public double converterParaMetro(double v) {
                return v;
            }
        },
        CENTIMETRO("cm", 0.01) {
            @Override
            public double converterParaMetro(double v) {
                return v * 0.01;
            }
        };

        private final String simbolo;
        private final double fator;

        private Unidade(String simbolo, double fator) {
            this.simbolo = simbolo;
            this.fator = fator;
        }

        private Unidade(String simbolo) {
            this(simbolo, 1.0);
        }

        public abstract double converterParaMetro(double v);

        public String getSimbolo() {
            return simbolo;
        }
    }
}

public non-sealed interface Quadrilatero extends Forma {
    int lados();
}

public record Circulo(double raio, @Deprecated String... etiquetas) implements Forma {
    public static final double RAIO_MINIMO = 0.001;

    public Circulo {
        if (raio < RAIO_MINIMO) {
            raio = RAIO_MINIMO;
        }
    }

    public Circulo() {
        this(1.0, "padrao");
    }

    @Override
    public double area() {
        return Forma.PI * raio * raio;
    }
}

public record Retangulo(double largura, double altura) implements Forma, Quadrilatero, Serializable {
    public Retangulo(double largura, double altura) {
        this.largura = largura;
        this.altura = altura;
    }

    @Override
    public double area() {
        return largura * altura;
    }

    @Override
    public int lados() {
        return 4;
    }

    public record Dimensao(double valor) {}
}

public record Caixa<T extends Forma>(T conteudo, String rotulo) {
    public Caixa {
        rotulo = rotulo.trim();
    }
}
