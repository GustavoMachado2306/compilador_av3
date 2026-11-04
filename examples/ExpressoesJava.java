package com.exemplo.expressoes;

import java.util.List;

public class ExpressoesJava {
    private int contador = 0;
    private Servico servico = new Servico();

    public void demonstrarOperadores() {
        int a = 10;
        int b = 20;
        int c = a + b * 2;
        boolean cond = (c >= 50 && a != 0) || !false;
        int resultado = cond ? a : b;

        int[] numeros = new int[5];
        numeros[0] = 10;
        numeros[1] = (int) (c / 2);

        String texto = (String) "Processamento Java";
        this.contador += resultado;
        this.contador++;

        this.servico.executar(x -> x * 2);
        System.out.println(texto);
    }
}
