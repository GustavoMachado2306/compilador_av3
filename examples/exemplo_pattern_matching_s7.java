// Exemplo completo da Etapa S7 — Patterns, Pattern Matching e Switch Moderno (Java SE 26)

sealed interface Expressao permits Numero, Texto, Soma, Par {}

record Numero(int valor) implements Expressao {}
final class Texto implements Expressao {
    final String conteudo;
    Texto(String conteudo) {
        this.conteudo = conteudo;
    }
}
record Soma(Expressao esquerda, Expressao direita) implements Expressao {}
record Par<A, B>(A primeiro, B segundo) implements Expressao {}

public class ExemploPatternMatchingS7 {

    static int avaliar(Expressao expr) {
        return switch (expr) {
            case Numero(var v) when v >= 0 -> v;
            case Numero(_) -> 0;
            case Texto t -> t.conteudo.length();
            case Soma(Numero(var a), Numero(var b)) -> a + b;
            case Soma(var esq, var dir) -> avaliar(esq) + avaliar(dir);
            case Par(var a, _) -> a instanceof Expressao e ? avaliar(e) : 0;
        };
    }

    static String classificarObjeto(Object obj) {
        if (!(obj instanceof String s) || s.isEmpty()) {
            return switch (obj) {
                case null -> "nulo ou texto vazio";
                case Numero(var v) when v > 100 -> "numero grande: " + v;
                case Numero _ -> "numero qualquer";
                case Par<String, Integer>(String chave, Integer codigo) -> chave + ":" + codigo;
                case int[] numeros when numeros.length > 0 -> "array com " + numeros.length;
                case String _, Expressao _ -> "vazio ou expressao";
                default -> "desconhecido";
            };
        }
        int tamanho = obj instanceof CharSequence cs ? cs.length() : 0;
        String when = "contextual";
        return s + " (" + tamanho + ", " + when + ")";
    }

    static String fallbackSeguro(Object obj) {
        return switch (obj) {
            case Par(var a, var b) -> a.toString() + ":" + b.toString();
            case null, default -> "vazio";
        };
    }

    static void demonstrarFluxoECasos(Object valor, boolean interromper) {
        if (!(valor instanceof String texto)) {
            return;
        }
        System.out.println(texto.toUpperCase());

        externo: {
            if (interromper) {
                break externo;
            }
            System.out.println("Bloco rotulado concluido normalmente");
        }
    }

    public static void main(String[] args) {
        Expressao e1 = new Soma(new Numero(10), new Numero(20));
        Expressao e2 = new Par<String, Integer>("S7", 26);
        System.out.println(avaliar(e1));
        System.out.println(classificarObjeto(e2));
        demonstrarFluxoECasos("Java SE 26", false);
    }

    /*
     * Referência negativa (NÃO deve compilar se descomentada — erro de dominância JLS §14.11.1):
     *
     * static void erroDominancia(Object o) {
     *     switch (o) {
     *         case Object x -> System.out.println(x);
     *         case String s -> System.out.println(s); // dominado por 'Object x'
     *     }
     * }
     *
     * Nota JEP 530 (Preview — Auditoria S7.1):
     * `case Numero(int v) -> ...` e `o instanceof int i` exigem `enable_preview_primitive_patterns=True`;
     * no Java SE 26 estável (padrão), utilize `Numero(var v)` ou `Numero(_)`.
     */
}
