import module java.base;

module br.com.exemplo.sistema {
    requires java.base;
    requires transitive java.logging;
    exports br.com.exemplo.api;
    opens br.com.exemplo.interno to moduloA;
}

