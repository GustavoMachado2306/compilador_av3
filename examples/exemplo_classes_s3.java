package com.empresa.cadastro;

import java.util.List;
import static java.lang.Math.max;

/**
 * Exemplo Canônico da Etapa S3 - Java SE 26:
 * Classes, Campos, Métodos, Construtores, Flexible Constructor Bodies,
 * Receiver Parameters, Inicializadores e Classes Aninhadas.
 */
public class Pessoa {

    // 1. Campos simples, múltiplos e inicializadores independentes
    private final String nome;
    private int idade, peso, altura;
    private static int totalPessoas;
    private int matriz[][], vetor[];
    private int[] buffer, historico[];

    // 2. Inicializador estático
    static {
        totalPessoas = 0;
    }

    // 3. Inicializador de instância
    {
        this.idade = 18;
    }

    // 4. Construtor com invocação alternada this(...)
    public Pessoa() {
        this("Sem Nome", 0);
    }

    // 5. Construtor com Flexible Constructor Body (JEP 513 / Java SE 26):
    // Prólogo de validação e cálculo preliminar antes da invocação super(...)
    public Pessoa(String nome, int idade) {
        int idadeValidada = max(0, idade);
        if (idadeValidada < 0) {
            throw new IllegalArgumentException();
        }

        super();

        this.nome = nome;
        this.idade = idadeValidada;
        totalPessoas++;
    }

    // 6. Construtor genérico
    public <T> Pessoa(T identificadorGenerico) {
        super();
        this.nome = "Generico";
    }

    // 7. Método com Receiver Parameter explícito (JLS §8.4.1)
    public void validar(Pessoa this) {
        if (this.idade < 0) {
            throw new IllegalStateException();
        }
    }

    // 8. Método genérico com múltiplos bounds
    public <T extends Number & Comparable<T>> T escolherMaior(T a, T b) {
        return a;
    }

    // 9. Método com parâmetros múltiplos, varargs e variável não nomeada local (JEP 456)
    public void registrarContatos(String principal, String... secundarios) {
        int _ = 0; // Variável local não nomeada permitida no Java 21+
    }

    // 10. Métodos com dimensões antes, depois e combinadas no retorno (JLS §8.4.5 e §10.2)
    public int[][] primeiro() {
        return null;
    }

    public int segundo()[][] {
        return null;
    }

    public int[][] terceiro()[][] {
        return null;
    }

    public String[] quarto() {
        return null;
    }

    public int[][] gerarCoordenadas()[][] {
        return null;
    }

    // 11. Classe aninhada (Inner Class)
    public class Endereco {
        private String rua, cidade, cep;

        // Construtor de classe aninhada com receiver parameter qualificado
        public Endereco(Pessoa Pessoa.this, String rua, String cidade) {
            this.rua = rua;
            this.cidade = cidade;
        }

        public String getRua() {
            return this.rua;
        }
    }
}

