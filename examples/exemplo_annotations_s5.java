@AuditRoles({
    @AuditRole("PACKAGE_READ")
})
package br.com.compilador.s5;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Repeatable;
import java.lang.annotation.Target;
import java.util.ArrayList;
import java.util.List;

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@interface EntityMarker {
}

@Target({ElementType.TYPE, ElementType.METHOD, ElementType.PACKAGE})
@Retention(RetentionPolicy.RUNTIME)
@interface AuditRoles {
    AuditRole[] value();
}

@Target({ElementType.TYPE, ElementType.METHOD, ElementType.PACKAGE})
@Retention(RetentionPolicy.RUNTIME)
@Repeatable(AuditRoles.class)
@interface AuditRole {
    String value();
    int level() default 1;
}

@Target(ElementType.TYPE_USE)
@Retention(RetentionPolicy.RUNTIME)
@interface NonNull {
}

@Target(ElementType.TYPE_USE)
@Retention(RetentionPolicy.RUNTIME)
@interface Immutable {
}

@Target(ElementType.TYPE_PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
@interface BoundedType {
}

@Target({ElementType.FIELD, ElementType.PARAMETER, ElementType.LOCAL_VARIABLE})
@Retention(RetentionPolicy.RUNTIME)
@interface Validated {
    String rule() default "not-empty";
}

enum Ambiente {
    DEV, HOMOLOG, PROD
}

@interface Detalhe {
    String chave();
    int ordem() default 0;
}

@interface ServiceConfig {
    int DEFAULT_PORT = 8080;
    String nome();
    Ambiente ambiente() default Ambiente.PROD;
    Class<?> contrato() default Object.class;
    Class<? extends Number> versaoNumerica() default Integer.class;
    String[] tags() default { "java26", "s5", };
    Detalhe detalhe() default @Detalhe(chave = "padrao", ordem = 1);
    int porta() default DEFAULT_PORT;
}

interface ContratoBase {
    @AuditRole("EXEC")
    void executar();
}

@EntityMarker
@AuditRole("USER")
@AuditRole(value = "ADMIN", level = 2)
@ServiceConfig(
    nome = "Catalogo",
    ambiente = Ambiente.HOMOLOG,
    contrato = ContratoBase.class,
    tags = { "api", "v26", },
    detalhe = @Detalhe(chave = "principal", ordem = 10)
)
record RegistroItem(@Validated(rule = "positive") int codigo, @NonNull String nome, String @NonNull ... etiquetas)
        implements @NonNull ContratoBase {

    public RegistroItem {
        if (codigo < 0) {
            codigo = 0;
        }
    }

    @Override
    public int codigo() {
        return codigo;
    }

    @Override
    public void executar() {
        String s = nome;
    }
}

public class ServicoAnotacoes<@BoundedType T extends @NonNull Number> implements @NonNull ContratoBase {

    @Validated(rule = "non-empty")
    private final List<@NonNull String> historico = new @NonNull ArrayList<>();

    private int @Immutable [] matriz @Immutable [];

    @Override
    @AuditRole("RUN_SERVICE")
    public void executar(@Immutable ServicoAnotacoes<T> this) {
        @Validated(rule = "local") final int limite = 3;
        Object bruto = "Compilador";
        if (bruto instanceof @NonNull String) {
            String texto = (@NonNull String) bruto;
            for (@NonNull String item : historico) {
                int len = limite;
            }
        }
    }
}
