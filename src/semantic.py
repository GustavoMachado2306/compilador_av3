"""
Módulo do Analisador Semântico do Compilador Java (AV3).
Responsável pela validação de escopos, verificação de variáveis e membros declarados,
duplicidade de identificadores e compatibilidade básica de tipos.
Evita falsos erros para membros qualificados externos como System.out.println(...).
"""

import math
import re
import struct
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from .type_inference import JLS18ConstraintSolver
from .exception_analysis import ExceptionAnalyzer
from .inheritance_access import InheritanceAccessAnalyzer
from .classpath_resolver import (
    ExternalSymbolResolver,
    ExternalTypeInfo,
    ExternalMethodInfo,
    ExternalFieldInfo,
    DEFAULT_MAX_CLASS_MAJOR,
)
from .ast_nodes import (
    ASTNode, CompilationUnit, PackageDeclaration, ClassDeclaration, InterfaceDeclaration,
    InterfaceConstantDeclaration, InterfaceMethodDeclaration,
    EnumDeclaration, EnumConstant, EnumConstantBody,
    RecordDeclaration, RecordComponent,
    NormalCanonicalConstructor, CompactConstructorDeclaration, NonCanonicalRecordConstructor,
    FieldDeclaration, MethodDeclaration, ConstructorDeclaration,
    Block, ReturnStatement, Declaration, LocalVariableDeclaration, Assignment,
    BinaryOp, UnaryOp, MethodCall, Literal, Identifier, ExpressionStatement,
    EmptyStatement, IfStatement, WhileStatement, DoWhileStatement,
    ForStatement, EnhancedForStatement, SwitchStatement, SwitchCase,
    BreakStatement, ContinueStatement, ThrowStatement, AssertStatement,
    TryStatement, CatchClause, SynchronizedStatement, ConditionalExpression,
    LabeledStatement, StatementExpressionList, SwitchLabel, CaseConstantList,
    CaseLabel, DefaultLabel, SwitchBlockStatementGroup, SwitchRule, SwitchBlock,
    SwitchExpression, YieldStatement, CatchType, Resource, ResourceSpecification,
    MemberAccess, ArrayAccess, ClassLiteral,
    ObjectCreationExpression, ArrayInitializer, ArrayCreationExpression,
    CastExpression, InstanceOfExpression, PatternInstanceOfExpression,
    LambdaExpression, MethodReference,
    ModuleDeclaration, ExportsDirective, RequiresDirective, InstanceInitializer, StaticInitializer, ConstructorBody,
    SuperclassConstructorInvocation, AlternateConstructorInvocation,
    TypeReference, WildcardType, Annotation, MarkerAnnotation,
    SingleElementAnnotation, NormalAnnotation, ElementValue, ElementValueList,
    ElementValueArrayInitializer, ElementValuePair, ElementValuePairList,
    AnnotationDefaultValue, AnnotationInterfaceElementDeclaration,
    AnnotationInterfaceBody, AnnotationInterfaceDeclaration,
    ComponentPattern, Pattern, PatternVariable, TypePattern,
    ComponentPatternList, RecordPattern, MatchAllPattern, Guard,
    PatternCaseLabel
)


class SemanticError(str):
    """Exceção/mensagem estruturada de erro semântico compatível com string."""
    def __new__(cls, message: str, line: int):
        formatted = f"[ERRO SEMÂNTICO]\nLinha {line}:\n{message}"
        instance = super().__new__(cls, formatted)
        instance.message = message
        instance.line = line
        return instance


class SemanticAnalyzer:
    """
    Analisador semântico para Java (Fases A, B e C e Etapas S1-S4).
    Gerencia escopos hierárquicos e valida a consistência de tipos e símbolos,
    escopos locais em blocos/laços/métodos e previne falsos positivos para símbolos externos.
    """
    FORBIDDEN_RECORD_COMPONENTS = frozenset({
        "clone", "finalize", "getClass", "hashCode",
        "notify", "notifyAll", "toString", "wait",
    })
    FORBIDDEN_ANNOTATION_ELEMENTS = frozenset({
        "clone", "equals", "finalize", "getClass", "hashCode",
        "notify", "notifyAll", "toString", "wait", "annotationType",
    })
    PRIMITIVE_TYPES = frozenset({
        "byte", "short", "int", "long", "float", "double", "boolean", "char",
    })
    NUMERIC_PRIMITIVE_TYPES = frozenset({
        "byte", "short", "char", "int", "long", "float", "double",
    })
    WRAPPER_TO_PRIMITIVE = {
        "Byte": "byte",
        "Short": "short",
        "Character": "char",
        "Integer": "int",
        "Long": "long",
        "Float": "float",
        "Double": "double",
        "Boolean": "boolean",
    }
    BUILTIN_NON_REPEATABLE_ANNOTATIONS = frozenset({
        "Override", "Deprecated", "SuppressWarnings", "Target", "Retention",
        "Documented", "Inherited", "FunctionalInterface", "SafeVarargs", "Repeatable",
    })
    BUILTIN_ANNOTATION_TYPES = BUILTIN_NON_REPEATABLE_ANNOTATIONS | frozenset({
        "Native", "Serial",
    })
    KNOWN_ENUM_TYPES = frozenset({
        "ElementType", "RetentionPolicy",
        "java.lang.annotation.ElementType", "java.lang.annotation.RetentionPolicy",
    })
    DISALLOWED_ANNOTATION_RETURN_TYPES = frozenset({
        "Object", "java.lang.Object",
        "Integer", "Long", "Double", "Float", "Boolean", "Character", "Byte", "Short", "Number",
        "List", "Map", "Set", "Collection", "Optional", "Date", "BigDecimal", "CharSequence",
        "Throwable", "Exception", "Error", "StringBuilder", "Record", "Enum",
    })
    RETENTION_RANK = {"SOURCE": 0, "CLASS": 1, "RUNTIME": 2}
    ACCESS_RANK = {"private": 0, "package": 1, "protected": 2, "public": 3}
    KNOWN_EXCEPTION_PARENTS = {
        "Exception": "Throwable",
        "RuntimeException": "Exception",
        "Error": "Throwable",
        "VirtualMachineError": "Error",
        "OutOfMemoryError": "VirtualMachineError",
        "StackOverflowError": "VirtualMachineError",
        "LinkageError": "Error",
        "NoClassDefFoundError": "LinkageError",
        "AssertionError": "Error",
        "IOException": "Exception",
        "FileNotFoundException": "IOException",
        "EOFException": "IOException",
        "MalformedURLException": "IOException",
        "SQLException": "Exception",
        "IllegalArgumentException": "RuntimeException",
        "IllegalStateException": "RuntimeException",
        "NullPointerException": "RuntimeException",
        "IndexOutOfBoundsException": "RuntimeException",
        "ArrayIndexOutOfBoundsException": "IndexOutOfBoundsException",
        "NumberFormatException": "IllegalArgumentException",
        "ArithmeticException": "RuntimeException",
        "ClassCastException": "RuntimeException",
        "UnsupportedOperationException": "RuntimeException",
        "SecurityException": "RuntimeException",
        "NoSuchElementException": "RuntimeException",
        "ConcurrentModificationException": "RuntimeException",
        "ReflectiveOperationException": "Exception",
        "ClassNotFoundException": "ReflectiveOperationException",
        "NoSuchMethodException": "ReflectiveOperationException",
        "NoSuchFieldException": "ReflectiveOperationException",
        "InstantiationException": "ReflectiveOperationException",
        "IllegalAccessException": "ReflectiveOperationException",
        "InvocationTargetException": "ReflectiveOperationException",
        "InterruptedException": "Exception",
        "CloneNotSupportedException": "Exception",
        "ParseException": "Exception",
        "TimeoutException": "Exception",
        "ExecutionException": "Exception",
        "URISyntaxException": "Exception",
    }
    BUILTIN_TYPE_SUPERTYPES = {
        "Object": [],
        "String": ["CharSequence", "Comparable<String>", "Serializable", "Object"],
        "StringBuilder": ["CharSequence", "Appendable", "Serializable", "Object"],
        "StringBuffer": ["CharSequence", "Appendable", "Serializable", "Object"],
        "CharSequence": ["Object"],
        "Appendable": ["Object"],
        "Number": ["Serializable", "Object"],
        "Integer": ["Number", "Comparable<Integer>", "Serializable", "Object"],
        "Long": ["Number", "Comparable<Long>", "Serializable", "Object"],
        "Double": ["Number", "Comparable<Double>", "Serializable", "Object"],
        "Float": ["Number", "Comparable<Float>", "Serializable", "Object"],
        "Byte": ["Number", "Comparable<Byte>", "Serializable", "Object"],
        "Short": ["Number", "Comparable<Short>", "Serializable", "Object"],
        "Boolean": ["Comparable<Boolean>", "Serializable", "Object"],
        "Character": ["Comparable<Character>", "Serializable", "Object"],
        "Void": ["Object"],
        "Iterable": ["Object"],
        "Iterator": ["Object"],
        "ListIterator": ["Iterator<E>", "Object"],
        "Collection": ["Iterable<E>", "Object"],
        "java.util.Collection": ["Iterable<E>", "Object"],
        "List": ["Collection<E>", "Iterable<E>", "Object"],
        "java.util.List": ["Collection<E>", "Iterable<E>", "Object"],
        "ArrayList": ["List<E>", "Collection<E>", "Iterable<E>", "Serializable", "Cloneable", "Object"],
        "java.util.ArrayList": ["List<E>", "Collection<E>", "Iterable<E>", "Serializable", "Cloneable", "Object"],
        "LinkedList": ["List<E>", "Collection<E>", "Iterable<E>", "Serializable", "Cloneable", "Object"],
        "Set": ["Collection<E>", "Iterable<E>", "Object"],
        "HashSet": ["Set<E>", "Collection<E>", "Iterable<E>", "Serializable", "Cloneable", "Object"],
        "Map": ["Object"],
        "HashMap": ["Map<K, V>", "Serializable", "Cloneable", "Object"],
        "Optional": ["Object"],
        "Record": ["Object"],
        "Enum": ["Comparable", "Serializable", "Object"],
        "Comparable": ["Object"],
        "Serializable": ["Object"],
        "Cloneable": ["Object"],
        "Runnable": ["Object"],
        "Callable": ["Object"],
        "Comparator": ["Object"],
        "Function": ["Object"],
        "BiFunction": ["Object"],
        "Consumer": ["Object"],
        "BiConsumer": ["Object"],
        "Supplier": ["Object"],
        "Predicate": ["Object"],
        "BiPredicate": ["Object"],
        "UnaryOperator": ["Function", "Object"],
        "BinaryOperator": ["BiFunction", "Object"],
        "IntFunction": ["Object"],
        "ToIntFunction": ["Object"],
        "IntUnaryOperator": ["Object"],
        "IntBinaryOperator": ["Object"],
        "IntPredicate": ["Object"],
        "IntConsumer": ["Object"],
        "IntSupplier": ["Object"],
        "Stream": ["Object"],
        "AutoCloseable": ["Object"],
        "java.lang.AutoCloseable": ["Object"],
        "Closeable": ["AutoCloseable", "Object"],
        "java.io.Closeable": ["AutoCloseable", "Object"],
        "PrintStream": ["OutputStream", "Closeable", "AutoCloseable", "Object"],
        "InputStream": ["Closeable", "AutoCloseable", "Object"],
        "java.io.InputStream": ["Closeable", "AutoCloseable", "Object"],
        "OutputStream": ["Closeable", "AutoCloseable", "Object"],
        "java.io.OutputStream": ["Closeable", "AutoCloseable", "Object"],
        "FileInputStream": ["InputStream", "Closeable", "AutoCloseable", "Object"],
        "java.io.FileInputStream": ["InputStream", "Closeable", "AutoCloseable", "Object"],
        "FileOutputStream": ["OutputStream", "Closeable", "AutoCloseable", "Object"],
        "java.io.FileOutputStream": ["OutputStream", "Closeable", "AutoCloseable", "Object"],
        "Reader": ["Closeable", "AutoCloseable", "Object"],
        "java.io.Reader": ["Closeable", "AutoCloseable", "Object"],
        "InputStreamReader": ["Reader", "Closeable", "AutoCloseable", "Object"],
        "java.io.InputStreamReader": ["Reader", "Closeable", "AutoCloseable", "Object"],
        "FileReader": ["InputStreamReader", "Reader", "Closeable", "AutoCloseable", "Object"],
        "java.io.FileReader": ["InputStreamReader", "Reader", "Closeable", "AutoCloseable", "Object"],
        "BufferedReader": ["Reader", "Closeable", "AutoCloseable", "Object"],
        "java.io.BufferedReader": ["Reader", "Closeable", "AutoCloseable", "Object"],
        "Writer": ["Closeable", "AutoCloseable", "Appendable", "Object"],
        "java.io.Writer": ["Closeable", "AutoCloseable", "Appendable", "Object"],
        "FileWriter": ["Writer", "Closeable", "AutoCloseable", "Appendable", "Object"],
        "java.io.FileWriter": ["Writer", "Closeable", "AutoCloseable", "Appendable", "Object"],
        "File": ["Serializable", "Comparable<File>", "Object"],
        "java.io.File": ["Serializable", "Comparable<File>", "Object"],
        "Thread": ["Runnable", "Object"],
        "java.lang.Thread": ["Runnable", "Object"],
        "Class": ["Serializable", "Object"],
        "java.lang.Class": ["Serializable", "Object"],
        "System": ["Object"],
        "Math": ["Object"],
        "Collections": ["Object"],
        "Arrays": ["Object"],
        "java.util.Arrays": ["Object"],
        "Objects": ["Object"],
        "Throwable": ["Serializable", "Object"],
    }
    TYPE_SYMBOL_CATEGORIES = frozenset({
        "tipo", "classe", "interface", "enum", "record", "annotation_interface",
    })
    BUILTIN_FINAL_TYPES = frozenset({
        "String", "Integer", "Long", "Double", "Float", "Byte", "Short", "Boolean", "Character", "Void",
    })
    BUILTIN_INTERFACE_TYPES = frozenset({
        "CharSequence", "Appendable", "Iterable", "Iterator", "ListIterator",
        "Collection", "List", "Set", "Map", "AutoCloseable", "Closeable",
        "Comparable", "Serializable", "Cloneable", "Runnable", "Callable", "Comparator",
        "Function", "BiFunction", "Consumer", "BiConsumer", "Supplier", "Predicate",
        "BiPredicate", "UnaryOperator", "BinaryOperator", "IntFunction", "ToIntFunction",
        "IntUnaryOperator", "IntBinaryOperator", "IntPredicate", "IntConsumer", "IntSupplier",
        "Stream", "java.util.List", "java.util.Collection",
        "java.lang.AutoCloseable", "java.io.Closeable",
    })
    BUILTIN_CLASS_TYPES = frozenset({
        "Object", "String", "StringBuilder", "StringBuffer", "Number",
        "Integer", "Long", "Double", "Float", "Byte", "Short", "Boolean",
        "Character", "Void", "ArrayList", "LinkedList", "HashSet", "HashMap",
        "Optional", "Record", "Enum", "Throwable", "Exception",
        "RuntimeException", "Error", "PrintStream", "InputStream", "OutputStream",
        "FileInputStream", "FileOutputStream", "Reader", "InputStreamReader",
        "FileReader", "BufferedReader", "Writer", "FileWriter", "File",
        "Thread", "Class",
        "java.io.InputStream", "java.io.OutputStream", "java.io.FileInputStream",
        "java.io.FileOutputStream", "java.io.Reader", "java.io.InputStreamReader",
        "java.io.FileReader", "java.io.BufferedReader", "java.io.Writer",
        "java.io.FileWriter", "java.io.File", "java.lang.Thread", "java.lang.Class",
        "System", "Math", "Collections", "Arrays", "Objects",
        "java.util.Arrays", "java.util.ArrayList",
    })
    PRIMITIVE_TO_WRAPPER = {
        "byte": "Byte",
        "short": "Short",
        "char": "Character",
        "int": "Integer",
        "long": "Long",
        "float": "Float",
        "double": "Double",
        "boolean": "Boolean",
    }
    INTEGRAL_PRIMITIVES = frozenset({"byte", "short", "char", "int", "long"})
    INTEGER_RANGES = {
        "byte": (-128, 127),
        "short": (-32768, 32767),
        "char": (0, 65535),
    }
    WIDENING_PRIMITIVE_TARGETS = {
        "byte": frozenset({"short", "int", "long", "float", "double"}),
        "short": frozenset({"int", "long", "float", "double"}),
        "char": frozenset({"int", "long", "float", "double"}),
        "int": frozenset({"long", "float", "double"}),
        "long": frozenset({"float", "double"}),
        "float": frozenset({"double"}),
    }
    BUILTIN_TYPE_PARAMS = {
        "List": ["E"],
        "java.util.List": ["E"],
        "ArrayList": ["E"],
        "java.util.ArrayList": ["E"],
        "LinkedList": ["E"],
        "java.util.LinkedList": ["E"],
        "Set": ["E"],
        "java.util.Set": ["E"],
        "HashSet": ["E"],
        "java.util.HashSet": ["E"],
        "Collection": ["E"],
        "java.util.Collection": ["E"],
        "Iterable": ["T"],
        "Iterator": ["E"],
        "ListIterator": ["E"],
        "Optional": ["T"],
        "java.util.Optional": ["T"],
        "Stream": ["T"],
        "Map": ["K", "V"],
        "java.util.Map": ["K", "V"],
        "HashMap": ["K", "V"],
        "java.util.HashMap": ["K", "V"],
        "Class": ["T"],
        "java.lang.Class": ["T"],
        "Enum": ["E"],
        "java.lang.Enum": ["E"],
        "Comparable": ["T"],
        "Comparator": ["T"],
        "Function": ["T", "R"],
        "BiFunction": ["T", "U", "R"],
        "Consumer": ["T"],
        "BiConsumer": ["T", "U"],
        "Supplier": ["T"],
        "Predicate": ["T"],
        "BiPredicate": ["T", "U"],
        "UnaryOperator": ["T"],
        "BinaryOperator": ["T"],
        "IntFunction": ["R"],
        "ToIntFunction": ["T"],
        "Callable": ["V"],
    }
    # Mapa: nome_interface -> (param_types, return_type, type_params)
    BUILTIN_FUNCTIONAL_INTERFACES = {
        "Runnable": ([], "void", []),
        "Callable": ([], "V", ["V"]),
        "Comparable": (["T"], "int", ["T"]),
        "Comparator": (["T", "T"], "int", ["T"]),
        "Function": (["T"], "R", ["T", "R"]),
        "BiFunction": (["T", "U"], "R", ["T", "U", "R"]),
        "Consumer": (["T"], "void", ["T"]),
        "BiConsumer": (["T", "U"], "void", ["T", "U"]),
        "Supplier": ([], "T", ["T"]),
        "Predicate": (["T"], "boolean", ["T"]),
        "BiPredicate": (["T", "U"], "boolean", ["T", "U"]),
        "UnaryOperator": (["T"], "T", ["T"]),
        "BinaryOperator": (["T", "T"], "T", ["T"]),
        "IntFunction": (["int"], "R", ["R"]),
        "ToIntFunction": (["T"], "int", ["T"]),
        "IntUnaryOperator": (["int"], "int", []),
        "IntBinaryOperator": (["int", "int"], "int", []),
        "IntPredicate": (["int"], "boolean", []),
        "IntConsumer": (["int"], "void", []),
        "IntSupplier": ([], "int", []),
    }
    # Mapa: tipo -> {campo: (tipo_campo, is_static, is_final)}
    BUILTIN_FIELDS = {
        "System": {
            "out": ("PrintStream", True, True),
            "err": ("PrintStream", True, True),
            "in": ("InputStream", True, True),
        },
        "Math": {
            "PI": ("double", True, True),
            "E": ("double", True, True),
        },
        "Byte": {
            "MAX_VALUE": ("byte", True, True),
            "MIN_VALUE": ("byte", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
        "Short": {
            "MAX_VALUE": ("short", True, True),
            "MIN_VALUE": ("short", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
        "Character": {
            "MAX_VALUE": ("char", True, True),
            "MIN_VALUE": ("char", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
        "Integer": {
            "MAX_VALUE": ("int", True, True),
            "MIN_VALUE": ("int", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
        "Long": {
            "MAX_VALUE": ("long", True, True),
            "MIN_VALUE": ("long", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
        "Float": {
            "MAX_VALUE": ("float", True, True),
            "MIN_VALUE": ("float", True, True),
            "POSITIVE_INFINITY": ("float", True, True),
            "NEGATIVE_INFINITY": ("float", True, True),
            "NaN": ("float", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
        "Double": {
            "MAX_VALUE": ("double", True, True),
            "MIN_VALUE": ("double", True, True),
            "POSITIVE_INFINITY": ("double", True, True),
            "NEGATIVE_INFINITY": ("double", True, True),
            "NaN": ("double", True, True),
            "SIZE": ("int", True, True),
            "BYTES": ("int", True, True),
        },
    }
    BUILTIN_CONSTANT_VALUES = {
        "Byte": {"MAX_VALUE": ("byte", 127), "MIN_VALUE": ("byte", -128), "SIZE": ("int", 8), "BYTES": ("int", 1)},
        "Short": {"MAX_VALUE": ("short", 32767), "MIN_VALUE": ("short", -32768), "SIZE": ("int", 16), "BYTES": ("int", 2)},
        "Character": {"MAX_VALUE": ("char", 65535), "MIN_VALUE": ("char", 0), "SIZE": ("int", 16), "BYTES": ("int", 2)},
        "Integer": {"MAX_VALUE": ("int", 2147483647), "MIN_VALUE": ("int", -2147483648), "SIZE": ("int", 32), "BYTES": ("int", 4)},
        "Long": {"MAX_VALUE": ("long", 9223372036854775807), "MIN_VALUE": ("long", -9223372036854775808), "SIZE": ("int", 64), "BYTES": ("int", 8)},
        "Float": {
            "MAX_VALUE": ("float", 3.4028235e38),
            "MIN_VALUE": ("float", 1.4e-45),
            "POSITIVE_INFINITY": ("float", float("inf")),
            "NEGATIVE_INFINITY": ("float", float("-inf")),
            "NaN": ("float", float("nan")),
            "SIZE": ("int", 32),
            "BYTES": ("int", 4),
        },
        "Double": {
            "MAX_VALUE": ("double", 1.7976931348623157e308),
            "MIN_VALUE": ("double", 4.9e-324),
            "POSITIVE_INFINITY": ("double", float("inf")),
            "NEGATIVE_INFINITY": ("double", float("-inf")),
            "NaN": ("double", float("nan")),
            "SIZE": ("int", 64),
            "BYTES": ("int", 8),
        },
        "Math": {"PI": ("double", math.pi), "E": ("double", math.e)},
    }
    # Assinaturas embutidas: tipo -> nome_metodo -> lista de dicts {params, ret, static, varargs, tparams}
    BUILTIN_METHODS = {
        "Object": {
            "toString": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": [], "access": "public"}],
            "equals": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": [], "access": "public"}],
            "hashCode": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": [], "access": "public"}],
            "getClass": [{"params": [], "ret": "Class", "static": False, "varargs": False, "tparams": [], "access": "public", "is_final": True}],
            "clone": [{"params": [], "ret": "Object", "static": False, "varargs": False, "tparams": [], "access": "protected", "throws": ["CloneNotSupportedException"]}],
            "finalize": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "access": "protected", "throws": ["Throwable"]}],
            "notify": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "access": "public", "is_final": True}],
            "notifyAll": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "access": "public", "is_final": True}],
            "wait": [
                {"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "access": "public", "is_final": True, "throws": ["InterruptedException"]},
                {"params": ["long"], "ret": "void", "static": False, "varargs": False, "tparams": [], "access": "public", "is_final": True, "throws": ["InterruptedException"]},
            ],
        },
        "CharSequence": {
            "length": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "charAt": [{"params": ["int"], "ret": "char", "static": False, "varargs": False, "tparams": []}],
            "isEmpty": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "subSequence": [{"params": ["int", "int"], "ret": "CharSequence", "static": False, "varargs": False, "tparams": []}],
        },
        "String": {
            "length": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "isEmpty": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "isBlank": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "charAt": [{"params": ["int"], "ret": "char", "static": False, "varargs": False, "tparams": []}],
            "substring": [
                {"params": ["int"], "ret": "String", "static": False, "varargs": False, "tparams": []},
                {"params": ["int", "int"], "ret": "String", "static": False, "varargs": False, "tparams": []},
            ],
            "toUpperCase": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "toLowerCase": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "trim": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "strip": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "contains": [{"params": ["CharSequence"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "startsWith": [{"params": ["String"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "endsWith": [{"params": ["String"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "equalsIgnoreCase": [{"params": ["String"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "compareTo": [{"params": ["String"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "indexOf": [
                {"params": ["int"], "ret": "int", "static": False, "varargs": False, "tparams": []},
                {"params": ["String"], "ret": "int", "static": False, "varargs": False, "tparams": []},
            ],
            "lastIndexOf": [
                {"params": ["int"], "ret": "int", "static": False, "varargs": False, "tparams": []},
                {"params": ["String"], "ret": "int", "static": False, "varargs": False, "tparams": []},
            ],
            "replace": [{"params": ["CharSequence", "CharSequence"], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "split": [{"params": ["String"], "ret": "String[]", "static": False, "varargs": False, "tparams": []}],
            "concat": [{"params": ["String"], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "formatted": [{"params": ["Object..."], "ret": "String", "static": False, "varargs": True, "tparams": []}],
            "toCharArray": [{"params": [], "ret": "char[]", "static": False, "varargs": False, "tparams": []}],
            "valueOf": [
                {"params": ["int"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["long"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["double"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["boolean"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["char"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["Object"], "ret": "String", "static": True, "varargs": False, "tparams": []},
            ],
            "format": [{"params": ["String", "Object..."], "ret": "String", "static": True, "varargs": True, "tparams": []}],
            "join": [{"params": ["CharSequence", "CharSequence..."], "ret": "String", "static": True, "varargs": True, "tparams": []}],
        },
        "StringBuilder": {
            "append": [
                {"params": ["String"], "ret": "StringBuilder", "static": False, "varargs": False, "tparams": []},
                {"params": ["int"], "ret": "StringBuilder", "static": False, "varargs": False, "tparams": []},
                {"params": ["double"], "ret": "StringBuilder", "static": False, "varargs": False, "tparams": []},
                {"params": ["char"], "ret": "StringBuilder", "static": False, "varargs": False, "tparams": []},
                {"params": ["Object"], "ret": "StringBuilder", "static": False, "varargs": False, "tparams": []},
            ],
            "length": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
        },
        "StringBuffer": {
            "append": [
                {"params": ["String"], "ret": "StringBuffer", "static": False, "varargs": False, "tparams": []},
                {"params": ["Object"], "ret": "StringBuffer", "static": False, "varargs": False, "tparams": []},
            ],
            "length": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
        },
        "Math": {
            "max": [
                {"params": ["int", "int"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["long", "long"], "ret": "long", "static": True, "varargs": False, "tparams": []},
                {"params": ["float", "float"], "ret": "float", "static": True, "varargs": False, "tparams": []},
                {"params": ["double", "double"], "ret": "double", "static": True, "varargs": False, "tparams": []},
            ],
            "min": [
                {"params": ["int", "int"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["long", "long"], "ret": "long", "static": True, "varargs": False, "tparams": []},
                {"params": ["float", "float"], "ret": "float", "static": True, "varargs": False, "tparams": []},
                {"params": ["double", "double"], "ret": "double", "static": True, "varargs": False, "tparams": []},
            ],
            "abs": [
                {"params": ["int"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["long"], "ret": "long", "static": True, "varargs": False, "tparams": []},
                {"params": ["float"], "ret": "float", "static": True, "varargs": False, "tparams": []},
                {"params": ["double"], "ret": "double", "static": True, "varargs": False, "tparams": []},
            ],
            "sqrt": [{"params": ["double"], "ret": "double", "static": True, "varargs": False, "tparams": []}],
            "pow": [{"params": ["double", "double"], "ret": "double", "static": True, "varargs": False, "tparams": []}],
            "round": [
                {"params": ["double"], "ret": "long", "static": True, "varargs": False, "tparams": []},
                {"params": ["float"], "ret": "int", "static": True, "varargs": False, "tparams": []},
            ],
        },
        "PrintStream": {
            "println": [
                {"params": [], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["boolean"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["char"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["int"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["long"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["double"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["String"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["Object"], "ret": "void", "static": False, "varargs": False, "tparams": []},
            ],
            "print": [
                {"params": ["int"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["String"], "ret": "void", "static": False, "varargs": False, "tparams": []},
                {"params": ["Object"], "ret": "void", "static": False, "varargs": False, "tparams": []},
            ],
            "printf": [{"params": ["String", "Object..."], "ret": "PrintStream", "static": False, "varargs": True, "tparams": []}],
        },
        "Integer": {
            "parseInt": [{"params": ["String"], "ret": "int", "static": True, "varargs": False, "tparams": []}],
            "valueOf": [
                {"params": ["int"], "ret": "Integer", "static": True, "varargs": False, "tparams": []},
                {"params": ["String"], "ret": "Integer", "static": True, "varargs": False, "tparams": []},
            ],
            "intValue": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "doubleValue": [{"params": [], "ret": "double", "static": False, "varargs": False, "tparams": []}],
            "compareTo": [{"params": ["Integer"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "compare": [{"params": ["int", "int"], "ret": "int", "static": True, "varargs": False, "tparams": []}],
        },
        "Long": {
            "parseLong": [{"params": ["String"], "ret": "long", "static": True, "varargs": False, "tparams": []}],
            "valueOf": [{"params": ["long"], "ret": "Long", "static": True, "varargs": False, "tparams": []}],
            "longValue": [{"params": [], "ret": "long", "static": False, "varargs": False, "tparams": []}],
        },
        "Double": {
            "parseDouble": [{"params": ["String"], "ret": "double", "static": True, "varargs": False, "tparams": []}],
            "valueOf": [{"params": ["double"], "ret": "Double", "static": True, "varargs": False, "tparams": []}],
            "doubleValue": [{"params": [], "ret": "double", "static": False, "varargs": False, "tparams": []}],
            "intValue": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
        },
        "Boolean": {
            "parseBoolean": [{"params": ["String"], "ret": "boolean", "static": True, "varargs": False, "tparams": []}],
            "valueOf": [{"params": ["boolean"], "ret": "Boolean", "static": True, "varargs": False, "tparams": []}],
            "booleanValue": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
        },
        "Number": {
            "intValue": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "longValue": [{"params": [], "ret": "long", "static": False, "varargs": False, "tparams": []}],
            "floatValue": [{"params": [], "ret": "float", "static": False, "varargs": False, "tparams": []}],
            "doubleValue": [{"params": [], "ret": "double", "static": False, "varargs": False, "tparams": []}],
            "byteValue": [{"params": [], "ret": "byte", "static": False, "varargs": False, "tparams": []}],
            "shortValue": [{"params": [], "ret": "short", "static": False, "varargs": False, "tparams": []}],
        },
        "Iterator": {
            "hasNext": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "next": [{"params": [], "ret": "E", "static": False, "varargs": False, "tparams": []}],
            "remove": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "is_default": True}],
        },
        "ListIterator": {
            "hasNext": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "next": [{"params": [], "ret": "E", "static": False, "varargs": False, "tparams": []}],
            "hasPrevious": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "previous": [{"params": [], "ret": "E", "static": False, "varargs": False, "tparams": []}],
            "add": [{"params": ["E"], "ret": "void", "static": False, "varargs": False, "tparams": []}],
            "set": [{"params": ["E"], "ret": "void", "static": False, "varargs": False, "tparams": []}],
            "remove": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "is_default": True}],
        },
        "Collection": {
            "size": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "isEmpty": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "contains": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "iterator": [{"params": [], "ret": "Iterator<E>", "static": False, "varargs": False, "tparams": []}],
            "add": [{"params": ["E"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "addAll": [{"params": ["Collection<? extends E>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "containsAll": [{"params": ["Collection<?>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "remove": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "removeAll": [{"params": ["Collection<?>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "retainAll": [{"params": ["Collection<?>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "clear": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": []}],
            "stream": [{"params": [], "ret": "Stream<E>", "static": False, "varargs": False, "tparams": [], "is_default": True}],
        },
        "List": {
            "size": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "isEmpty": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "contains": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "iterator": [{"params": [], "ret": "Iterator<E>", "static": False, "varargs": False, "tparams": []}],
            "toArray": [
                {"params": [], "ret": "Object[]", "static": False, "varargs": False, "tparams": []},
                {"params": ["T[]"], "ret": "T[]", "static": False, "varargs": False, "tparams": ["T"]},
            ],
            "get": [{"params": ["int"], "ret": "E", "static": False, "varargs": False, "tparams": []}],
            "set": [{"params": ["int", "E"], "ret": "E", "static": False, "varargs": False, "tparams": []}],
            "add": [
                {"params": ["E"], "ret": "boolean", "static": False, "varargs": False, "tparams": []},
                {"params": ["int", "E"], "ret": "void", "static": False, "varargs": False, "tparams": []},
            ],
            "remove": [
                {"params": ["int"], "ret": "E", "static": False, "varargs": False, "tparams": []},
                {"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []},
            ],
            "containsAll": [{"params": ["Collection<?>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "addAll": [
                {"params": ["Collection<? extends E>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []},
                {"params": ["int", "Collection<? extends E>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []},
            ],
            "removeAll": [{"params": ["Collection<?>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "retainAll": [{"params": ["Collection<?>"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "clear": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": []}],
            "equals": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "hashCode": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "indexOf": [{"params": ["Object"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "lastIndexOf": [{"params": ["Object"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "listIterator": [
                {"params": [], "ret": "ListIterator<E>", "static": False, "varargs": False, "tparams": []},
                {"params": ["int"], "ret": "ListIterator<E>", "static": False, "varargs": False, "tparams": []},
            ],
            "subList": [{"params": ["int", "int"], "ret": "List<E>", "static": False, "varargs": False, "tparams": []}],
            "sort": [{"params": ["Comparator"], "ret": "void", "static": False, "varargs": False, "tparams": [], "is_default": True}],
            "stream": [{"params": [], "ret": "Stream<E>", "static": False, "varargs": False, "tparams": [], "is_default": True}],
            "of": [
                {"params": [], "ret": "List<E>", "static": True, "varargs": False, "tparams": ["E"]},
                {"params": ["E"], "ret": "List<E>", "static": True, "varargs": False, "tparams": ["E"]},
                {"params": ["E", "E"], "ret": "List<E>", "static": True, "varargs": False, "tparams": ["E"]},
                {"params": ["E..."], "ret": "List<E>", "static": True, "varargs": True, "tparams": ["E"]},
            ],
            "copyOf": [{"params": ["Collection<? extends E>"], "ret": "List<E>", "static": True, "varargs": False, "tparams": ["E"]}],
        },
        "Set": {
            "of": [
                {"params": [], "ret": "Set<E>", "static": True, "varargs": False, "tparams": ["E"]},
                {"params": ["E..."], "ret": "Set<E>", "static": True, "varargs": True, "tparams": ["E"]},
            ],
        },
        "Map": {
            "get": [{"params": ["Object"], "ret": "V", "static": False, "varargs": False, "tparams": []}],
            "put": [{"params": ["K", "V"], "ret": "V", "static": False, "varargs": False, "tparams": []}],
            "putAll": [{"params": ["Map<? extends K, ? extends V>"], "ret": "void", "static": False, "varargs": False, "tparams": []}],
            "containsKey": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "containsValue": [{"params": ["Object"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "size": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": []}],
            "isEmpty": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "keySet": [{"params": [], "ret": "Set<K>", "static": False, "varargs": False, "tparams": []}],
            "values": [{"params": [], "ret": "Collection<V>", "static": False, "varargs": False, "tparams": []}],
        },
        "Optional": {
            "get": [{"params": [], "ret": "T", "static": False, "varargs": False, "tparams": []}],
            "isPresent": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "isEmpty": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "orElse": [{"params": ["T"], "ret": "T", "static": False, "varargs": False, "tparams": []}],
            "of": [{"params": ["T"], "ret": "Optional<T>", "static": True, "varargs": False, "tparams": ["T"]}],
            "ofNullable": [{"params": ["T"], "ret": "Optional<T>", "static": True, "varargs": False, "tparams": ["T"]}],
            "empty": [{"params": [], "ret": "Optional<T>", "static": True, "varargs": False, "tparams": ["T"]}],
        },
        "Collections": {
            "emptyList": [{"params": [], "ret": "List<T>", "static": True, "varargs": False, "tparams": ["T"]}],
            "singletonList": [{"params": ["T"], "ret": "List<T>", "static": True, "varargs": False, "tparams": ["T"]}],
            "sort": [{"params": ["List<T>"], "ret": "void", "static": True, "varargs": False, "tparams": ["T"]}],
            "copy": [{"params": ["List<? super T>", "List<? extends T>"], "ret": "void", "static": True, "varargs": False, "tparams": ["T"]}],
        },
        "Arrays": {
            "asList": [{"params": ["T..."], "ret": "List<T>", "static": True, "varargs": True, "tparams": ["T"]}],
            "sort": [
                {"params": ["int[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["float[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["char[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["byte[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["short[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["Object[]"], "ret": "void", "static": True, "varargs": False, "tparams": []},
            ],
            "binarySearch": [
                {"params": ["int[]", "int"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]", "long"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]", "double"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["float[]", "float"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["char[]", "char"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["byte[]", "byte"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["short[]", "short"], "ret": "int", "static": True, "varargs": False, "tparams": []},
                {"params": ["Object[]", "Object"], "ret": "int", "static": True, "varargs": False, "tparams": []},
            ],
            "equals": [
                {"params": ["boolean[]", "boolean[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["byte[]", "byte[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["char[]", "char[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["short[]", "short[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["int[]", "int[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]", "long[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["float[]", "float[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]", "double[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
                {"params": ["Object[]", "Object[]"], "ret": "boolean", "static": True, "varargs": False, "tparams": []},
            ],
            "fill": [
                {"params": ["int[]", "int"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]", "long"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]", "double"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["float[]", "float"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["char[]", "char"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["byte[]", "byte"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["short[]", "short"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["boolean[]", "boolean"], "ret": "void", "static": True, "varargs": False, "tparams": []},
                {"params": ["Object[]", "Object"], "ret": "void", "static": True, "varargs": False, "tparams": []},
            ],
            "copyOf": [
                {"params": ["T[]", "int"], "ret": "T[]", "static": True, "varargs": False, "tparams": ["T"]},
                {"params": ["boolean[]", "int"], "ret": "boolean[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["byte[]", "int"], "ret": "byte[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["char[]", "int"], "ret": "char[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["short[]", "int"], "ret": "short[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["int[]", "int"], "ret": "int[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]", "int"], "ret": "long[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["float[]", "int"], "ret": "float[]", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]", "int"], "ret": "double[]", "static": True, "varargs": False, "tparams": []},
            ],
            "stream": [
                {"params": ["T[]"], "ret": "Stream<T>", "static": True, "varargs": False, "tparams": ["T"]},
                {"params": ["int[]"], "ret": "IntStream", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]"], "ret": "LongStream", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]"], "ret": "DoubleStream", "static": True, "varargs": False, "tparams": []},
            ],
            "deepToString": [
                {"params": ["Object[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
            ],
            "toString": [
                {"params": ["boolean[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["byte[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["char[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["short[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["int[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["long[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["float[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["double[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
                {"params": ["Object[]"], "ret": "String", "static": True, "varargs": False, "tparams": []},
            ],
        },
        "Objects": {
            "requireNonNull": [{"params": ["T"], "ret": "T", "static": True, "varargs": False, "tparams": ["T"]}],
            "equals": [{"params": ["Object", "Object"], "ret": "boolean", "static": True, "varargs": False, "tparams": []}],
        },
        "Function": {
            "apply": [{"params": ["T"], "ret": "R", "static": False, "varargs": False, "tparams": []}],
        },
        "BiFunction": {
            "apply": [{"params": ["T", "U"], "ret": "R", "static": False, "varargs": False, "tparams": []}],
        },
        "Consumer": {
            "accept": [{"params": ["T"], "ret": "void", "static": False, "varargs": False, "tparams": []}],
        },
        "BiConsumer": {
            "accept": [{"params": ["T", "U"], "ret": "void", "static": False, "varargs": False, "tparams": []}],
        },
        "Supplier": {
            "get": [{"params": [], "ret": "T", "static": False, "varargs": False, "tparams": []}],
        },
        "Predicate": {
            "test": [{"params": ["T"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
        },
        "BiPredicate": {
            "test": [{"params": ["T", "U"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
        },
        "UnaryOperator": {
            "apply": [{"params": ["T"], "ret": "T", "static": False, "varargs": False, "tparams": []}],
        },
        "BinaryOperator": {
            "apply": [{"params": ["T", "T"], "ret": "T", "static": False, "varargs": False, "tparams": []}],
        },
        "Callable": {
            "call": [{"params": [], "ret": "V", "static": False, "varargs": False, "tparams": [], "throws": ["Exception"]}],
        },
        "Runnable": {
            "run": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": []}],
        },
        "Comparator": {
            "compare": [{"params": ["T", "T"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
        },
        "IntUnaryOperator": {
            "applyAsInt": [{"params": ["int"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
        },
        "IntBinaryOperator": {
            "applyAsInt": [{"params": ["int", "int"], "ret": "int", "static": False, "varargs": False, "tparams": []}],
        },
        "IntPredicate": {
            "test": [{"params": ["int"], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
        },
        "Throwable": {
            "getMessage": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "getCause": [{"params": [], "ret": "Throwable", "static": False, "varargs": False, "tparams": []}],
            "printStackTrace": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": []}],
        },
        "AutoCloseable": {
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["Exception"]}],
        },
        "Closeable": {
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
        },
        "InputStream": {
            "read": [
                {"params": [], "ret": "int", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
                {"params": ["byte[]"], "ret": "int", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
            ],
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
        },
        "OutputStream": {
            "write": [
                {"params": ["int"], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
                {"params": ["byte[]"], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
            ],
            "flush": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
        },
        "Reader": {
            "read": [
                {"params": [], "ret": "int", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
                {"params": ["char[]"], "ret": "int", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
            ],
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
        },
        "BufferedReader": {
            "readLine": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
            "read": [{"params": [], "ret": "int", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
        },
        "Writer": {
            "write": [
                {"params": ["String"], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
                {"params": ["int"], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]},
            ],
            "flush": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
            "close": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
        },
        "File": {
            "createNewFile": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": [], "throws": ["IOException"]}],
            "exists": [{"params": [], "ret": "boolean", "static": False, "varargs": False, "tparams": []}],
            "getName": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
            "getPath": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
        },
        "Thread": {
            "sleep": [{"params": ["long"], "ret": "void", "static": True, "varargs": False, "tparams": [], "throws": ["InterruptedException"]}],
            "start": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": []}],
            "join": [{"params": [], "ret": "void", "static": False, "varargs": False, "tparams": [], "throws": ["InterruptedException"]}],
        },
        "Class": {
            "forName": [{"params": ["String"], "ret": "Class", "static": True, "varargs": False, "tparams": [], "throws": ["ClassNotFoundException"]}],
            "getName": [{"params": [], "ret": "String", "static": False, "varargs": False, "tparams": []}],
        },
    }
    BUILTIN_METHODS["java.util.List"] = BUILTIN_METHODS["List"]
    BUILTIN_METHODS["ArrayList"] = BUILTIN_METHODS["List"]
    BUILTIN_METHODS["java.util.ArrayList"] = BUILTIN_METHODS["List"]
    BUILTIN_METHODS["java.util.Collection"] = BUILTIN_METHODS["Collection"]
    BUILTIN_METHODS["java.util.Arrays"] = BUILTIN_METHODS["Arrays"]
    BUILTIN_METHODS["java.lang.AutoCloseable"] = BUILTIN_METHODS["AutoCloseable"]
    BUILTIN_METHODS["java.io.Closeable"] = BUILTIN_METHODS["Closeable"]
    BUILTIN_METHODS["java.io.InputStream"] = BUILTIN_METHODS["InputStream"]
    BUILTIN_METHODS["java.io.OutputStream"] = BUILTIN_METHODS["OutputStream"]
    BUILTIN_METHODS["java.io.Reader"] = BUILTIN_METHODS["Reader"]
    BUILTIN_METHODS["java.io.BufferedReader"] = BUILTIN_METHODS["BufferedReader"]
    BUILTIN_METHODS["java.io.Writer"] = BUILTIN_METHODS["Writer"]
    BUILTIN_METHODS["java.io.File"] = BUILTIN_METHODS["File"]
    BUILTIN_METHODS["java.lang.Thread"] = BUILTIN_METHODS["Thread"]
    BUILTIN_METHODS["java.lang.Class"] = BUILTIN_METHODS["Class"]

    BUILTIN_CONSTRUCTORS = {
        "Object": [[]],
        "String": [[], ["String"], ["char[]"]],
        "StringBuilder": [[], ["int"], ["String"]],
        "StringBuffer": [[], ["int"], ["String"]],
        "ArrayList": [[], ["int"], ["Collection"]],
        "java.util.ArrayList": [[], ["int"], ["Collection"]],
        "LinkedList": [[], ["Collection"]],
        "java.util.LinkedList": [[], ["Collection"]],
        "HashSet": [[], ["int"], ["Collection"]],
        "java.util.HashSet": [[], ["int"], ["Collection"]],
        "HashMap": [[], ["int"], ["Map"]],
        "java.util.HashMap": [[], ["int"], ["Map"]],
        "Exception": [[], ["String"], ["Throwable"], ["String", "Throwable"]],
        "RuntimeException": [[], ["String"], ["Throwable"], ["String", "Throwable"]],
        "IllegalArgumentException": [[], ["String"]],
        "IllegalStateException": [[], ["String"]],
        "IOException": [[], ["String"], ["Throwable"], ["String", "Throwable"]],
        "FileNotFoundException": [[], ["String"]],
        "SQLException": [[], ["String"]],
        "Thread": [[], ["Runnable"]],
        "File": [["String"]],
        "java.io.File": [["String"]],
        "InputStreamReader": [{"params": ["InputStream"], "throws": []}],
        "java.io.InputStreamReader": [{"params": ["InputStream"], "throws": []}],
        "FileReader": [
            {"params": ["String"], "throws": ["FileNotFoundException"]},
            {"params": ["File"], "throws": ["FileNotFoundException"]},
        ],
        "java.io.FileReader": [
            {"params": ["String"], "throws": ["FileNotFoundException"]},
            {"params": ["File"], "throws": ["FileNotFoundException"]},
        ],
        "BufferedReader": [{"params": ["Reader"], "throws": []}],
        "java.io.BufferedReader": [{"params": ["Reader"], "throws": []}],
        "FileInputStream": [
            {"params": ["String"], "throws": ["FileNotFoundException"]},
            {"params": ["File"], "throws": ["FileNotFoundException"]},
        ],
        "java.io.FileInputStream": [
            {"params": ["String"], "throws": ["FileNotFoundException"]},
            {"params": ["File"], "throws": ["FileNotFoundException"]},
        ],
        "FileWriter": [
            {"params": ["String"], "throws": ["IOException"]},
            {"params": ["File"], "throws": ["IOException"]},
        ],
        "java.io.FileWriter": [
            {"params": ["String"], "throws": ["IOException"]},
            {"params": ["File"], "throws": ["IOException"]},
        ],
        "FileOutputStream": [
            {"params": ["String"], "throws": ["FileNotFoundException"]},
            {"params": ["File"], "throws": ["FileNotFoundException"]},
        ],
        "java.io.FileOutputStream": [
            {"params": ["String"], "throws": ["FileNotFoundException"]},
            {"params": ["File"], "throws": ["FileNotFoundException"]},
        ],
    }

    BUILTIN_COMPAT_FQNS: Dict[str, str] = {
        "Closeable": "java.io.Closeable",
        "InputStream": "java.io.InputStream",
        "OutputStream": "java.io.OutputStream",
        "FileInputStream": "java.io.FileInputStream",
        "FileOutputStream": "java.io.FileOutputStream",
        "Reader": "java.io.Reader",
        "InputStreamReader": "java.io.InputStreamReader",
        "FileReader": "java.io.FileReader",
        "BufferedReader": "java.io.BufferedReader",
        "Writer": "java.io.Writer",
        "FileWriter": "java.io.FileWriter",
        "File": "java.io.File",
        "PrintStream": "java.io.PrintStream",
        "Serializable": "java.io.Serializable",
        "IOException": "java.io.IOException",
        "FileNotFoundException": "java.io.FileNotFoundException",
        "EOFException": "java.io.EOFException",
        "Collection": "java.util.Collection",
        "List": "java.util.List",
        "ArrayList": "java.util.ArrayList",
        "LinkedList": "java.util.LinkedList",
        "Set": "java.util.Set",
        "HashSet": "java.util.HashSet",
        "Map": "java.util.Map",
        "HashMap": "java.util.HashMap",
        "Iterator": "java.util.Iterator",
        "ListIterator": "java.util.ListIterator",
        "Comparator": "java.util.Comparator",
        "Optional": "java.util.Optional",
        "Collections": "java.util.Collections",
        "Arrays": "java.util.Arrays",
        "Objects": "java.util.Objects",
        "Function": "java.util.function.Function",
        "BiFunction": "java.util.function.BiFunction",
        "Consumer": "java.util.function.Consumer",
        "BiConsumer": "java.util.function.BiConsumer",
        "Supplier": "java.util.function.Supplier",
        "Predicate": "java.util.function.Predicate",
        "BiPredicate": "java.util.function.BiPredicate",
        "UnaryOperator": "java.util.function.UnaryOperator",
        "BinaryOperator": "java.util.function.BinaryOperator",
        "Stream": "java.util.stream.Stream",
        "Collector": "java.util.stream.Collector",
        "Collectors": "java.util.stream.Collectors",
        "Callable": "java.util.concurrent.Callable",
        "Future": "java.util.concurrent.Future",
        "Target": "java.lang.annotation.Target",
        "Retention": "java.lang.annotation.Retention",
        "Repeatable": "java.lang.annotation.Repeatable",
        "Documented": "java.lang.annotation.Documented",
        "Inherited": "java.lang.annotation.Inherited",
        "ElementType": "java.lang.annotation.ElementType",
        "RetentionPolicy": "java.lang.annotation.RetentionPolicy",
        "SQLException": "java.sql.SQLException",
    }

    _JAVA_LANG_SIMPLIFY_RE = re.compile(r"(?<![.\w$])java\.lang\.([A-Z][A-Za-z0-9_$]*)(?!\.[A-Za-z0-9_$])")

    def __init__(
        self,
        symbol_table,
        enable_preview_primitive_patterns: bool = False,
        classpath: Optional[Sequence[str]] = None,
        include_stdlib: bool = True,
        max_class_major: Optional[int] = None,
    ):
        self.symbols = symbol_table
        self.enable_preview_primitive_patterns = enable_preview_primitive_patterns
        self._classpath: List[str] = list(classpath) if classpath is not None else []
        self._include_stdlib: bool = include_stdlib
        self._max_class_major: int = DEFAULT_MAX_CLASS_MAJOR if max_class_major is None else max_class_major
        self._classpath_resolver = ExternalSymbolResolver(
            classpath=self._classpath,
            include_stdlib=include_stdlib,
            max_class_major=self._max_class_major,
        )
        self._reported_classpath_diags: Set[Tuple[str, str]] = set()
        self._checked_explicit_imports: Set[str] = set()
        self._checked_module_imports: Set[str] = set()
        self._declared_modules: Dict[str, Dict[str, List[str]]] = {}
        self.errors = []
        self.unresolved_checks: List[str] = []
        self._in_early_construction_context = False
        self._in_compact_constructor = False
        self._compact_component_names: Set[str] = set()
        self._declared_types: Dict[str, Tuple[str, ASTNode]] = {}
        self._annotation_interfaces: Dict[str, AnnotationInterfaceDeclaration] = {}
        self._enums: Dict[str, EnumDeclaration] = {}
        self._static_imports: Set[str] = set()
        self._has_wildcard_static_import: bool = False
        self._validated_ann_targets: Set[int] = set()
        self._loop_depth: int = 0
        self._switch_depth: int = 0
        self._switch_expr_depth: int = 0
        self._callable_kind: str = "top_level"
        self._current_return_type: Optional[str] = None
        self._active_labels: Dict[str, Tuple[bool, int]] = {}
        self._local_var_scopes: List[Dict[str, Dict[str, Any]]] = []
        self._active_pattern_scopes: List[Dict[str, Dict[str, Any]]] = []
        self._local_type_scopes: List[Dict[str, int]] = []
        self._local_declared_type_scopes: List[Dict[str, Tuple[str, ASTNode]]] = []
        self._enclosing_type_names: List[str] = []
        self._current_type_is_local: bool = False
        self._in_static_context: bool = False
        self._anon_enclosing_blocked: bool = False
        self._static_context_local_keys: Set[str] = set()
        self._lambda_scope_floor_stack: List[int] = []
        self._pending_lambda_captures: List[Tuple[str, Dict[str, Any], int]] = []
        self._lambda_return_exprs_stack: List[List[Optional[ASTNode]]] = []
        self._inferred_types: Dict[int, str] = {}
        self._switch_yield_exprs_stack: List[List[Tuple[Optional[ASTNode], int]]] = []
        self._switch_expected_type_stack: List[Optional[str]] = []
        self._flow_da: Set[Any] = set()
        self._flow_du: Set[Any] = set()
        self._flow_reachable: bool = True
        self._flow_tracked: Dict[Any, Dict[str, Any]] = {}
        self._flow_exit_frames: List[Dict[str, Any]] = []
        self._flow_write_trackers: List[Set[Any]] = []
        self._flow_pending_labels: Set[str] = set()
        self._flow_suppress_errors: bool = False
        self._flow_blank_final_fields: Dict[str, Dict[str, Any]] = {}
        self._flow_in_delegating_ctor: bool = False
        self._const_eval_stack: Set[Tuple[str, str]] = set()
        self._capture_vars: Dict[str, Dict[str, Any]] = {}
        self._capture_counter: int = 0
        self._active_type_params: List[Dict[str, List[str]]] = []
        self._subtype_visiting: Set[Tuple[str, str]] = set()
        self._type_inference = JLS18ConstraintSolver(self)
        self._exception_analyzer = ExceptionAnalyzer(self)
        self._inheritance_analyzer = InheritanceAccessAnalyzer(self)
        self._reachability_const_bools: Dict[int, Optional[bool]] = {}

    def _save_exec_context(self) -> Dict[str, Any]:
        return {
            "early": self._in_early_construction_context,
            "compact": self._in_compact_constructor,
            "comp_names": self._compact_component_names,
            "loop": self._loop_depth,
            "switch": self._switch_depth,
            "switch_expr": self._switch_expr_depth,
            "kind": self._callable_kind,
            "ret": self._current_return_type,
            "labels": self._active_labels,
            "var_scopes": self._local_var_scopes,
            "pat_scopes": self._active_pattern_scopes,
            "type_scopes": self._local_type_scopes,
            "decl_type_scopes": self._local_declared_type_scopes,
            "local_type_flag": self._current_type_is_local,
            "in_static": self._in_static_context,
            "anon_enc_blocked": self._anon_enclosing_blocked,
            "lambda_floors": self._lambda_scope_floor_stack,
            "lambda_captures": self._pending_lambda_captures,
            "lambda_rets": self._lambda_return_exprs_stack,
            "switch_yields": self._switch_yield_exprs_stack,
            "switch_expected": self._switch_expected_type_stack,
            "flow_da": set(self._flow_da),
            "flow_du": set(self._flow_du),
            "flow_reachable": self._flow_reachable,
            "flow_tracked": dict(self._flow_tracked),
            "flow_exit_frames": self._flow_exit_frames,
            "flow_write_trackers": self._flow_write_trackers,
            "flow_pending_labels": self._flow_pending_labels,
            "flow_suppress_errors": self._flow_suppress_errors,
            "flow_blank_final_fields": self._flow_blank_final_fields,
            "flow_in_delegating_ctor": self._flow_in_delegating_ctor,
            "exc_frames": self._exception_analyzer.snapshot_frames(),
            "tparams_snapshot": list(self._active_type_params),
            "restore_flow": True,
        }

    def _restore_exec_context(self, saved: Dict[str, Any]):
        self._in_early_construction_context = saved["early"]
        self._in_compact_constructor = saved["compact"]
        self._compact_component_names = saved["comp_names"]
        self._loop_depth = saved["loop"]
        self._switch_depth = saved["switch"]
        self._switch_expr_depth = saved["switch_expr"]
        self._callable_kind = saved["kind"]
        self._current_return_type = saved["ret"]
        self._active_labels = saved["labels"]
        self._local_var_scopes = saved["var_scopes"]
        self._active_pattern_scopes = saved["pat_scopes"]
        self._local_type_scopes = saved["type_scopes"]
        self._local_declared_type_scopes = saved["decl_type_scopes"]
        self._current_type_is_local = saved["local_type_flag"]
        self._in_static_context = saved["in_static"]
        self._anon_enclosing_blocked = saved.get("anon_enc_blocked", False)
        self._lambda_scope_floor_stack = saved["lambda_floors"]
        self._pending_lambda_captures = saved["lambda_captures"]
        self._lambda_return_exprs_stack = saved["lambda_rets"]
        self._switch_yield_exprs_stack = saved["switch_yields"]
        self._switch_expected_type_stack = saved["switch_expected"]
        if "tparams_snapshot" in saved:
            self._active_type_params = list(saved["tparams_snapshot"])
        if saved.get("restore_flow", True):
            self._flow_da = saved["flow_da"]
            self._flow_du = saved["flow_du"]
            self._flow_reachable = saved["flow_reachable"]
            self._flow_tracked = saved["flow_tracked"]
            self._flow_exit_frames = saved["flow_exit_frames"]
            self._flow_write_trackers = saved["flow_write_trackers"]
            self._flow_pending_labels = saved["flow_pending_labels"]
            self._flow_suppress_errors = saved["flow_suppress_errors"]
            self._flow_blank_final_fields = saved["flow_blank_final_fields"]
            self._flow_in_delegating_ctor = saved["flow_in_delegating_ctor"]
            if "exc_frames" in saved:
                self._exception_analyzer.restore_frames(saved["exc_frames"])

    def _enter_exec_context(
        self,
        kind: str,
        return_type: Optional[str] = None,
        is_compact: bool = False,
        compact_names: Optional[Set[str]] = None,
        share_locals: bool = False,
        switch_expr_depth: int = 0,
        is_static: Optional[bool] = None,
    ) -> Dict[str, Any]:
        saved = self._save_exec_context()
        if kind == "switch_expression":
            saved["restore_flow"] = False
        self._in_early_construction_context = False
        self._in_compact_constructor = is_compact
        self._compact_component_names = compact_names if compact_names is not None else set()
        self._loop_depth = 0
        self._switch_depth = 0
        self._switch_expr_depth = switch_expr_depth
        self._callable_kind = kind
        self._current_return_type = return_type
        self._active_labels = {}
        if is_static is not None:
            self._in_static_context = is_static
        callable_roots = ("method", "constructor", "initializer", "field_initializer")
        if not share_locals:
            self._lambda_scope_floor_stack = []
            self._pending_lambda_captures = []
            self._lambda_return_exprs_stack = []
            self._switch_yield_exprs_stack = []
            self._switch_expected_type_stack = []
            self._local_var_scopes = [{}] if kind in callable_roots else []
            if not self._current_type_is_local:
                self._active_pattern_scopes = [{}] if kind in callable_roots else []
                self._local_declared_type_scopes = [{}] if kind in callable_roots else []
            else:
                self._active_pattern_scopes = list(self._active_pattern_scopes) + (
                    [{}] if kind in callable_roots else []
                )
                self._local_declared_type_scopes = list(self._local_declared_type_scopes) + (
                    [{}] if kind in callable_roots else []
                )
            self._local_type_scopes = [{}] if kind in callable_roots else []
            self._flow_da = set()
            self._flow_du = set()
            self._flow_reachable = True
            self._flow_tracked = {}
            self._flow_exit_frames = []
            self._flow_write_trackers = []
            self._flow_pending_labels = set()
            self._flow_in_delegating_ctor = False
            if kind == "type_body":
                self._flow_blank_final_fields = {}
        else:
            self._lambda_scope_floor_stack = list(self._lambda_scope_floor_stack)
            self._lambda_return_exprs_stack = list(self._lambda_return_exprs_stack)
            self._switch_yield_exprs_stack = list(self._switch_yield_exprs_stack)
            self._switch_expected_type_stack = list(self._switch_expected_type_stack)
            if kind == "lambda":
                # Lambda herda variáveis DA/tracked externas como leitura, mas tem fluxo próprio isolado
                self._flow_da = set(self._flow_da)
                self._flow_du = set(self._flow_du)
                self._flow_reachable = True
                self._flow_tracked = dict(self._flow_tracked)
                self._flow_exit_frames = []
                self._flow_write_trackers = []
                self._flow_pending_labels = set()
        return saved

    def _flow_snapshot(self) -> Tuple[Set[Any], Set[Any], bool]:
        """Captura um retrato imutável do estado atual de atribuição definitiva (DA, DU, alcançável)."""
        return (set(self._flow_da), set(self._flow_du), self._flow_reachable)

    def _flow_restore(self, snap: Tuple[Set[Any], Set[Any], bool]):
        """Restaura o estado atual de atribuição definitiva a partir de um retrato."""
        da, du, reach = snap
        self._flow_da = set(da)
        self._flow_du = set(du)
        self._flow_reachable = reach

    def _flow_unreachable(self) -> Tuple[Set[Any], Set[Any], bool]:
        """Retorna estado inalcançável (vacuamente DA e DU segundo JLS §16.1)."""
        return (set(), set(), False)

    def _flow_join_states(self, *states: Tuple[Set[Any], Set[Any], bool]) -> Tuple[Set[Any], Set[Any], bool]:
        """Une múltiplos estados de fluxo na junção de caminhos (interseção de DA e DU para caminhos alcançáveis)."""
        live = [(da, du) for da, du, reach in states if reach]
        if not live:
            return (set(), set(), False)
        res_da = set(live[0][0])
        res_du = set(live[0][1])
        for da, du in live[1:]:
            res_da &= da
            res_du &= du
        return (res_da, res_du, True)

    def _flow_cleanup_scope(self, scope_dict: Optional[Dict[str, Dict[str, Any]]]):
        """Remove variáveis de um bloco encerrado do rastreamento de fluxo para evitar colisão de IDs."""
        if not scope_dict:
            return
        for info in scope_dict.values():
            vid = ("local", id(info))
            self._flow_da.discard(vid)
            self._flow_du.discard(vid)
            self._flow_tracked.pop(vid, None)

    def _flow_record_write_id(self, vid: Any):
        """Registra uma escrita alcançável em todos os rastreadores de escrita ativos (try/finally)."""
        if not self._flow_reachable:
            return
        for tracker in self._flow_write_trackers:
            tracker.add(vid)

    def _flow_push_exit_frame(self, kind: str, labels: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Empilha quadro de desvio estruturado (loop, switch, label ou try_finally)."""
        frame: Dict[str, Any] = {
            "kind": kind,
            "labels": set(labels or ()),
            "breaks": [],
            "continues": [],
            "yields": [],
            "returns": [],
            "pending_breaks": [],
            "pending_continues": [],
            "pending_yields": [],
            "pending_returns": [],
        }
        self._flow_exit_frames.append(frame)
        return frame

    def _flow_record_yield(self):
        """Registra estado DA/DU de um 'yield' e encerra o fluxo normal subsequente."""
        if not self._flow_reachable:
            return
        snap = self._flow_snapshot()
        for frame in reversed(self._flow_exit_frames):
            if frame["kind"] == "try_finally":
                frame["pending_yields"].append(snap)
                self._flow_reachable = False
                return
            if frame["kind"] == "switch_expr":
                frame["yields"].append(snap)
                self._flow_reachable = False
                return
        self._flow_reachable = False

    def _flow_record_return(self):
        """Registra saída por 'return' (para construtores com campos final) e encerra o fluxo normal."""
        if not self._flow_reachable:
            return
        snap = self._flow_snapshot()
        for frame in reversed(self._flow_exit_frames):
            if frame["kind"] == "try_finally":
                frame["pending_returns"].append(snap)
                self._flow_reachable = False
                return
            if frame["kind"] == "callable":
                frame["returns"].append(snap)
                self._flow_reachable = False
                return
        self._flow_reachable = False

    def _flow_record_break(self, label: Optional[str]):
        """Registra estado DA/DU de um 'break' e encerra o fluxo normal subsequente."""
        if not self._flow_reachable:
            return
        snap = self._flow_snapshot()
        for frame in reversed(self._flow_exit_frames):
            fkind = frame["kind"]
            if fkind == "try_finally":
                frame["pending_breaks"].append((label, snap))
                self._flow_reachable = False
                return
            if label is not None:
                if label in frame["labels"]:
                    frame["breaks"].append(snap)
                    self._flow_reachable = False
                    return
            else:
                if fkind in ("loop", "switch"):
                    frame["breaks"].append(snap)
                    self._flow_reachable = False
                    return
        self._flow_reachable = False

    def _flow_record_continue(self, label: Optional[str]):
        """Registra estado DA/DU de um 'continue' e encerra o fluxo normal subsequente."""
        if not self._flow_reachable:
            return
        snap = self._flow_snapshot()
        for frame in reversed(self._flow_exit_frames):
            fkind = frame["kind"]
            if fkind == "try_finally":
                frame["pending_continues"].append((label, snap))
                self._flow_reachable = False
                return
            if label is not None:
                if fkind == "loop" and label in frame["labels"]:
                    frame["continues"].append(snap)
                    self._flow_reachable = False
                    return
            else:
                if fkind == "loop":
                    frame["continues"].append(snap)
                    self._flow_reachable = False
                    return
        self._flow_reachable = False

    def _flow_forward_abrupt_through_finally(
        self,
        pending_breaks: List[Tuple[Optional[str], Tuple[Set[Any], Set[Any], bool]]],
        pending_continues: List[Tuple[Optional[str], Tuple[Set[Any], Set[Any], bool]]],
        finally_da_added: Set[Any],
        finally_may_write: Set[Any],
        finally_completes: bool,
        pending_yields: Optional[List[Tuple[Set[Any], Set[Any], bool]]] = None,
        pending_returns: Optional[List[Tuple[Set[Any], Set[Any], bool]]] = None,
    ):
        """Propaga desvios retidos por um try/finally aos quadros externos após passar pelo finally."""
        if not finally_completes:
            return
        for lbl, (bda, bdu, breach) in pending_breaks:
            new_snap = (bda | finally_da_added, bdu - finally_may_write, breach)
            for frame in reversed(self._flow_exit_frames):
                fkind = frame["kind"]
                if fkind == "try_finally":
                    frame["pending_breaks"].append((lbl, new_snap))
                    break
                if lbl is not None:
                    if lbl in frame["labels"]:
                        frame["breaks"].append(new_snap)
                        break
                elif fkind in ("loop", "switch"):
                    frame["breaks"].append(new_snap)
                    break
        for lbl, (cda, cdu, creach) in pending_continues:
            new_snap = (cda | finally_da_added, cdu - finally_may_write, creach)
            for frame in reversed(self._flow_exit_frames):
                fkind = frame["kind"]
                if fkind == "try_finally":
                    frame["pending_continues"].append((lbl, new_snap))
                    break
                if lbl is not None:
                    if fkind == "loop" and lbl in frame["labels"]:
                        frame["continues"].append(new_snap)
                        break
                elif fkind == "loop":
                    frame["continues"].append(new_snap)
                    break
        for yda, ydu, yreach in (pending_yields or []):
            new_snap = (yda | finally_da_added, ydu - finally_may_write, yreach)
            for frame in reversed(self._flow_exit_frames):
                if frame["kind"] == "try_finally":
                    frame["pending_yields"].append(new_snap)
                    break
                if frame["kind"] == "switch_expr":
                    frame["yields"].append(new_snap)
                    break
        for rda, rdu, rreach in (pending_returns or []):
            new_snap = (rda | finally_da_added, rdu - finally_may_write, rreach)
            for frame in reversed(self._flow_exit_frames):
                if frame["kind"] == "try_finally":
                    frame["pending_returns"].append(new_snap)
                    break
                if frame["kind"] == "callable":
                    frame["returns"].append(new_snap)
                    break

    def _flow_check_read(self, name: str, line: int, is_this_qualified: bool = False):
        """Verifica se variável local ou campo blank final foi definitivamente inicializado antes da leitura."""
        if not self._flow_reachable or self._flow_suppress_errors or not name or name == "_":
            return
        if not is_this_qualified:
            local_info = self._find_local_var_info(name)
            if local_info is not None:
                vid = ("local", id(local_info))
                if vid in self._flow_tracked and vid not in self._flow_da:
                    self.errors.append(
                        SemanticError(f"A variável local '{name}' pode não ter sido inicializada (JLS §16).", line)
                    )
                return
        if self._callable_kind in ("constructor", "initializer") and name in self._flow_blank_final_fields:
            finfo = self._flow_blank_final_fields[name]
            if is_this_qualified and finfo.get("is_static", False):
                return
            if finfo.get("is_final", False):
                vid = finfo["vid"]
                if vid in self._flow_tracked and vid not in self._flow_da:
                    self.errors.append(
                        SemanticError(f"O campo 'final' '{name}' pode não ter sido inicializado antes da leitura (JLS §16).", line)
                    )

    def _flow_apply_local_write(self, name: str, line: int, is_compound: bool = False, is_this_qualified: bool = False):
        """Aplica escrita em variável local ou campo final conforme regras DA/DU da JLS §16."""
        if not name or name == "_":
            return
        if not is_this_qualified:
            local_info = self._find_local_var_info(name)
            if local_info is not None:
                vid = ("local", id(local_info))
                if is_compound:
                    if self._flow_reachable and not self._flow_suppress_errors:
                        if vid in self._flow_tracked and vid not in self._flow_da:
                            self.errors.append(
                                SemanticError(f"A variável local '{name}' pode não ter sido inicializada (JLS §16).", line)
                            )
                        if local_info.get("is_final", False):
                            self.errors.append(
                                SemanticError(f"Não é possível modificar a variável 'final' '{name}'.", line)
                            )
                    self._record_lambda_capture(name, line)
                    local_info["reassigned"] = True
                    if self._flow_reachable:
                        self._flow_da.add(vid)
                        self._flow_du.discard(vid)
                        self._flow_record_write_id(vid)
                    return

                # Atribuição simples '='
                was_du = (vid in self._flow_du) if vid in self._flow_tracked else (not local_info.get("has_initializer", True))
                if self._flow_reachable and not self._flow_suppress_errors:
                    if local_info.get("is_final", False) and not was_du:
                        self.errors.append(
                            SemanticError(f"Não é possível modificar a variável 'final' '{name}'.", line)
                        )
                self._record_lambda_capture(name, line)
                if not was_du:
                    local_info["reassigned"] = True
                else:
                    local_info["has_initializer"] = True
                if self._flow_reachable:
                    self._flow_da.add(vid)
                    self._flow_du.discard(vid)
                    self._flow_record_write_id(vid)
                return

        if self._callable_kind in ("constructor", "initializer") and name in self._flow_blank_final_fields:
            finfo = self._flow_blank_final_fields[name]
            if finfo.get("is_final", False) and not self._flow_in_delegating_ctor:
                if is_this_qualified and finfo.get("is_static", False):
                    return
                vid = finfo["vid"]
                if is_compound:
                    if self._flow_reachable and not self._flow_suppress_errors:
                        self.errors.append(
                            SemanticError(f"Não é possível modificar o campo 'final' '{name}' com operador composto.", line)
                        )
                    if self._flow_reachable:
                        self._flow_da.add(vid)
                        self._flow_du.discard(vid)
                        self._flow_record_write_id(vid)
                    return
                if self._flow_reachable and not self._flow_suppress_errors and vid not in self._flow_du:
                    self.errors.append(
                        SemanticError(f"O campo 'final' '{name}' já pode ter sido inicializado (JLS §16).", line)
                    )
                if self._flow_reachable:
                    self._flow_da.add(vid)
                    self._flow_du.discard(vid)
                    self._flow_record_write_id(vid)

    def _snapshot_local_var_flags(self) -> List[Tuple[Dict[str, Any], bool, bool]]:
        """Captura sinalizadores mutáveis de variáveis locais externas antes de passo especulativo de laço."""
        saved = []
        for scope in self._local_var_scopes:
            for info in scope.values():
                saved.append((info, info.get("has_initializer", True), info.get("reassigned", False)))
        for scope in self._active_pattern_scopes:
            for info in scope.values():
                saved.append((info, info.get("has_initializer", True), info.get("reassigned", False)))
        return saved

    def _restore_local_var_flags(self, saved: List[Tuple[Dict[str, Any], bool, bool]]):
        """Restaura sinalizadores mutáveis de variáveis locais externas após passo especulativo de laço."""
        for info, has_init, reassigned in saved:
            info["has_initializer"] = has_init
            info["reassigned"] = reassigned

    def _reset_analyzer_state(self):
        self.errors = []
        self.unresolved_checks = []
        self._in_early_construction_context = False
        self._in_compact_constructor = False
        self._compact_component_names = set()
        self._declared_types = {}
        self._annotation_interfaces = {}
        self._enums = {}
        self._static_imports = set()
        self._has_wildcard_static_import = False
        self._validated_ann_targets = set()
        self._loop_depth = 0
        self._switch_depth = 0
        self._switch_expr_depth = 0
        self._callable_kind = "top_level"
        self._current_return_type = None
        self._active_labels = {}
        self._local_var_scopes = []
        self._active_pattern_scopes = []
        self._local_type_scopes = []
        self._local_declared_type_scopes = []
        self._enclosing_type_names = []
        self._current_type_is_local = False
        self._in_static_context = False
        self._anon_enclosing_blocked = False
        self._static_context_local_keys = set()
        self._lambda_scope_floor_stack = []
        self._pending_lambda_captures = []
        self._lambda_return_exprs_stack = []
        self._inferred_types = {}
        self._validated_literal_ids: Set[int] = set()
        self._switch_yield_exprs_stack = []
        self._switch_expected_type_stack = []
        self._flow_da = set()
        self._flow_du = set()
        self._flow_reachable = True
        self._flow_tracked = {}
        self._flow_exit_frames = []
        self._flow_write_trackers = []
        self._flow_pending_labels = set()
        self._flow_suppress_errors = False
        self._flow_blank_final_fields = {}
        self._flow_in_delegating_ctor = False
        self._const_eval_stack = set()
        self._capture_vars = {}
        self._capture_counter = 0
        self._active_type_params = []
        self._subtype_visiting = set()
        self._reported_classpath_diags = set()
        self._reachability_const_bools = {}
        self._checked_explicit_imports = set()
        self._checked_module_imports = set()
        self._declared_modules = {}
        self._declared_top_level_pkg_names: Set[Tuple[str, str]] = set()
        self._exception_analyzer.reset()
        self._inheritance_analyzer.reset()

    def get_classpath_coverage(self) -> Dict[str, Any]:
        """Retorna relatório honesto de cobertura da biblioteca padrão e classpath externo."""
        return self._classpath_resolver.coverage_report()

    def _flush_classpath_diagnostics(self, line: int = 1) -> None:
        """Converte diagnósticos de classpath/bytecode (versão incompatível, corrupção, ausência) em mensagens semânticas."""
        for diag in self._classpath_resolver.get_diagnostics():
            key = (diag.kind, diag.target or diag.message)
            if key in self._reported_classpath_diags:
                continue
            self._reported_classpath_diags.add(key)
            if diag.kind in ("unsupported_class_version", "corrupt_classfile"):
                self.errors.append(SemanticError(diag.message, line))
            elif diag.kind == "missing_entry":
                self._record_unresolved(diag.message)

    def _get_declared_module_exported_packages(self, module_name: str, seen: Optional[Set[str]] = None) -> List[str]:
        """Retorna pacotes exportados (e requires transitive) de módulos declarados nas unidades internas."""
        if not module_name:
            return []
        if seen is None:
            seen = set()
        if module_name in seen:
            return []
        seen.add(module_name)
        if module_name not in self._declared_modules:
            return list(self._classpath_resolver.get_module_exported_packages(module_name) or [])
        meta = self._declared_modules[module_name]
        pkgs = list(meta.get("exports", []))
        for req in meta.get("transitive_requires", []):
            for p in self._get_declared_module_exported_packages(req, seen):
                if p not in pkgs:
                    pkgs.append(p)
        return pkgs

    def _current_import_context(self) -> Tuple[str, List[Tuple[str, bool]]]:
        """Retorna (pacote_atual, lista[(nome_import, is_wildcard)]) da CompilationUnit ativa."""
        pkg = getattr(self._inheritance_analyzer, "_current_unit_package", "") or ""
        unit = getattr(self._inheritance_analyzer, "_current_unit", None)
        imports: List[Tuple[str, bool]] = []
        if unit is not None:
            for imp in getattr(unit, "imports", []) or []:
                if getattr(imp, "is_static", False) or not getattr(imp, "name", None):
                    continue
                if getattr(imp, "is_module", False):
                    mod_name = imp.name
                    for exp_pkg in self._get_declared_module_exported_packages(mod_name):
                        imports.append((exp_pkg, True))
                    ext_pkgs = self._classpath_resolver.get_module_exported_packages(mod_name)
                    if ext_pkgs:
                        for exp_pkg in ext_pkgs:
                            imports.append((exp_pkg, True))
                    continue
                is_wild = bool(getattr(imp, "is_wildcard", False))
                iname = imp.name[:-2] if (is_wild and imp.name.endswith(".*")) else imp.name
                imports.append((iname, is_wild))
        return pkg, imports

    def _format_ext_type(self, type_str: Optional[str]) -> Optional[str]:
        """Normaliza FQNs java.lang.<Nome> vindos do bytecode para compatibilidade com tipos simples quando não sombreados."""
        if not type_str:
            return type_str
        def _repl(match: re.Match) -> str:
            sname = match.group(1)
            if "$" in sname:
                return f"java.lang.{sname.replace('$', '.')}"
            if self._lookup_type_decl(sname) is not None:
                return match.group(0)
            return sname
        return self._JAVA_LANG_SIMPLIFY_RE.sub(_repl, type_str)

    def _is_partial_external_stdlib(self, ext: ExternalTypeInfo) -> bool:
        """Indica se o tipo pertence à stdlib carregada a partir de uma JDK/JRE anterior ao alvo Java 26."""
        return self._classpath_resolver.is_older_stdlib() and ext.fqn.startswith(("java.", "javax.", "jdk.", "sun."))


    def _lookup_internal_type_key(self, raw_base: Optional[str], context_type: Optional[str] = None) -> Optional[str]:
        """Resolve chave canônica somente se o tipo pertencer às unidades de compilação internas."""
        if not raw_base:
            return None
        key = self._inheritance_analyzer.resolve_type_key(raw_base, context_type=context_type)
        if key is not None and (key in self._inheritance_analyzer._type_meta or self._lookup_type_decl(key) is not None):
            return key
        return None

    def _resolve_external_type(self, type_name: Optional[str]) -> Optional[ExternalTypeInfo]:
        """Resolve tipo externo no classpath respeitando estritamente a precedência dos tipos declarados na unidade."""
        if not type_name:
            return None
        clean = self._strip_leading_type_annotations(type_name) or type_name
        stripped = self._strip_generics(clean)
        if not stripped:
            return None
        base, _ = self._split_type_dims(stripped)
        if not base or base in self.PRIMITIVE_TYPES or base in ("void", "var", "null", "desconhecido"):
            return None
        if self._is_capture_var(base) or self._is_wildcard_arg(base) or self._lookup_type_param_bounds(base) is not None:
            return None

        # Precedência absoluta da unidade de compilação (JLS §6.5 / Requisito 12)
        simple = base.split(".")[-1]
        for lscope in reversed(self._local_declared_type_scopes):
            if base in lscope or ("." not in base and simple in lscope):
                return None
        internal_key = self._inheritance_analyzer.resolve_type_key(base)
        if internal_key is not None and internal_key in self._inheritance_analyzer._type_meta:
            return None
        if "." not in base and self._lookup_type_decl(base) is not None:
            return None

        pkg, imports = self._current_import_context()
        ext = self._classpath_resolver.resolve_type(
            base,
            current_package=pkg,
            imports=imports,
            compat_fqns=self.BUILTIN_COMPAT_FQNS,
        )
        self._flush_classpath_diagnostics(line=1)
        return ext

    def _validate_unit_imports(self, unit: CompilationUnit) -> None:
        """Verifica imports explícitos não-estáticos e imports de módulo contra tipos/módulos internos ou externos."""
        self._flush_classpath_diagnostics(line=1)
        for imp in getattr(unit, "imports", []) or []:
            if getattr(imp, "is_module", False):
                iname = getattr(imp, "name", None)
                if not iname or iname in self._checked_module_imports:
                    continue
                self._checked_module_imports.add(iname)
                iline = getattr(imp, "line", 1)
                if iname in self._declared_modules:
                    continue
                if self._classpath_resolver.has_module(iname):
                    continue
                self._record_unresolved(
                    f"Módulo '{iname}' não encontrado no classpath/jmods ou sem descritor modular no runtime atual (linha {iline})."
                )
                continue
            if getattr(imp, "is_static", False) or getattr(imp, "is_wildcard", False):
                continue
            iname = getattr(imp, "name", None)
            if not iname or iname in self._checked_explicit_imports:
                continue
            self._checked_explicit_imports.add(iname)
            iline = getattr(imp, "line", 1)
            if iname in self._inheritance_analyzer._type_meta:
                continue
            ext = self._classpath_resolver.get_type_info_by_fqn(iname)
            self._flush_classpath_diagnostics(line=iline)
            if ext is not None:
                ok, reason = self._inheritance_analyzer.is_type_accessible(ext.fqn)
                if not ok and reason:
                    self.errors.append(SemanticError(reason, iline))
                continue
            simple = iname.split(".")[-1]
            if self.BUILTIN_COMPAT_FQNS.get(simple) == iname:
                continue
            self._record_unresolved(
                f"Classe ou interface importada '{iname}' não encontrada no classpath ou biblioteca padrão (linha {iline})."
            )

    def _ext_field_to_dict(self, finfo: ExternalFieldInfo, ext_owner: ExternalTypeInfo, tvar_map: Dict[str, str]) -> Dict[str, Any]:
        """Converte metadados de campo de bytecode para o formato interno do analisador semântico."""
        raw_t = self._format_ext_type(finfo.type) or finfo.type or "Object"
        ftype = self._substitute_type_vars(raw_t, tvar_map) or raw_t
        cat = "constante_interface" if ext_owner.kind == "interface" else ("constante_enum" if finfo.is_static and finfo.is_final and ext_owner.kind == "enum" else "campo")
        return {
            "type": ftype,
            "is_static": finfo.is_static,
            "is_final": finfo.is_final,
            "category": cat,
            "owner": ext_owner.simple_name,
            "owner_key": ext_owner.fqn,
            "access": finfo.access,
            "constant_value": finfo.constant_value,
        }


    _COMPAT_DEDUP_RE = re.compile(
        r"(?<![.\w$])(" + "|".join(sorted(BUILTIN_COMPAT_FQNS.keys(), key=len, reverse=True)) + r")(?![.\w$])"
    )

    def _sig_dedup_key(
        self,
        params: List[str],
        varargs: bool,
        sig: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, ...]:
        """Normaliza assinaturas de bytecode e BUILTIN_METHODS para evitar duplicatas no resolvedor de sobrecarga."""
        canon_params = tuple(
            self._COMPAT_DEDUP_RE.sub(lambda m: self.BUILTIN_COMPAT_FQNS[m.group(1)], prm or "")
            for prm in params
        )
        tparams = (sig or {}).get("tparams") or []
        if not tparams:
            return (canon_params, bool(varargs))
        tparam_bounds = (sig or {}).get("tparam_bounds") or {}
        canon_tparams = tuple(
            (
                tp,
                tuple(
                    self._COMPAT_DEDUP_RE.sub(lambda m: self.BUILTIN_COMPAT_FQNS[m.group(1)], b or "")
                    for b in (tparam_bounds.get(tp) or ["Object"])
                ),
            )
            for tp in tparams
        )
        return (canon_params, bool(varargs), canon_tparams)

    def _ext_method_to_sig(self, minfo: ExternalMethodInfo, ext_owner: ExternalTypeInfo, tvar_map: Dict[str, str]) -> Dict[str, Any]:
        """Converte metadados de método/construtor de bytecode para assinatura de sobrecarga e herança."""
        params: List[str] = []
        raw_params = list(minfo.params or [])
        for idx, p in enumerate(raw_params):
            fmt_p = self._format_ext_type(p) or p
            if minfo.varargs and idx == len(raw_params) - 1 and fmt_p.endswith("[]"):
                fmt_p = fmt_p[:-2]
            if tvar_map:
                fmt_p = self._substitute_type_vars(fmt_p, tvar_map) or fmt_p
            params.append(fmt_p)

        if minfo.is_constructor:
            ret_t = ext_owner.simple_name
        else:
            raw_ret = self._format_ext_type(minfo.ret) or minfo.ret or "void"
            ret_t = (self._substitute_type_vars(raw_ret, tvar_map) or raw_ret) if tvar_map else raw_ret

        tparam_bounds: Dict[str, List[str]] = {}
        for tp in minfo.tparams:
            bs = minfo.tparam_bounds.get(tp, ["java.lang.Object"])
            tparam_bounds[tp] = [self._format_ext_type(b) or b for b in bs] or ["Object"]

        throws_list: List[str] = []
        for th in minfo.throws:
            fmt_th = self._format_ext_type(th) or th
            if tvar_map:
                fmt_th = self._substitute_type_vars(fmt_th, tvar_map) or fmt_th
            throws_list.append(fmt_th)

        return {
            "name": minfo.name,
            "params": params,
            "ret": ret_t,
            "static": minfo.static,
            "varargs": minfo.varargs,
            "tparams": list(minfo.tparams),
            "tparam_bounds": tparam_bounds,
            "throws": throws_list,
            "owner": ext_owner.simple_name,
            "owner_key": ext_owner.fqn,
            "owner_kind": ext_owner.kind,
            "access": minfo.access,
            "is_abstract": minfo.is_abstract,
            "is_final": minfo.is_final,
            "is_default": minfo.is_default,
        }

    def _collect_unit_static_imports(self, unit: CompilationUnit):
        self._static_imports = set()
        self._has_wildcard_static_import = False
        for imp in getattr(unit, "imports", []):
            if getattr(imp, "is_static", False):
                if getattr(imp, "is_wildcard", False):
                    self._has_wildcard_static_import = True
                elif getattr(imp, "name", None):
                    self._static_imports.add(imp.name.split(".")[-1])

    def analyze(self, program: ASTNode) -> List[SemanticError]:
        """Executa a análise semântica sobre a árvore sintática."""
        self._reset_analyzer_state()
        if not program:
            return self.errors

        # 1. Pré-indexa tipos e imports estáticos e analisa Unidade de Compilação completa
        if isinstance(program, CompilationUnit):
            self._preindex_compilation_unit(program)
            self._inheritance_analyzer.set_current_unit(program)
            self._validate_unit_imports(program)
            if program.package is not None:
                pkg_annos = [
                    m for m in getattr(program.package, "modifiers", [])
                    if isinstance(m, Annotation)
                ]
                if not pkg_annos and getattr(program.package, "annotations", None):
                    pkg_annos = list(program.package.annotations)
                self._analyze_annotations(pkg_annos, valid_targets={"PACKAGE"})
            for type_decl in program.type_declarations:
                self._analyze_type_declaration(type_decl, is_nested=False, is_local=False)

        # 2. Analisa comandos didáticos de nível superior ou fragmentos
        statements = getattr(program, "statements", [])
        if statements:
            self._local_var_scopes = [{}]
            self._active_pattern_scopes = [{}]
            self._flow_da = set()
            self._flow_du = set()
            self._flow_reachable = True
            self._flow_tracked = {}
            self._flow_exit_frames = []
            self._flow_write_trackers = []
            self._flow_pending_labels = set()
            self._exception_analyzer.push_callable_frame("top_level", "escopo superior", [], enforce_unreported=False)
            try:
                self._check_stmt_list_with_flow(statements)
                self._check_stmt_list_reachability(statements, True)
            finally:
                self._exception_analyzer.pop_callable_frame()

        return self.errors

    def analyze_units(self, units: List[ASTNode]) -> List[SemanticError]:
        """Executa a análise semântica conjunta sobre múltiplas CompilationUnits (multi-pacote)."""
        self._reset_analyzer_state()
        if not units:
            return self.errors

        # Passada 1: pré-indexa todos os tipos de todas as unidades antes de validar referências cruzadas
        for unit in units:
            if isinstance(unit, CompilationUnit):
                self._preindex_compilation_unit(unit)

        # Passada 2: analisa cada unidade com seu próprio contexto de pacote e imports
        for unit in units:
            if isinstance(unit, CompilationUnit):
                self._inheritance_analyzer.set_current_unit(unit)
                self._collect_unit_static_imports(unit)
                self._validate_unit_imports(unit)
                if unit.package is not None:
                    pkg_annos = [
                        m for m in getattr(unit.package, "modifiers", [])
                        if isinstance(m, Annotation)
                    ]
                    if not pkg_annos and getattr(unit.package, "annotations", None):
                        pkg_annos = list(unit.package.annotations)
                    self._analyze_annotations(pkg_annos, valid_targets={"PACKAGE"})
                for type_decl in unit.type_declarations:
                    self._analyze_type_declaration(type_decl, is_nested=False, is_local=False)

            statements = getattr(unit, "statements", [])
            if statements:
                self._local_var_scopes = [{}]
                self._active_pattern_scopes = [{}]
                self._flow_da = set()
                self._flow_du = set()
                self._flow_reachable = True
                self._flow_tracked = {}
                self._flow_exit_frames = []
                self._flow_write_trackers = []
                self._flow_pending_labels = set()
                self._exception_analyzer.push_callable_frame("top_level", "escopo superior", [], enforce_unreported=False)
                try:
                    self._check_stmt_list_with_flow(statements)
                finally:
                    self._exception_analyzer.pop_callable_frame()

        return self.errors

    def _preindex_compilation_unit(self, unit: CompilationUnit):
        """Pré-indexa classes, interfaces, enums, records e @interfaces declarados na unidade."""
        self._collect_unit_static_imports(unit)
        self._inheritance_analyzer.register_unit_types(unit)

        def visit_type(node: ASTNode):
            if isinstance(node, AnnotationInterfaceDeclaration):
                self._declared_types.setdefault(node.name, ("annotation_interface", node))
                self._annotation_interfaces.setdefault(node.name, node)
                for m in node.members:
                    visit_type(m)
            elif isinstance(node, EnumDeclaration):
                self._declared_types.setdefault(node.name, ("enum", node))
                self._enums.setdefault(node.name, node)
                for m in node.members:
                    visit_type(m)
                for c in node.constants:
                    if isinstance(c.body, EnumConstantBody):
                        for cm in c.body.members:
                            visit_type(cm)
            elif isinstance(node, RecordDeclaration):
                self._declared_types.setdefault(node.name, ("record", node))
                for m in node.members:
                    visit_type(m)
            elif isinstance(node, InterfaceDeclaration):
                self._declared_types.setdefault(node.name, ("interface", node))
                for m in node.members:
                    visit_type(m)
            elif isinstance(node, ClassDeclaration):
                self._declared_types.setdefault(node.name, ("class", node))
                for m in node.members:
                    visit_type(m)

        for tdecl in getattr(unit, "type_declarations", []):
            visit_type(tdecl)

        mod_decl = getattr(unit, "module_declaration", None)
        if isinstance(mod_decl, ModuleDeclaration) and getattr(mod_decl, "name", None):
            exports: List[str] = []
            trans_reqs: List[str] = []
            for d in getattr(mod_decl, "directives", []) or []:
                if isinstance(d, ExportsDirective) and not getattr(d, "to_modules", None):
                    if getattr(d, "package_name", None):
                        exports.append(d.package_name)
                elif isinstance(d, RequiresDirective) and getattr(d, "is_transitive", False):
                    if getattr(d, "module_name", None):
                        trans_reqs.append(d.module_name)
            self._declared_modules[mod_decl.name] = {
                "exports": exports,
                "transitive_requires": trans_reqs,
            }

    def _index_local_type_decl(self, node: ASTNode):
        """Registra declarações de tipos locais (inclusive aninhados e enums locais) no escopo de bloco atual."""
        if not self._local_declared_type_scopes:
            self._local_declared_type_scopes.append({})
        target = self._local_declared_type_scopes[-1]

        def visit_local(n: ASTNode):
            if isinstance(n, AnnotationInterfaceDeclaration):
                target.setdefault(n.name, ("annotation_interface", n))
                self._inheritance_analyzer.register_local_type(n, "annotation_interface")
                for m in n.members:
                    visit_local(m)
            elif isinstance(n, EnumDeclaration):
                target.setdefault(n.name, ("enum", n))
                self._enums.setdefault(n.name, n)
                self._inheritance_analyzer.register_local_type(n, "enum")
                for m in n.members:
                    visit_local(m)
                for c in n.constants:
                    if isinstance(c.body, EnumConstantBody):
                        for cm in c.body.members:
                            visit_local(cm)
            elif isinstance(n, RecordDeclaration):
                target.setdefault(n.name, ("record", n))
                self._inheritance_analyzer.register_local_type(n, "record")
                for m in n.members:
                    visit_local(m)
            elif isinstance(n, InterfaceDeclaration):
                target.setdefault(n.name, ("interface", n))
                self._inheritance_analyzer.register_local_type(n, "interface")
                for m in n.members:
                    visit_local(m)
            elif isinstance(n, ClassDeclaration):
                target.setdefault(n.name, ("class", n))
                self._inheritance_analyzer.register_local_type(n, "class")
                for m in n.members:
                    visit_local(m)

        visit_local(node)

    def _analyze_type_declaration(self, type_decl: ASTNode, is_nested: bool = False, is_local: bool = False):
        """Despacha a análise semântica para declarações de tipo (class, interface, enum, record, @interface, module)."""
        tname = getattr(type_decl, "name", None)
        pushed_key = None
        if tname and not isinstance(type_decl, ModuleDeclaration):
            self._enclosing_type_names.append(tname)
            pushed_key = self._inheritance_analyzer.push_enclosing_type(type_decl)
        saved_is_local = self._current_type_is_local
        self._current_type_is_local = is_local
        added_static_local = False
        if is_local:
            self._index_local_type_decl(type_decl)
            if pushed_key and (self._in_static_context or self._in_early_construction_context or self._anon_enclosing_blocked):
                self._static_context_local_keys.add(pushed_key)
                added_static_local = True
        try:
            if isinstance(type_decl, ClassDeclaration):
                self.analyze_class(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, InterfaceDeclaration):
                self.analyze_interface(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, EnumDeclaration):
                self.analyze_enum(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, RecordDeclaration):
                self.analyze_record(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, AnnotationInterfaceDeclaration):
                self.analyze_annotation_interface(type_decl, is_nested=is_nested, is_local=is_local)
            elif isinstance(type_decl, ModuleDeclaration):
                self._analyze_annotations(getattr(type_decl, "annotations", []), valid_targets={"MODULE"})
                self.symbols.declare(type_decl.name, "module", type_decl.line, category="modulo")
        finally:
            if added_static_local and pushed_key:
                self._static_context_local_keys.discard(pushed_key)
            self._current_type_is_local = saved_is_local
            if tname and not isinstance(type_decl, ModuleDeclaration):
                self._inheritance_analyzer.pop_enclosing_type(pushed_key)
                self._enclosing_type_names.pop()

    def _effective_access(self, modifiers: List[str]) -> int:
        """Retorna o nível de acesso efetivo segundo a JLS."""
        for m in modifiers:
            if m in self.ACCESS_RANK:
                return self.ACCESS_RANK[m]
        return self.ACCESS_RANK["package"]

    def _check_conflicting_access_modifiers(self, modifiers: List[str], context_label: str, line: int):
        """Verifica se há múltiplos modificadores de acesso incompatíveis na mesma declaração."""
        access_mods = [m for m in modifiers if m in ("public", "protected", "private")]
        if len(access_mods) > 1:
            self.errors.append(
                SemanticError(f"Modificadores de acesso conflitantes ({', '.join(access_mods)}) em {context_label}.", line)
            )

    def _validate_type_modifiers(
        self,
        modifiers: List[str],
        kind: str,
        name: str,
        line: int,
        is_nested: bool = False,
        is_local: bool = False,
    ):
        """Valida modificadores permitidos para interfaces, enums e records (JLS §8.9, §8.10, §9.1)."""
        self._check_conflicting_access_modifiers(modifiers, f"{kind} '{name}'", line)
        mod_set = set(modifiers)

        if is_local:
            for acc in ("public", "protected", "private"):
                if acc in mod_set:
                    self.errors.append(
                        SemanticError(f"Modificador de acesso '{acc}' não é permitido em {kind} local '{name}'.", line)
                    )
            if "static" in mod_set:
                self.errors.append(
                    SemanticError(
                        f"Modificador 'static' explícito não é permitido em {kind} local '{name}' (JLS §14.3).",
                        line,
                    )
                )
            for forbidden_local in ("sealed", "non-sealed"):
                if forbidden_local in mod_set:
                    self.errors.append(
                        SemanticError(
                            f"Modificador '{forbidden_local}' não é permitido em {kind} local '{name}' (JLS §14.3).",
                            line,
                        )
                    )
        elif not is_nested:
            for m in ("private", "protected"):
                if m in mod_set:
                    self.errors.append(
                        SemanticError(f"Modificador '{m}' não é permitido em {kind} de nível superior '{name}'.", line)
                    )
            if "static" in mod_set:
                self.errors.append(
                    SemanticError(f"Modificador 'static' não é permitido em {kind} de nível superior '{name}'.", line)
                )

        if kind == "interface":
            if "final" in mod_set:
                self.errors.append(SemanticError(f"A interface '{name}' não pode ser declarada como 'final' (JLS §9.1.1).", line))
            if "sealed" in mod_set and "non-sealed" in mod_set:
                self.errors.append(SemanticError(f"A interface '{name}' não pode combinar 'sealed' e 'non-sealed'.", line))
        elif kind == "enum":
            for bad in ("abstract", "final", "sealed", "non-sealed"):
                if bad in mod_set:
                    self.errors.append(SemanticError(f"Enum '{name}' não pode possuir modificador '{bad}' (JLS §8.9).", line))
        elif kind == "record":
            for bad in ("abstract", "sealed", "non-sealed"):
                if bad in mod_set:
                    self.errors.append(SemanticError(f"Record '{name}' não pode possuir modificador '{bad}' (JLS §8.10).", line))
        elif kind == "annotation_interface":
            for bad in ("final", "sealed", "non-sealed"):
                if bad in mod_set:
                    self.errors.append(
                        SemanticError(f"Annotation interface '@{name}' não pode possuir modificador '{bad}' (JLS §9.6).", line)
                    )

    def _declare_type_symbol(self, name: str, type_label: str, category: str, dup_label: str, line: int):
        """Declara símbolo de tipo no escopo atual reportando duplicidade no mesmo escopo/pacote."""
        if len(self._enclosing_type_names) <= 1 and getattr(self._inheritance_analyzer, "_current_unit", None) is not None:
            cur_pkg = getattr(self._inheritance_analyzer, "_current_unit_package", "") or ""
            pkg_key = (cur_pkg, name)
            if pkg_key in self._declared_top_level_pkg_names:
                prev = self.symbols.lookup(name)
                prev_line = f" (declarada na linha {prev['line']})" if prev and "line" in prev else ""
                self.errors.append(SemanticError(f"{dup_label} '{name}' declarada novamente{prev_line}.", line))
                return
            self._declared_top_level_pkg_names.add(pkg_key)
            if self.symbols.lookup(name) is None:
                self.symbols.declare(name, type_label, line, category=category)
            elif cur_pkg:
                self.symbols.declare(f"{cur_pkg}.{name}", type_label, line, category=category)
            return
        prev = self.symbols.lookup(name)
        if not self.symbols.declare(name, type_label, line, category=category):
            prev_line = f" (declarada na linha {prev['line']})" if prev and "line" in prev else ""
            self.errors.append(SemanticError(f"{dup_label} '{name}' declarada novamente{prev_line}.", line))

    def _analyze_field_declaration(
        self,
        member: FieldDeclaration,
        container_label: str = "classe",
        is_interface_constant: bool = False,
        collected_inst_throws: Optional[List[Tuple[str, int, str]]] = None,
    ):
        """Analisa declarações de campo ou constantes de interface, registrando símbolos e validando '_' e inicializadores."""
        self._analyze_annotations(
            getattr(member, "annotations", []),
            valid_targets={"FIELD"},
            adjacent_type_ref=getattr(member, "type_ref", None),
        )
        self._check_type_ref_annotations(getattr(member, "type_ref", None))

        decls = member.declarators if hasattr(member, "declarators") and member.declarators else []
        if getattr(member, "type_ref", None) is not None and getattr(member.type_ref, "name", None) == "var":
            self.errors.append(
                SemanticError("'var' não é permitido em declarações de campo (JLS §8.3 / §14.4).", member.line)
            )
        is_static = True if is_interface_constant else ("static" in member.modifiers)
        is_final = True if is_interface_constant else ("final" in member.modifiers)
        category = "constante_interface" if is_interface_constant else "campo"
        dup_noun = "Constante" if is_interface_constant else "Campo"

        if not decls and hasattr(member, "name"):
            eff_type = None
            if member.name == "_":
                self.errors.append(
                    SemanticError("O identificador '_' não pode ser utilizado como nome de campo (JLS §8.3 / JEP 456).", member.line)
                )
            else:
                if is_interface_constant and member.initializer is None:
                    self.errors.append(
                        SemanticError(f"Constante de interface '{member.name}' deve possuir inicializador (JLS §9.3).", member.line)
                    )
                eff_type = getattr(member, "effective_type", member.type_ref.full_name)
                const_res = self._resolve_constant_var_declaration(eff_type, is_final, member.initializer)
                is_const = const_res is not None
                decl_extra = {"const_typed": const_res} if is_const else {}
                if not self.symbols.declare(
                    member.name, eff_type, member.line, category=category,
                    is_static=is_static, is_final=is_final, is_compile_constant=is_const, **decl_extra
                ):
                    self.errors.append(SemanticError(f"{dup_noun} '{member.name}' declarado novamente na {container_label}.", member.line))
            if member.initializer is not None:
                init_ctx = self._enter_exec_context("field_initializer", return_type=None, is_static=is_static, share_locals=False)
                defer_inst = (not is_static) and (collected_inst_throws is not None)
                exc_frame = self._exception_analyzer.push_callable_frame(
                    "initializer",
                    f"inicializador do campo '{member.name}'",
                    allowed_throws=[],
                    enforce_unreported=not defer_inst,
                )
                try:
                    if eff_type and eff_type != "var":
                        self._check_expression_with_target(member.initializer, eff_type)
                        self.check_assignment_type(eff_type, member.initializer, member.name, member.line)
                    else:
                        self.check_expression(member.initializer)
                    self._check_reachability_in_expr(member.initializer)
                    self._check_lambda_capture_boundaries()
                finally:
                    popped = self._exception_analyzer.pop_callable_frame()
                    if defer_inst and popped is not None and collected_inst_throws is not None:
                        collected_inst_throws.extend(popped.get("thrown", []))
                    self._restore_exec_context(init_ctx)
            return

        for decl in decls:
            if hasattr(decl, "id") and getattr(decl.id, "dims_annotations", None):
                for da in decl.id.dims_annotations:
                    self._analyze_annotations(da, valid_targets={"TYPE_USE"})
            if decl.name == "_" or (hasattr(decl, "id") and getattr(decl.id, "is_unnamed", False)):
                self.errors.append(
                    SemanticError("O identificador '_' não pode ser utilizado como nome de campo (JLS §8.3 / JEP 456).", decl.line)
                )
                if decl.initializer is not None:
                    self.check_expression(decl.initializer)
                continue

            if is_interface_constant and decl.initializer is None:
                self.errors.append(
                    SemanticError(f"Constante de interface '{decl.name}' deve possuir inicializador (JLS §9.3).", decl.line)
                )

            eff_type = decl.effective_type
            const_res = self._resolve_constant_var_declaration(eff_type, is_final, decl.initializer)
            is_const = const_res is not None
            decl_extra = {"const_typed": const_res} if is_const else {}
            if not self.symbols.declare(
                decl.name, eff_type, decl.line, category=category,
                is_static=is_static, is_final=is_final, is_compile_constant=is_const, **decl_extra
            ):
                self.errors.append(SemanticError(f"{dup_noun} '{decl.name}' declarado novamente na {container_label}.", decl.line))
            if decl.initializer is not None:
                init_ctx = self._enter_exec_context("field_initializer", return_type=None, is_static=is_static, share_locals=False)
                defer_inst = (not is_static) and (collected_inst_throws is not None)
                self._exception_analyzer.push_callable_frame(
                    "initializer",
                    f"inicializador do campo '{decl.name}'",
                    allowed_throws=[],
                    enforce_unreported=not defer_inst,
                )
                try:
                    if eff_type and eff_type != "var":
                        self._check_expression_with_target(decl.initializer, eff_type)
                        self.check_assignment_type(eff_type, decl.initializer, decl.name, decl.line)
                    else:
                        self.check_expression(decl.initializer)
                    self._check_reachability_in_expr(decl.initializer)
                    self._check_lambda_capture_boundaries()
                finally:
                    popped = self._exception_analyzer.pop_callable_frame()
                    if defer_inst and popped is not None and collected_inst_throws is not None:
                        collected_inst_throws.extend(popped.get("thrown", []))
                    self._restore_exec_context(init_ctx)

    def _analyze_method_member(
        self,
        member: MethodDeclaration,
        owner_type: Optional[str] = None,
        is_anonymous: bool = False,
        owner_kind: str = "class",
        owner_modifiers: Optional[List[str]] = None,
    ):
        """Registra um método e analisa annotations, type parameters, parâmetros e corpo em escopo isolado."""
        self._analyze_annotations(
            getattr(member, "annotations", []),
            valid_targets={"METHOD"},
            adjacent_type_ref=getattr(member, "return_type", None),
        )
        eff_ret_type = member.effective_return_type
        is_static = "static" in member.modifiers
        self.symbols.declare(member.name, eff_ret_type, member.line, category="metodo", is_static=is_static)
        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("method", return_type=eff_ret_type, is_static=is_static)
        self._push_type_params(getattr(member, "type_parameters", []), is_type_level=False)
        pushed_exc_frame = False
        try:
            self._check_type_parameters_annotations(getattr(member, "type_parameters", []))
            self._check_type_ref_annotations(getattr(member, "return_type", None))
            for da in getattr(member, "dims_annotations", []):
                self._analyze_annotations(da, valid_targets={"TYPE_USE"})
            for tt in getattr(member, "throws_types", []):
                self._check_type_ref_annotations(tt)
            recv = getattr(member, "receiver_parameter", None)
            if recv is not None:
                self._analyze_annotations(getattr(recv, "annotations", []), valid_targets={"TYPE_USE"})
                self._check_type_ref_annotations(getattr(recv, "type_ref", None))

            if getattr(member, "return_type", None) is not None and getattr(member.return_type, "name", None) == "var":
                self.errors.append(
                    SemanticError("'var' não é permitido como tipo de retorno de método (JLS §8.4 / §14.4).", member.line)
                )

            eff_owner = owner_type or self._inheritance_analyzer.current_enclosing_key() or (self._enclosing_type_names[-1] if self._enclosing_type_names else "")
            allowed_throws = self._exception_analyzer.validate_throws_clause(
                getattr(member, "throws_types", []), member.line
            )
            msig = self._extract_method_sig(member, eff_owner, owner_kind=owner_kind)
            msig["name"] = member.name
            self._inheritance_analyzer.validate_method_declaration(
                eff_owner,
                member,
                msig,
                is_anonymous=is_anonymous,
                owner_kind=owner_kind,
                owner_modifiers=owner_modifiers,
            )
            self._exception_analyzer.validate_method_override(
                eff_owner, member, msig, is_anonymous=is_anonymous
            )
            self._exception_analyzer.push_callable_frame(
                "method",
                f"método '{member.name}'",
                allowed_throws=allowed_throws,
                enforce_unreported=True,
            )
            pushed_exc_frame = True
            for p in member.parameters:
                self._analyze_annotations(
                    getattr(p, "annotations", []),
                    valid_targets={"PARAMETER"},
                    adjacent_type_ref=getattr(p, "type_ref", None),
                )
                self._check_type_ref_annotations(getattr(p, "type_ref", None))
                if getattr(p, "type_ref", None) is not None and getattr(p.type_ref, "name", None) == "var":
                    self.errors.append(
                        SemanticError(
                            f"'var' não é permitido em parâmetro formal '{p.name}' (JLS §8.4.1 / §14.4).",
                            getattr(p, "line", member.line),
                        )
                    )
                for ea in getattr(p, "ellipsis_annotations", []):
                    self._analyze_annotations([ea], valid_targets={"TYPE_USE"})
                if p.name != "_":
                    p_type = self._resolve_param_effective_type(p)
                    self._register_local_var(
                        p.name,
                        p_type,
                        p.line,
                        is_final=("final" in getattr(p, "modifiers", [])),
                        has_initializer=True,
                        category="parametro",
                    )
            if member.body:
                self.analyze_block(member.body)
                self._check_stmt_reachability(member.body, True)
            self._check_lambda_capture_boundaries()
        finally:
            if pushed_exc_frame:
                self._exception_analyzer.pop_callable_frame()
            self._restore_exec_context(saved_ctx)
            self.symbols.exit_scope()

    def _emit_ctor_invocation_throws(
        self,
        owner_name: Optional[str],
        inv: Optional[ASTNode],
        line: int,
        is_enum: bool = False,
    ):
        """Propaga exceções verificadas de 'super(...)' explícito/implícito ou 'this(...)' no construtor."""
        if not owner_name or is_enum:
            return
        if isinstance(inv, AlternateConstructorInvocation):
            target_cls = owner_name
            args = list(getattr(inv, "arguments", []) or [])
            desc = "invocação 'this(...)'"
            inv_line = getattr(inv, "line", line)
        else:
            tdecl = self._lookup_type_decl(owner_name)
            if tdecl is None or tdecl[0] != "class":
                return
            ext = getattr(tdecl[1], "extends_type", None)
            if ext is None:
                return
            target_cls = self._normalize_type_str(ext)
            if not target_cls:
                return
            args = list(getattr(inv, "arguments", []) or []) if isinstance(inv, SuperclassConstructorInvocation) else []
            desc = "invocação 'super(...)'" if inv is not None else "construtor padrão implícito 'super()'"
            inv_line = getattr(inv, "line", line) if inv is not None else line

        ctors, is_known, _ = self._collect_type_constructors(target_cls)
        if not is_known:
            self._exception_analyzer.mark_unresolved_thrower()
            return
        if ctors:
            win_sig, _, _ = self._resolve_overload(ctors, args, inv_line, f"{target_cls}(...)")
            if win_sig is not None:
                is_super_ctor = not isinstance(inv, AlternateConstructorInvocation)
                ctor_owner = win_sig.get("owner_key") or win_sig.get("owner") or target_cls
                self._inheritance_analyzer.check_member_access(
                    ctor_owner,
                    win_sig.get("access", "public"),
                    False,
                    "construtor",
                    self._simple_base_name(target_cls) or target_cls,
                    inv_line,
                    via_super=is_super_ctor,
                )
                self._exception_analyzer.emit_thrown(win_sig.get("throws", []), inv_line, desc)

    def _analyze_constructor_member(
        self,
        member: ConstructorDeclaration,
        expected_name: Optional[str] = None,
        is_enum: bool = False,
        is_compact: bool = False,
        derived_components: Optional[List[RecordComponent]] = None,
        seed_flow: Optional[Tuple[Set[Any], Set[Any]]] = None,
    ):
        """Analisa construtor de classe, enum ou record, gerenciando early construction context e regras compactas."""
        self._inheritance_analyzer.validate_constructor_modifiers(member)
        if expected_name is not None and member.name != expected_name:
            self.errors.append(
                SemanticError(f"Nome do construtor '{member.name}' não corresponde ao tipo declarador '{expected_name}'.", member.line)
            )

        if is_enum:
            for acc in ("public", "protected"):
                if acc in member.modifiers:
                    self.errors.append(
                        SemanticError(
                            f"Construtor de enum '{expected_name or member.name}' não pode possuir modificador '{acc}'; construtores de enum são implicitamente 'private' (JLS §8.9.2).",
                            member.line,
                        )
                    )

        self._analyze_annotations(getattr(member, "annotations", []), valid_targets={"CONSTRUCTOR"})

        self.symbols.declare(member.name, member.name, member.line, category="construtor")
        self.symbols.enter_scope()

        derived_names: Set[str] = set()
        if is_compact and derived_components is not None:
            for comp in derived_components:
                if comp.name != "_":
                    derived_names.add(comp.name)

        saved_ctx = self._enter_exec_context(
            "constructor",
            return_type=None,
            is_compact=is_compact,
            compact_names=derived_names if is_compact else set(),
            is_static=False,
        )
        self._push_type_params(getattr(member, "type_parameters", []), is_type_level=False)
        pushed_exc_frame = False
        ctor_owner = expected_name or (self._enclosing_type_names[-1] if self._enclosing_type_names else member.name)
        try:
            self._check_type_parameters_annotations(getattr(member, "type_parameters", []))
            for tt in getattr(member, "throws_types", []):
                self._check_type_ref_annotations(tt)
            recv = getattr(member, "receiver_parameter", None)
            if recv is not None:
                self._analyze_annotations(getattr(recv, "annotations", []), valid_targets={"TYPE_USE"})
                self._check_type_ref_annotations(getattr(recv, "type_ref", None))

            allowed_ctor_throws = self._exception_analyzer.validate_throws_clause(
                getattr(member, "throws_types", []), member.line
            )
            self._exception_analyzer.push_callable_frame(
                "constructor",
                f"construtor '{member.name}'",
                allowed_throws=allowed_ctor_throws,
                enforce_unreported=True,
            )
            pushed_exc_frame = True
            if seed_flow is not None:
                seed_da, seed_du = seed_flow
                self._flow_da |= set(seed_da)
                self._flow_du |= set(seed_du)
                for fn, fi in self._flow_blank_final_fields.items():
                    self._flow_tracked[fi["vid"]] = {"name": fn, "is_final": True, "kind": "field", "line": fi["line"]}

            ctor_frame = self._flow_push_exit_frame("callable")
            ctor_frame["returns"] = []

            if is_compact and derived_components is not None:
                for comp in derived_components:
                    if comp.name != "_":
                        self._register_local_var(
                            comp.name,
                            comp.effective_type,
                            comp.line,
                            has_initializer=True,
                            category="parametro",
                        )
            else:
                for p in member.parameters:
                    self._analyze_annotations(
                        getattr(p, "annotations", []),
                        valid_targets={"PARAMETER"},
                        adjacent_type_ref=getattr(p, "type_ref", None),
                    )
                    self._check_type_ref_annotations(getattr(p, "type_ref", None))
                    if getattr(p, "type_ref", None) is not None and getattr(p.type_ref, "name", None) == "var":
                        self.errors.append(
                            SemanticError(
                                f"'var' não é permitido em parâmetro de construtor '{p.name}' (JLS §8.8.1 / §14.4).",
                                getattr(p, "line", member.line),
                            )
                        )
                    for ea in getattr(p, "ellipsis_annotations", []):
                        self._analyze_annotations([ea], valid_targets={"TYPE_USE"})
                    if p.name != "_":
                        p_type = self._resolve_param_effective_type(p)
                        self._register_local_var(
                            p.name,
                            p_type,
                            p.line,
                            is_final=("final" in getattr(p, "modifiers", [])),
                            has_initializer=True,
                            category="parametro",
                        )

            if member.body:
                if isinstance(member.body, ConstructorBody):
                    inv = member.body.constructor_invocation
                    self._flow_in_delegating_ctor = isinstance(inv, AlternateConstructorInvocation)
                    if is_enum and isinstance(inv, SuperclassConstructorInvocation):
                        self.errors.append(
                            SemanticError(f"Construtor de enum '{expected_name or member.name}' não pode conter invocação explícita 'super(...)' (JLS §8.9.2).", inv.line)
                        )
                    if inv is not None:
                        # 1. Prólogo (Early Construction Context - JLS §8.8.7 / JEP 513)
                        self._in_early_construction_context = True
                        try:
                            self._check_stmt_list_with_flow(member.body.prologue)
                        finally:
                            self._in_early_construction_context = False

                        # 2. Invocação explícita de construtor (argumentos no Early Construction Context)
                        self._in_early_construction_context = True
                        try:
                            for arg in inv.arguments:
                                self.check_expression(arg)
                        finally:
                            self._in_early_construction_context = False

                        self._emit_ctor_invocation_throws(ctor_owner, inv, member.line, is_enum=is_enum)

                        # 3. Epílogo (contexto normal com superclasse já inicializada)
                        self._check_stmt_list_with_flow(member.body.epilogue)
                    else:
                        self._emit_ctor_invocation_throws(ctor_owner, None, member.line, is_enum=is_enum)
                        self._check_stmt_list_with_flow(member.body.prologue)
                        self._check_stmt_list_with_flow(member.body.epilogue)
                    self._check_constructor_body_reachability(member.body)
                elif isinstance(member.body, Block):
                    self._emit_ctor_invocation_throws(ctor_owner, None, member.line, is_enum=is_enum)
                    self.analyze_block(member.body)
                    self._check_stmt_reachability(member.body, True)

            if self._flow_exit_frames and self._flow_exit_frames[-1] is ctor_frame:
                self._flow_exit_frames.pop()
            if not self._flow_in_delegating_ctor and self._flow_blank_final_fields:
                exit_states = list(ctor_frame.get("returns", []))
                if self._flow_reachable:
                    exit_states.append(self._flow_snapshot())
                joined_exit = self._flow_join_states(*exit_states) if exit_states else self._flow_unreachable()
                if joined_exit[2]:
                    for fn, fi in self._flow_blank_final_fields.items():
                        if not fi["is_static"] and fi["is_final"] and fi["vid"] not in joined_exit[0]:
                            self.errors.append(
                                SemanticError(
                                    f"O campo 'final' '{fn}' pode não ter sido inicializado no construtor '{member.name}' (JLS §8.3.1.2 / §16.9).",
                                    getattr(member, "line", fi["line"]),
                                )
                            )
            self._check_lambda_capture_boundaries()
        finally:
            if pushed_exc_frame:
                self._exception_analyzer.pop_callable_frame()
            self._restore_exec_context(saved_ctx)
            self.symbols.exit_scope()

    def _collect_blank_final_fields(
        self,
        members: List[ASTNode],
        enclosing_name: str,
    ) -> Tuple[Set[Any], Set[Any], Set[Any], Set[Any]]:
        """Mapeia campos 'final' do tipo atual para rastreamento DA/DU distinto de variáveis locais (JLS §16.8 / §16.9)."""
        field_map: Dict[str, Dict[str, Any]] = {}
        inst_da: Set[Any] = set()
        inst_du: Set[Any] = set()
        static_da: Set[Any] = set()
        static_du: Set[Any] = set()
        for member in members:
            if not isinstance(member, FieldDeclaration):
                continue
            is_static = "static" in getattr(member, "modifiers", [])
            is_final = "final" in getattr(member, "modifiers", [])
            if not is_final:
                continue
            decls = member.declarators if hasattr(member, "declarators") and member.declarators else []
            pairs: List[Tuple[str, bool, int]] = []
            if not decls and hasattr(member, "name"):
                pairs.append((member.name, member.initializer is not None, getattr(member, "line", 1)))
            else:
                for decl in decls:
                    pairs.append((decl.name, decl.initializer is not None, getattr(decl, "line", member.line)))
            for fname, has_init, fline in pairs:
                if not fname or fname == "_":
                    continue
                vid = ("field", enclosing_name, fname)
                field_map[fname] = {
                    "vid": vid,
                    "is_static": is_static,
                    "is_final": True,
                    "has_initializer": has_init,
                    "line": fline,
                }
                if is_static:
                    (static_da if has_init else static_du).add(vid)
                else:
                    (inst_da if has_init else inst_du).add(vid)
        self._flow_blank_final_fields = field_map
        return inst_da, inst_du, static_da, static_du

    def _analyze_class_like_members(
        self,
        members: List[ASTNode],
        container_label: str,
        enclosing_name: str,
        allow_constructor: bool = True,
        is_enum: bool = False,
        anon_inst_throws: Optional[List[Tuple[str, int, str]]] = None,
        anon_super_type: Optional[str] = None,
        owner_kind: str = "class",
        owner_modifiers: Optional[List[str]] = None,
        enum_const_impls: Optional[List[Tuple[str, Set[Tuple[str, int]]]]] = None,
        owner_line: int = 1,
    ):
        """Analisa membros comuns de classes, enums e corpos de constantes de enum."""
        inst_da, inst_du, static_da, static_du = self._collect_blank_final_fields(members, enclosing_name)
        inst_init_thrown: List[Tuple[str, int, str]] = []

        # Passo A: campos e blocos inicializadores na ordem textual (JLS §12.4.2)
        for member in members:
            if isinstance(member, FieldDeclaration):
                self._analyze_field_declaration(
                    member,
                    container_label=container_label,
                    collected_inst_throws=inst_init_thrown,
                )
            elif isinstance(member, (InstanceInitializer, StaticInitializer)):
                if member.block:
                    is_stat_init = isinstance(member, StaticInitializer)
                    saved_ctx = self._enter_exec_context(
                        "initializer",
                        return_type=None,
                        is_static=is_stat_init,
                    )
                    self._exception_analyzer.push_callable_frame(
                        "initializer",
                        "inicializador estático" if is_stat_init else "inicializador de instância",
                        allowed_throws=[],
                        enforce_unreported=is_stat_init,
                    )
                    try:
                        for fn, fi in self._flow_blank_final_fields.items():
                            self._flow_tracked[fi["vid"]] = {"name": fn, "is_final": True, "kind": "field", "line": fi["line"]}
                        if is_stat_init:
                            self._flow_da = set(static_da)
                            self._flow_du = set(static_du)
                        else:
                            self._flow_da = set(inst_da | static_da)
                            self._flow_du = set(inst_du)
                        self.analyze_block(member.block)
                        self._check_stmt_reachability(member.block, True)
                        self._check_lambda_capture_boundaries()
                        if self._flow_reachable:
                            if is_stat_init:
                                static_da = {v for v in self._flow_da if isinstance(v, tuple) and v[0] == "field"} & (static_da | static_du) | (self._flow_da & {fi["vid"] for fi in self._flow_blank_final_fields.values() if fi["is_static"]})
                                static_du = self._flow_du & {fi["vid"] for fi in self._flow_blank_final_fields.values() if fi["is_static"]}
                            else:
                                inst_vids = {fi["vid"] for fi in self._flow_blank_final_fields.values() if not fi["is_static"]}
                                inst_da = self._flow_da & inst_vids
                                inst_du = self._flow_du & inst_vids
                    finally:
                        popped = self._exception_analyzer.pop_callable_frame()
                        if (not is_stat_init) and popped is not None:
                            inst_init_thrown.extend(popped.get("thrown", []))
                        self._restore_exec_context(saved_ctx)

        if anon_inst_throws is not None:
            anon_inst_throws.extend(inst_init_thrown)
        elif inst_init_thrown:
            non_del_ctors = [
                m for m in members
                if isinstance(m, ConstructorDeclaration)
                and not (
                    isinstance(getattr(m, "body", None), ConstructorBody)
                    and isinstance(m.body.constructor_invocation, AlternateConstructorInvocation)
                )
            ]
            for exc_t, exc_ln, exc_desc in inst_init_thrown:
                if not non_del_ctors:
                    self.errors.append(
                        SemanticError(
                            f"Exceção verificada não reportada '{exc_t}' em {exc_desc}; construtor padrão implícito de '{enclosing_name}' não declara compatibilidade em 'throws' (JLS §8.3.2 / §8.6).",
                            exc_ln,
                        )
                    )
                else:
                    for ctor in non_del_ctors:
                        c_throws = [
                            self._normalize_type_str(t)
                            for t in (getattr(ctor, "throws_types", []) or [])
                            if self._normalize_type_str(t)
                        ]
                        if self._exception_analyzer.is_covered_by(exc_t, c_throws) is False:
                            self.errors.append(
                                SemanticError(
                                    f"Exceção verificada não reportada '{exc_t}' em {exc_desc}; construtor '{ctor.name}' (linha {ctor.line}) deve declarar compatibilidade em 'throws' (JLS §8.3.2 / §8.6).",
                                    exc_ln,
                                )
                            )
                            break

        # Valida campos 'static final' blank não inicializados por nenhum inicializador estático
        for fn, fi in self._flow_blank_final_fields.items():
            if fi["is_static"] and not fi["has_initializer"] and fi["vid"] not in static_da:
                self.errors.append(
                    SemanticError(
                        f"O campo 'static final' '{fn}' pode não ter sido inicializado (JLS §8.3.1.2 / §16.8).",
                        fi["line"],
                    )
                )

        # Passo B: construtores, métodos e tipos aninhados
        ctor_count = 0
        ctor_members: List[ASTNode] = []
        seed_flow = (inst_da | static_da, inst_du | static_du)
        eff_method_owner = anon_super_type if anon_super_type else (self._inheritance_analyzer.current_enclosing_key() or enclosing_name)
        for member in members:
            if isinstance(member, (EmptyStatement, FieldDeclaration, InstanceInitializer, StaticInitializer)):
                continue
            elif isinstance(member, MethodDeclaration):
                self._analyze_method_member(
                    member,
                    owner_type=eff_method_owner,
                    is_anonymous=bool(anon_super_type),
                    owner_kind=owner_kind,
                    owner_modifiers=owner_modifiers,
                )
            elif isinstance(member, ConstructorDeclaration):
                if not allow_constructor:
                    self.errors.append(
                        SemanticError(f"Corpo específico de constante de enum '{enclosing_name}' não pode declarar construtores (JLS §8.9.1).", member.line)
                    )
                else:
                    ctor_count += 1
                    ctor_members.append(member)
                    self._analyze_constructor_member(
                        member,
                        expected_name=enclosing_name if is_enum else None,
                        is_enum=is_enum,
                        seed_flow=seed_flow,
                    )
            elif isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                self._analyze_type_declaration(member, is_nested=True, is_local=False)

        if ctor_members:
            self._inheritance_analyzer.validate_constructor_cycles(enclosing_name, ctor_members)

        if container_label != "corpo de constante de enum":
            self._inheritance_analyzer.validate_type_inherited_methods(
                eff_method_owner,
                owner_kind=owner_kind,
                owner_modifiers=owner_modifiers or [],
                members=members,
                line=owner_line,
                is_anonymous=bool(anon_super_type),
                enum_const_impls=enum_const_impls,
            )

        if ctor_count == 0:
            if (not is_enum) and (not anon_super_type) and allow_constructor:
                tdecl_cls = self._lookup_type_decl(enclosing_name)
                cls_line = getattr(tdecl_cls[1], "line", 1) if tdecl_cls else 1
                self._exception_analyzer.push_callable_frame(
                    "constructor",
                    f"construtor padrão implícito de '{enclosing_name}'",
                    allowed_throws=[],
                    enforce_unreported=True,
                )
                try:
                    self._emit_ctor_invocation_throws(enclosing_name, None, cls_line, is_enum=False)
                finally:
                    self._exception_analyzer.pop_callable_frame()
            for fn, fi in self._flow_blank_final_fields.items():
                if not fi["is_static"] and not fi["has_initializer"] and fi["vid"] not in inst_da:
                    self.errors.append(
                        SemanticError(
                            f"O campo 'final' '{fn}' pode não ter sido inicializado (JLS §8.3.1.2 / §16.9).",
                            fi["line"],
                        )
                    )

    def _register_local_type_conflict(self, name: str, kind_label: str, line: int, is_local: bool):
        """Verifica duplicidade de declarações de tipos locais e colisão com tipo envolvente (JLS §14.3)."""
        if not is_local:
            return
        # _analyze_type_declaration já empilhou `name` no topo de _enclosing_type_names; verifica apenas ancestrais
        if name in self._enclosing_type_names[:-1]:
            self.errors.append(
                SemanticError(
                    f"{kind_label} '{name}' não pode possuir o mesmo nome de um tipo envolvente (JLS §8.1 / §14.3).",
                    line,
                )
            )
            return
        if not self._local_type_scopes:
            return
        for scope in reversed(self._local_type_scopes):
            if name in scope:
                self.errors.append(
                    SemanticError(
                        f"{kind_label} '{name}' declarada novamente no mesmo escopo local ou escopo envolvente (linha {scope[name]}).",
                        line,
                    )
                )
                return
        self._local_type_scopes[-1][name] = line

    def _enter_type_body_context(
        self,
        node: ASTNode,
        is_nested: bool = False,
        is_local: bool = False,
        implicitly_static_when_nested: bool = False,
    ) -> Dict[str, Any]:
        """Entra no escopo de corpo de tipo isolando contextos estáticos e empilhando type parameters."""
        was_in_static = self._in_static_context
        mods = getattr(node, "modifiers", []) or []
        is_static_nested = is_nested and (implicitly_static_when_nested or ("static" in mods))
        self.symbols.enter_scope()
        saved_ctx = self._enter_exec_context("type_body", return_type=None, is_static=False)
        if is_static_nested:
            self._active_type_params = []
        elif is_local and was_in_static:
            self._active_type_params = [
                (m, is_tl) for (m, is_tl) in self._active_type_params if not is_tl
            ]
        self._push_type_params(getattr(node, "type_parameters", []), is_type_level=True)
        return saved_ctx

    def analyze_class(self, cls_node: ClassDeclaration, is_nested: bool = False, is_local: bool = False):
        """Registra a classe e seus membros (campos, métodos, construtores e tipos aninhados)."""
        self._register_local_type_conflict(cls_node.name, "Classe local", cls_node.line, is_local)
        self._declare_type_symbol(cls_node.name, "classe", "classe", "Classe", cls_node.line)
        self._validate_type_modifiers(
            cls_node.modifiers,
            "classe",
            cls_node.name,
            cls_node.line,
            is_nested=is_nested,
            is_local=is_local,
        )
        self._analyze_annotations(getattr(cls_node, "annotations", []), valid_targets={"TYPE"})
        self._check_functional_interface_annotation(cls_node, is_interface=False)

        saved_ctx = self._enter_type_body_context(cls_node, is_nested=is_nested, is_local=is_local, implicitly_static_when_nested=False)
        try:
            self._check_type_parameters_annotations(getattr(cls_node, "type_parameters", []))
            if getattr(cls_node, "extends_type", None) is not None:
                self._check_type_ref_annotations(cls_node.extends_type)
            for itype in getattr(cls_node, "implements_types", []):
                self._check_type_ref_annotations(itype)
            for ptype in getattr(cls_node, "permits_types", []):
                self._check_type_ref_annotations(ptype)

            cur_key = self._inheritance_analyzer.current_enclosing_key() or cls_node.name
            self._inheritance_analyzer.validate_type_hierarchy(cls_node, cur_key)
            self._analyze_class_like_members(
                cls_node.members,
                container_label="classe",
                enclosing_name=cls_node.name,
                allow_constructor=True,
                is_enum=False,
                owner_kind="class",
                owner_modifiers=cls_node.modifiers,
                owner_line=cls_node.line,
            )
        finally:
            self._restore_exec_context(saved_ctx)
            self.symbols.exit_scope()

    def analyze_interface(self, iface_node: InterfaceDeclaration, is_nested: bool = False, is_local: bool = False):
        """Valida declarações e membros de interface segundo JLS §9.1–§9.5."""
        self._register_local_type_conflict(iface_node.name, "Interface local", iface_node.line, is_local)
        self._declare_type_symbol(iface_node.name, "interface", "interface", "Interface", iface_node.line)
        self._validate_type_modifiers(iface_node.modifiers, "interface", iface_node.name, iface_node.line, is_nested=is_nested, is_local=is_local)
        self._analyze_annotations(getattr(iface_node, "annotations", []), valid_targets={"TYPE"})
        self._check_functional_interface_annotation(iface_node, is_interface=True)
        saved_ctx = self._enter_type_body_context(iface_node, is_nested=is_nested, is_local=is_local, implicitly_static_when_nested=True)
        try:
            self._check_type_parameters_annotations(getattr(iface_node, "type_parameters", []))
            for etype in getattr(iface_node, "extends_types", []):
                self._check_type_ref_annotations(etype)
            for ptype in getattr(iface_node, "permits_types", []):
                self._check_type_ref_annotations(ptype)
            cur_key = self._inheritance_analyzer.current_enclosing_key() or iface_node.name
            self._inheritance_analyzer.validate_type_hierarchy(iface_node, cur_key)
            allowed_const_mods = {"public", "static", "final"}
            forbidden_method_mods = {"protected", "final", "synchronized", "native"}

            for member in iface_node.members:
                if isinstance(member, EmptyStatement):
                    continue

                elif isinstance(member, (InterfaceConstantDeclaration, FieldDeclaration)):
                    for mod in member.modifiers:
                        if mod not in allowed_const_mods:
                            self.errors.append(
                                SemanticError(f"Modificador '{mod}' inválido em constante da interface '{iface_node.name}' (JLS §9.3).", member.line)
                            )
                    self._analyze_field_declaration(member, container_label="interface", is_interface_constant=True)

                elif isinstance(member, (InterfaceMethodDeclaration, MethodDeclaration)):
                    mset = set(member.modifiers)
                    self._check_conflicting_access_modifiers(member.modifiers, f"método '{member.name}' de interface", member.line)
                    for bad in member.modifiers:
                        if bad in forbidden_method_mods:
                            self.errors.append(
                                SemanticError(f"Modificador '{bad}' não é permitido em método de interface '{member.name}' (JLS §9.4).", member.line)
                            )
                    if "default" in mset and "static" in mset:
                        self.errors.append(SemanticError(f"Método de interface '{member.name}' não pode combinar 'default' e 'static' (JLS §9.4).", member.line))
                    if "default" in mset and "abstract" in mset:
                        self.errors.append(SemanticError(f"Método de interface '{member.name}' não pode combinar 'default' e 'abstract' (JLS §9.4).", member.line))
                    if "static" in mset and "abstract" in mset:
                        self.errors.append(SemanticError(f"Método de interface '{member.name}' não pode combinar 'static' e 'abstract' (JLS §9.4).", member.line))
                    if "private" in mset:
                        for clash in ("default", "abstract"):
                            if clash in mset:
                                self.errors.append(SemanticError(f"Método 'private' em interface '{member.name}' não pode ser '{clash}' (JLS §9.4).", member.line))

                    if "abstract" in mset and member.body is not None:
                        self.errors.append(SemanticError(f"Método 'abstract' em interface '{member.name}' não pode possuir corpo (JLS §9.4).", member.line))
                    if any(m in mset for m in ("default", "static", "private")) and member.body is None:
                        self.errors.append(SemanticError(f"Método '{member.name}' ('default', 'static' ou 'private') em interface deve possuir corpo (JLS §9.4).", member.line))

                    self._analyze_method_member(
                        member,
                        owner_type=cur_key,
                        owner_kind="interface",
                        owner_modifiers=iface_node.modifiers,
                    )

                elif isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                    self._analyze_type_declaration(member, is_nested=True, is_local=False)

                elif isinstance(member, (ConstructorDeclaration, InstanceInitializer, StaticInitializer)):
                    self.errors.append(
                        SemanticError(f"Interface '{iface_node.name}' não pode declarar construtores ou blocos inicializadores (JLS §9.1.4).", member.line)
                    )

            self._inheritance_analyzer.validate_type_inherited_methods(
                cur_key,
                owner_kind="interface",
                owner_modifiers=iface_node.modifiers,
                members=iface_node.members,
                line=iface_node.line,
            )
        finally:
            self._restore_exec_context(saved_ctx)
            self.symbols.exit_scope()

    def analyze_enum(self, enum_node: EnumDeclaration, is_nested: bool = False, is_local: bool = False):
        """Valida declarações de enum, constantes, corpos de constantes, métodos abstratos e membros (JLS §8.9)."""
        self._register_local_type_conflict(enum_node.name, "Enum local", enum_node.line, is_local)
        self._enums[enum_node.name] = enum_node
        self._declare_type_symbol(enum_node.name, "enum", "enum", "Enum", enum_node.line)
        self._validate_type_modifiers(enum_node.modifiers, "enum", enum_node.name, enum_node.line, is_nested=is_nested, is_local=is_local)
        self._analyze_annotations(getattr(enum_node, "annotations", []), valid_targets={"TYPE"})
        self._check_functional_interface_annotation(enum_node, is_interface=False)
        saved_ctx = self._enter_type_body_context(enum_node, is_nested=is_nested, is_local=is_local, implicitly_static_when_nested=True)
        try:
            for itype in getattr(enum_node, "implements_types", []):
                self._check_type_ref_annotations(itype)
            cur_key = self._inheritance_analyzer.current_enclosing_key() or enum_node.name
            self._inheritance_analyzer.validate_type_hierarchy(enum_node, cur_key)
            # Métodos abstratos declarados diretamente no corpo do enum (JLS §8.9.1)
            abstract_methods = [
                m for m in enum_node.members
                if isinstance(m, MethodDeclaration) and "abstract" in getattr(m, "modifiers", [])
            ]
            if abstract_methods and not enum_node.constants:
                for am in abstract_methods:
                    self.errors.append(
                        SemanticError(
                            f"Enum '{enum_node.name}' declara método abstrato '{am.name}' mas não possui constantes que o implementem (JLS §8.9).",
                            am.line,
                        )
                    )

            enum_ctors = [
                self._extract_method_sig(m, enum_node.name, owner_kind="enum")
                for m in enum_node.members
                if isinstance(m, ConstructorDeclaration)
            ]
            enum_const_impls: List[Tuple[str, Set[Tuple[str, int]]]] = []
            for const in enum_node.constants:
                self._analyze_annotations(getattr(const, "annotations", []), valid_targets={"FIELD"})
                if const.name == "_":
                    self.errors.append(SemanticError("O identificador '_' não pode ser utilizado como nome de constante de enum.", const.line))
                elif not self.symbols.declare(const.name, enum_node.name, const.line, category="constante_enum", is_static=True, is_final=True, is_compile_constant=True):
                    self.errors.append(SemanticError(f"Constante de enum '{const.name}' declarada novamente em '{enum_node.name}'.", const.line))

                self._exception_analyzer.push_callable_frame(
                    "initializer",
                    f"constante de enum '{const.name}'",
                    [],
                    enforce_unreported=True,
                )
                try:
                    for arg in const.arguments:
                        self.check_expression(arg)
                    for ecs in enum_ctors:
                        eparams = ecs.get("params", [])
                        arity_ok = (
                            len(eparams) == len(const.arguments)
                            or (ecs.get("varargs") and len(const.arguments) >= max(0, len(eparams) - 1))
                        )
                        if arity_ok:
                            self._exception_analyzer.emit_thrown(
                                ecs.get("throws", []),
                                const.line,
                                f"construtor de constante de enum '{const.name}'",
                            )
                finally:
                    self._exception_analyzer.pop_callable_frame()

                const_impl_sigs: Set[Tuple[str, int]] = set()
                if isinstance(const.body, EnumConstantBody):
                    for cm in const.body.members:
                        if isinstance(cm, MethodDeclaration) and "abstract" not in getattr(cm, "modifiers", []) and cm.body is not None:
                            const_impl_sigs.add((cm.name, len(cm.parameters)))
                    self.symbols.enter_scope()
                    self._analyze_class_like_members(
                        const.body.members,
                        container_label="corpo de constante de enum",
                        enclosing_name=const.name,
                        allow_constructor=False,
                        is_enum=False,
                        anon_super_type=cur_key,
                        owner_kind="class",
                        owner_modifiers=[],
                        owner_line=const.line,
                    )
                    self.symbols.exit_scope()
                enum_const_impls.append((const.name, const_impl_sigs))

                for am in abstract_methods:
                    if (am.name, len(am.parameters)) not in const_impl_sigs:
                        self.errors.append(
                            SemanticError(
                                f"Constante de enum '{const.name}' em '{enum_node.name}' deve implementar o método abstrato '{am.name}' (JLS §8.9).",
                                const.line,
                            )
                        )

            self._analyze_class_like_members(
                enum_node.members,
                container_label="enum",
                enclosing_name=enum_node.name,
                allow_constructor=True,
                is_enum=True,
                owner_kind="enum",
                owner_modifiers=enum_node.modifiers,
                enum_const_impls=enum_const_impls,
                owner_line=enum_node.line,
            )
        finally:
            self._restore_exec_context(saved_ctx)
            self.symbols.exit_scope()

    def analyze_record(self, rec_node: RecordDeclaration, is_nested: bool = False, is_local: bool = False):
        """Valida declarações de records, componentes, assessores explícitos e construtores (JLS §8.10)."""
        self._register_local_type_conflict(rec_node.name, "Record local", rec_node.line, is_local)
        self._declare_type_symbol(rec_node.name, "record", "record", "Record", rec_node.line)
        self._validate_type_modifiers(rec_node.modifiers, "record", rec_node.name, rec_node.line, is_nested=is_nested, is_local=is_local)
        self._analyze_annotations(getattr(rec_node, "annotations", []), valid_targets={"TYPE"})
        self._check_functional_interface_annotation(rec_node, is_interface=False)
        saved_ctx = self._enter_type_body_context(rec_node, is_nested=is_nested, is_local=is_local, implicitly_static_when_nested=True)
        try:
            self._check_type_parameters_annotations(getattr(rec_node, "type_parameters", []))
            for itype in getattr(rec_node, "implements_types", []):
                self._check_type_ref_annotations(itype)
            cur_key = self._inheritance_analyzer.current_enclosing_key() or rec_node.name
            self._inheritance_analyzer.validate_type_hierarchy(rec_node, cur_key)
            rec_ctor_members: List[ASTNode] = []
            seen_components: Set[str] = set()
            comp_by_name: Dict[str, RecordComponent] = {}
            for comp in rec_node.components:
                self._analyze_annotations(
                    getattr(comp, "annotations", []),
                    valid_targets={"RECORD_COMPONENT", "FIELD", "METHOD", "PARAMETER"},
                    adjacent_type_ref=getattr(comp, "type_ref", None),
                )
                self._check_type_ref_annotations(getattr(comp, "type_ref", None))
                if getattr(comp, "type_ref", None) is not None and getattr(comp.type_ref, "name", None) == "var":
                    self.errors.append(
                        SemanticError(f"'var' não é permitido em componente de record '{comp.name}' (JLS §8.10.1 / §14.4).", comp.line)
                    )
                for ea in getattr(comp, "ellipsis_annotations", []):
                    self._analyze_annotations([ea], valid_targets={"TYPE_USE"})
                if comp.name == "_":
                    self.errors.append(
                        SemanticError("O identificador '_' não pode ser utilizado como nome de componente de record (JLS §8.10.1).", comp.line)
                    )
                elif comp.name in self.FORBIDDEN_RECORD_COMPONENTS:
                    self.errors.append(
                        SemanticError(f"Nome de componente de record inválido: '{comp.name}' conflita com método reservado de java.lang.Object (JLS §8.10.1).", comp.line)
                    )
                elif comp.name in seen_components:
                    self.errors.append(
                        SemanticError(f"Componente de record '{comp.name}' declarado novamente em '{rec_node.name}' (JLS §8.10.1).", comp.line)
                    )
                else:
                    seen_components.add(comp.name)
                    comp_by_name[comp.name] = comp
                    self.symbols.declare(comp.name, comp.effective_type, comp.line, category="componente_record")

            rec_access = self._effective_access(rec_node.modifiers)
            canonical_ctors = 0

            for member in rec_node.members:
                if isinstance(member, EmptyStatement):
                    continue

                elif isinstance(member, FieldDeclaration):
                    if "static" not in member.modifiers:
                        self.errors.append(
                            SemanticError(f"Records não podem declarar campos de instância; apenas campos 'static' são permitidos em '{rec_node.name}' (JLS §8.10.2).", member.line)
                        )
                    self._analyze_field_declaration(member, container_label="record")

                elif isinstance(member, InstanceInitializer):
                    self.errors.append(
                        SemanticError(f"Records não podem declarar inicializadores de instância em '{rec_node.name}' (JLS §8.10.2).", member.line)
                    )
                    if member.block:
                        init_ctx = self._enter_exec_context("initializer", return_type=None, is_static=False)
                        try:
                            self.analyze_block(member.block)
                            self._check_stmt_reachability(member.block, True)
                            self._check_lambda_capture_boundaries()
                        finally:
                            self._restore_exec_context(init_ctx)

                elif isinstance(member, StaticInitializer):
                    if member.block:
                        init_ctx = self._enter_exec_context("initializer", return_type=None, is_static=True)
                        try:
                            self.analyze_block(member.block)
                            self._check_stmt_reachability(member.block, True)
                            self._check_lambda_capture_boundaries()
                        finally:
                            self._restore_exec_context(init_ctx)

                elif isinstance(member, MethodDeclaration):
                    for bad in ("abstract", "native"):
                        if bad in member.modifiers:
                            self.errors.append(
                                SemanticError(f"Método '{member.name}' do record '{rec_node.name}' não pode possuir modificador '{bad}' (JLS §8.10.2).", member.line)
                            )
                    if member.body is None and not any(m in member.modifiers for m in ("abstract", "native")):
                        self.errors.append(
                            SemanticError(f"Método '{member.name}' do record '{rec_node.name}' deve possuir corpo.", member.line)
                        )
                    if member.name in comp_by_name and len(member.parameters) == 0:
                        comp = comp_by_name[member.name]
                        if "static" in member.modifiers:
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' não pode ser 'static' (JLS §8.10.3).", member.line)
                            )
                        if "public" not in member.modifiers:
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' deve ser declarado como 'public' (JLS §8.10.3).", member.line)
                            )
                        if getattr(member, "type_parameters", None):
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' não pode declarar parâmetros de tipo genérico (JLS §8.10.3).", member.line)
                            )
                        if getattr(member, "throws_types", None):
                            self.errors.append(
                                SemanticError(f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' não pode possuir cláusula 'throws' (JLS §8.10.3).", member.line)
                            )
                        expected_ret = comp.effective_type.replace("...", "[]")
                        if member.effective_return_type != expected_ret:
                            self.errors.append(
                                SemanticError(
                                    f"Método acessor explícito '{member.name}()' do record '{rec_node.name}' deve retornar '{expected_ret}' (encontrado '{member.effective_return_type}' — JLS §8.10.3).",
                                    member.line,
                                )
                            )
                    self._analyze_method_member(
                        member,
                        owner_type=cur_key,
                        owner_kind="record",
                        owner_modifiers=rec_node.modifiers,
                    )

                elif isinstance(member, CompactConstructorDeclaration):
                    canonical_ctors += 1
                    rec_ctor_members.append(member)
                    if canonical_ctors > 1:
                        self.errors.append(
                            SemanticError(f"Record '{rec_node.name}' possui múltiplos construtores canônicos declarados (JLS §8.10.4).", member.line)
                        )
                    if self._effective_access(member.modifiers) < rec_access:
                        self.errors.append(
                            SemanticError(f"Construtor canônico compacto de '{rec_node.name}' não pode possuir visibilidade mais restrita que a do record (JLS §8.10.4).", member.line)
                        )
                    if getattr(member, "type_parameters", None):
                        self.errors.append(SemanticError("Construtor compacto de record não pode declarar type parameters (JLS §8.10.4.2).", member.line))
                    if getattr(member, "throws_types", None):
                        self.errors.append(SemanticError("Construtor compacto de record não pode possuir cláusula 'throws' (JLS §8.10.4.2).", member.line))
                    if isinstance(member.body, ConstructorBody) and member.body.constructor_invocation is not None:
                        inv_line = getattr(member.body.constructor_invocation, "line", member.line)
                        self.errors.append(
                            SemanticError("Construtor compacto de record não pode conter invocação explícita 'this(...)' ou 'super(...)' (JLS §8.10.4.2).", inv_line)
                        )
                    self._analyze_constructor_member(
                        member,
                        expected_name=rec_node.name,
                        is_compact=True,
                        derived_components=rec_node.components,
                    )

                elif isinstance(member, NormalCanonicalConstructor):
                    canonical_ctors += 1
                    rec_ctor_members.append(member)
                    if canonical_ctors > 1:
                        self.errors.append(
                            SemanticError(f"Record '{rec_node.name}' possui múltiplos construtores canônicos declarados (JLS §8.10.4).", member.line)
                        )
                    if self._effective_access(member.modifiers) < rec_access:
                        self.errors.append(
                            SemanticError(f"Construtor canônico normal de '{rec_node.name}' não pode possuir visibilidade mais restrita que a do record (JLS §8.10.4).", member.line)
                        )
                    if getattr(member, "type_parameters", None):
                        self.errors.append(SemanticError("Construtor canônico de record não pode declarar type parameters (JLS §8.10.4.1).", member.line))
                    if getattr(member, "throws_types", None):
                        self.errors.append(SemanticError("Construtor canônico de record não pode possuir cláusula 'throws' (JLS §8.10.4.1).", member.line))
                    if getattr(member, "receiver_parameter", None):
                        self.errors.append(SemanticError("Construtor canônico de record não pode declarar receiver parameter (JLS §8.10.4.1).", member.line))
                    if isinstance(member.body, ConstructorBody) and member.body.constructor_invocation is not None:
                        inv_line = getattr(member.body.constructor_invocation, "line", member.line)
                        self.errors.append(
                            SemanticError("Construtor canônico normal de record não pode conter invocação explícita 'this(...)' ou 'super(...)' (JLS §8.10.4.1).", inv_line)
                        )
                    if len(member.parameters) == len(rec_node.components):
                        for param, comp in zip(member.parameters, rec_node.components):
                            if param.name != comp.name:
                                self.errors.append(
                                    SemanticError(
                                        f"Parâmetro '{param.name}' do construtor canônico deve possuir o mesmo nome do componente '{comp.name}' do record '{rec_node.name}' (JLS §8.10.4.1).",
                                        param.line,
                                    )
                                )
                    self._analyze_constructor_member(member, expected_name=rec_node.name, is_compact=False)

                elif isinstance(member, NonCanonicalRecordConstructor):
                    rec_ctor_members.append(member)
                    inv = member.body.constructor_invocation if isinstance(member.body, ConstructorBody) else None
                    if isinstance(inv, SuperclassConstructorInvocation):
                        self.errors.append(
                            SemanticError(f"Construtor não canônico do record '{rec_node.name}' não pode invocar 'super(...)'; deve delegar via 'this(...)' (JLS §8.10.4).", inv.line)
                        )
                    elif not isinstance(inv, AlternateConstructorInvocation):
                        self.errors.append(
                            SemanticError(
                                f"Construtor não canônico do record '{rec_node.name}' deve iniciar com invocação explícita 'this(...)' (ou corresponder exatamente aos componentes e varargs do record — JLS §8.10.4).",
                                member.line,
                            )
                        )
                    self._analyze_constructor_member(member, expected_name=rec_node.name, is_compact=False)

                elif isinstance(member, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                    self._analyze_type_declaration(member, is_nested=True, is_local=False)

            if rec_ctor_members:
                self._inheritance_analyzer.validate_constructor_cycles(rec_node.name, rec_ctor_members)
            self._inheritance_analyzer.validate_type_inherited_methods(
                cur_key,
                owner_kind="record",
                owner_modifiers=rec_node.modifiers,
                members=rec_node.members,
                line=rec_node.line,
            )
        finally:
            self._restore_exec_context(saved_ctx)
            self.symbols.exit_scope()

    # =========================================================================
    # ANOTAÇÕES E ANNOTATION INTERFACES (ETAPA S5 — JLS §9.6, §9.7)
    # =========================================================================
    def analyze_annotation_interface(
        self,
        ann_node: AnnotationInterfaceDeclaration,
        is_nested: bool = False,
        is_local: bool = False,
    ):
        """Valida declaração de @interface, elementos, valores default e meta-anotações (JLS §9.6)."""
        if is_local:
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode ser declarada localmente dentro de bloco ou método (JLS §9.6 / §14.3).",
                    ann_node.line,
                )
            )
            return

        self._declare_type_symbol(
            ann_node.name, "annotation_interface", "annotation_interface", "Annotation interface", ann_node.line
        )
        self._validate_type_modifiers(
            ann_node.modifiers,
            "annotation_interface",
            ann_node.name,
            ann_node.line,
            is_nested=is_nested,
            is_local=is_local,
        )

        if getattr(ann_node, "type_parameters", None):
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode declarar parâmetros de tipo genérico (JLS §9.6).",
                    ann_node.line,
                )
            )
        if getattr(ann_node, "extends_types", None):
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode possuir cláusula 'extends' (JLS §9.6).",
                    ann_node.line,
                )
            )
        if getattr(ann_node, "permits_types", None):
            self.errors.append(
                SemanticError(
                    f"Annotation interface '@{ann_node.name}' não pode possuir cláusula 'permits' (JLS §9.6).",
                    ann_node.line,
                )
            )

        self._analyze_annotations(
            getattr(ann_node, "annotations", []),
            valid_targets={"ANNOTATION_TYPE", "TYPE"},
        )
        self._validate_repeatable_declaration(ann_node)

        self.symbols.enter_scope()
        allowed_const_mods = {"public", "static", "final"}
        allowed_elem_mods = {"public", "abstract"}
        seen_elements: Set[str] = set()

        for member in ann_node.members:
            if isinstance(member, EmptyStatement):
                continue

            elif isinstance(member, AnnotationInterfaceElementDeclaration):
                self._analyze_annotations(
                    getattr(member, "annotations", []),
                    valid_targets={"METHOD"},
                    adjacent_type_ref=member.effective_return_type_ref,
                )
                self._check_type_ref_annotations(member.return_type)
                for da in getattr(member, "dims_annotations", []):
                    self._analyze_annotations(da, valid_targets={"TYPE_USE"})

                self._check_conflicting_access_modifiers(
                    member.modifiers, f"elemento '{member.name}' de '@{ann_node.name}'", member.line
                )
                for mod in member.modifiers:
                    if mod not in allowed_elem_mods:
                        self.errors.append(
                            SemanticError(
                                f"Modificador '{mod}' não é permitido em elemento de '@interface' ('{member.name}' em '@{ann_node.name}' — JLS §9.6.1).",
                                member.line,
                            )
                        )
                if getattr(member, "parameters", None):
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' de '@{ann_node.name}' não pode possuir parâmetros formais (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if getattr(member, "throws_types", None):
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' de '@{ann_node.name}' não pode declarar 'throws' (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if getattr(member, "body", None) is not None:
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' de '@{ann_node.name}' não pode possuir corpo de implementação (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if member.name in self.FORBIDDEN_ANNOTATION_ELEMENTS:
                    self.errors.append(
                        SemanticError(
                            f"Nome de elemento inválido em '@{ann_node.name}': '{member.name}' conflita com método de java.lang.Object ou Annotation (JLS §9.6.1).",
                            member.line,
                        )
                    )
                if member.name in seen_elements:
                    self.errors.append(
                        SemanticError(
                            f"Elemento '{member.name}' declarado novamente na annotation interface '@{ann_node.name}'.",
                            member.line,
                        )
                    )
                else:
                    seen_elements.add(member.name)

                self._validate_annotation_element_return_type(member, ann_node.name)
                self.symbols.declare(
                    member.name,
                    member.effective_return_type,
                    member.line,
                    category="elemento_anotacao",
                )

                if member.default_value is not None:
                    ev = member.default_value.value
                    self._validate_element_value(
                        ev,
                        expected_type=member.effective_return_type,
                        owner_desc=f"valor default de '{member.name}' em '@{ann_node.name}'",
                    )

            elif isinstance(member, (InterfaceConstantDeclaration, FieldDeclaration)):
                for mod in member.modifiers:
                    if mod not in allowed_const_mods:
                        self.errors.append(
                            SemanticError(
                                f"Modificador '{mod}' inválido em constante da annotation interface '@{ann_node.name}' (JLS §9.6.1).",
                                member.line,
                            )
                        )
                self._analyze_field_declaration(
                    member, container_label="annotation interface", is_interface_constant=True
                )

            elif isinstance(member, MethodDeclaration):
                self.errors.append(
                    SemanticError(
                        f"Declaração de método '{member.name}' com parâmetros ou corpo não é permitida em '@{ann_node.name}' (JLS §9.6.1).",
                        member.line,
                    )
                )

            elif isinstance(
                member,
                (
                    ClassDeclaration,
                    InterfaceDeclaration,
                    EnumDeclaration,
                    RecordDeclaration,
                    AnnotationInterfaceDeclaration,
                ),
            ):
                self._analyze_type_declaration(member, is_nested=True, is_local=False)

            elif isinstance(member, (ConstructorDeclaration, InstanceInitializer, StaticInitializer)):
                self.errors.append(
                    SemanticError(
                        f"Annotation interface '@{ann_node.name}' não pode declarar construtores ou inicializadores (JLS §9.6.1).",
                        member.line,
                    )
                )

        self.symbols.exit_scope()

    def _validate_annotation_element_return_type(
        self,
        elem: AnnotationInterfaceElementDeclaration,
        owner_ann_name: str,
    ):
        """Valida tipos permitidos de elementos de annotation interface e ciclos (JLS §9.6.1)."""
        ret_ref = elem.effective_return_type_ref
        eff_str = elem.effective_return_type
        dims = ret_ref.array_dimensions
        raw_name = ret_ref.name
        base_name = raw_name.split(".")[-1]

        if dims > 1:
            self.errors.append(
                SemanticError(
                    f"Tipo de retorno '{eff_str}' inválido em elemento '{elem.name}' de '@{owner_ann_name}': arrays multidimensionais são proibidos (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if raw_name == "void":
            self.errors.append(
                SemanticError(
                    f"Tipo de retorno 'void' não é permitido no elemento '{elem.name}' de '@{owner_ann_name}' (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if ret_ref.type_arguments and base_name != "Class":
            self.errors.append(
                SemanticError(
                    f"Tipo parametrizado '{ret_ref.pretty()}' não é permitido no elemento '{elem.name}' de '@{owner_ann_name}'; apenas 'Class<...>' aceita argumentos de tipo (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if base_name == owner_ann_name:
            self.errors.append(
                SemanticError(
                    f"Referência cíclica proibida: elemento '{elem.name}' de '@{owner_ann_name}' referencia a própria annotation interface (JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if base_name in self._annotation_interfaces:
            if self._has_annotation_cycle(base_name, owner_ann_name, set()):
                self.errors.append(
                    SemanticError(
                        f"Referência cíclica indireta proibida entre '@{owner_ann_name}' e '@{base_name}' (JLS §9.6.1).",
                        elem.line,
                    )
                )
            return

        if raw_name in self.PRIMITIVE_TYPES or raw_name in ("String", "java.lang.String", "Class", "java.lang.Class"):
            return

        if raw_name in self.KNOWN_ENUM_TYPES or base_name in self._enums or base_name in self.BUILTIN_ANNOTATION_TYPES:
            return

        if base_name in self.DISALLOWED_ANNOTATION_RETURN_TYPES or raw_name in self.DISALLOWED_ANNOTATION_RETURN_TYPES:
            self.errors.append(
                SemanticError(
                    f"Tipo '{eff_str}' não é permitido para elemento '{elem.name}' de '@{owner_ann_name}' (apenas primitivos, String, Class, enum, annotation ou array unidimensional — JLS §9.6.1).",
                    elem.line,
                )
            )
            return

        if base_name in self._declared_types:
            kind, _ = self._declared_types[base_name]
            if kind in ("class", "interface", "record"):
                self.errors.append(
                    SemanticError(
                        f"Tipo '{eff_str}' ({kind}) não é permitido para elemento '{elem.name}' de '@{owner_ann_name}' (JLS §9.6.1).",
                        elem.line,
                    )
                )

    def _has_annotation_cycle(self, current_name: str, target_name: str, visited: Set[str]) -> bool:
        """Verifica se há ciclo de dependência entre annotation interfaces via seus elementos."""
        if current_name in visited:
            return False
        visited.add(current_name)
        ann_decl = self._annotation_interfaces.get(current_name)
        if not ann_decl:
            return False
        for el in ann_decl.elements:
            dep_base = el.return_type.name.split(".")[-1]
            if dep_base == target_name:
                return True
            if dep_base in self._annotation_interfaces and self._has_annotation_cycle(dep_base, target_name, visited):
                return True
        return False

    def _extract_target_elements(self, defn: AnnotationInterfaceDeclaration) -> Optional[Set[str]]:
        """Extrai o conjunto de ElementType declarados em @Target(...) ou None se ausente."""
        for ann in getattr(defn, "annotations", []):
            if ann.name.split(".")[-1] == "Target":
                vals: List[ElementValue] = []
                if isinstance(ann, SingleElementAnnotation) and ann.element_value is not None:
                    vals = [ann.element_value]
                elif isinstance(ann, NormalAnnotation):
                    for p in ann.pairs:
                        if p.name == "value":
                            vals = [p.value]
                            break
                if not vals:
                    return set()
                v0 = vals[0]
                items = v0.value.elements if isinstance(v0.value, ArrayInitializer) else [v0]
                targets: Set[str] = set()
                for item in items:
                    inner = item.value if isinstance(item, ElementValue) else item
                    if isinstance(inner, MemberAccess):
                        targets.add(inner.member_name)
                    elif isinstance(inner, Identifier):
                        targets.add(inner.name.split(".")[-1])
                return targets
        return None

    def _extract_retention_policy(self, defn: AnnotationInterfaceDeclaration) -> str:
        """Extrai a política de @Retention(...) (SOURCE, CLASS ou RUNTIME; padrão CLASS)."""
        for ann in getattr(defn, "annotations", []):
            if ann.name.split(".")[-1] == "Retention":
                val = None
                if isinstance(ann, SingleElementAnnotation):
                    val = ann.element_value
                elif isinstance(ann, NormalAnnotation):
                    for p in ann.pairs:
                        if p.name == "value":
                            val = p.value
                            break
                if val is not None:
                    inner = val.value if isinstance(val, ElementValue) else val
                    if isinstance(inner, MemberAccess):
                        return inner.member_name
                    if isinstance(inner, Identifier):
                        return inner.name.split(".")[-1]
        return "CLASS"

    def _extract_repeatable_container_name(self, defn: AnnotationInterfaceDeclaration) -> Optional[Tuple[str, int]]:
        """Retorna (NomeContainer, linha) se @interface possuir @Repeatable(Container.class)."""
        for ann in getattr(defn, "annotations", []):
            if ann.name.split(".")[-1] == "Repeatable":
                val = None
                if isinstance(ann, SingleElementAnnotation):
                    val = ann.element_value
                elif isinstance(ann, NormalAnnotation):
                    for p in ann.pairs:
                        if p.name == "value":
                            val = p.value
                            break
                if val is not None:
                    inner = val.value if isinstance(val, ElementValue) else val
                    if isinstance(inner, ClassLiteral):
                        return inner.type_ref.name.split(".")[-1], ann.line
                    return "", ann.line
        return None

    def _validate_repeatable_declaration(self, ann_node: AnnotationInterfaceDeclaration):
        """Valida meta-anotação @Repeatable e seu container segundo JLS §9.6.3."""
        rep = self._extract_repeatable_container_name(ann_node)
        if rep is None:
            return
        container_name, rep_line = rep
        if not container_name:
            self.errors.append(
                SemanticError(
                    f"@Repeatable em '@{ann_node.name}' requer literal de classe de uma annotation interface container (ex: Containers.class — JLS §9.6.3).",
                    rep_line,
                )
            )
            return

        if container_name in self._declared_types:
            kind, _ = self._declared_types[container_name]
            if kind != "annotation_interface":
                self.errors.append(
                    SemanticError(
                        f"Tipo container '{container_name}' de '@Repeatable' em '@{ann_node.name}' deve ser uma '@interface' (encontrado {kind} — JLS §9.6.3).",
                        rep_line,
                    )
                )
                return

        container = self._annotation_interfaces.get(container_name)
        if container is None:
            return

        elem_map = {e.name: e for e in container.elements}
        if "value" not in elem_map:
            self.errors.append(
                SemanticError(
                    f"Annotation container '@{container_name}' de '@{ann_node.name}' deve declarar elemento obrigatório 'value()' retornando '{ann_node.name}[]' (JLS §9.6.3).",
                    rep_line,
                )
            )
        else:
            val_el = elem_map["value"]
            val_ret = val_el.effective_return_type
            expected_arr = f"{ann_node.name}[]"
            if val_ret != expected_arr and val_ret.split(".")[-1] != expected_arr:
                self.errors.append(
                    SemanticError(
                        f"Elemento 'value()' do container '@{container_name}' deve retornar '{expected_arr}' (encontrado '{val_ret}' — JLS §9.6.3).",
                        val_el.line,
                    )
                )

        for el in container.elements:
            if el.name != "value" and el.default_value is None:
                self.errors.append(
                    SemanticError(
                        f"Elemento extra '{el.name}' do container '@{container_name}' deve possuir valor 'default' obrigatório para @Repeatable (JLS §9.6.3).",
                        el.line,
                    )
                )

        t_ret_policy = self._extract_retention_policy(ann_node)
        c_ret_policy = self._extract_retention_policy(container)
        if self.RETENTION_RANK.get(c_ret_policy, 1) < self.RETENTION_RANK.get(t_ret_policy, 1):
            self.errors.append(
                SemanticError(
                    f"Retenção '{c_ret_policy}' do container '@{container_name}' não pode ser menor que a retenção '{t_ret_policy}' de '@{ann_node.name}' (JLS §9.6.3).",
                    rep_line,
                )
            )

        t_targets = self._extract_target_elements(ann_node)
        c_targets = self._extract_target_elements(container)
        if t_targets is not None and c_targets is not None:
            allowed_for_container = set(t_targets)
            if "TYPE_USE" in allowed_for_container:
                allowed_for_container.update({"TYPE", "TYPE_PARAMETER"})
            if "TYPE" in allowed_for_container:
                allowed_for_container.add("ANNOTATION_TYPE")
            invalid_c_targets = c_targets - allowed_for_container
            if invalid_c_targets:
                self.errors.append(
                    SemanticError(
                        f"@Target do container '@{container_name}' ({sorted(invalid_c_targets)}) excede o @Target permitido pela anotação repetível '@{ann_node.name}' (JLS §9.6.3).",
                        rep_line,
                    )
                )

    def _check_type_parameters_annotations(self, type_params: List[ASTNode]):
        """Valida annotations em TypeParameters e seus bounds (JLS §4.4, §9.7.4), além de circularidade entre bounds."""
        tp_list = list(type_params or [])
        tp_names = {getattr(tp, "name", "") for tp in tp_list if getattr(tp, "name", None)}
        deps: Dict[str, List[str]] = {}
        tp_lines: Dict[str, int] = {}
        for tp in tp_list:
            tp_name = getattr(tp, "name", "")
            tp_lines[tp_name] = getattr(tp, "line", 1)
            self._analyze_annotations(getattr(tp, "annotations", []), valid_targets={"TYPE_PARAMETER", "TYPE_USE"})
            direct: List[str] = []
            for b in getattr(tp, "bounds", []):
                self._check_type_ref_annotations(b)
                b_name = getattr(b, "name", None)
                if (
                    tp_name
                    and b_name in tp_names
                    and not getattr(b, "type_arguments", [])
                    and (getattr(b, "array_dimensions", 0) or 0) == 0
                ):
                    direct.append(b_name)
            if tp_name:
                deps[tp_name] = direct

        for tp in tp_list:
            start = getattr(tp, "name", "")
            if not start:
                continue
            visiting: Set[str] = {start}
            stack = list(deps.get(start, []))
            seen: Set[str] = set()
            has_cycle = False
            while stack:
                cur = stack.pop()
                if cur in visiting:
                    has_cycle = True
                    break
                if cur in seen:
                    continue
                seen.add(cur)
                for nxt in deps.get(cur, []):
                    if nxt == start or nxt in visiting:
                        has_cycle = True
                        break
                    stack.append(nxt)
                if has_cycle:
                    break
            if has_cycle:
                self.errors.append(
                    SemanticError(
                        f"Dependência cíclica no limite (bound) do parâmetro de tipo '{start}' (JLS §4.4 / §8.1.2).",
                        tp_lines.get(start, 1),
                    )
                )

    def _is_explicitly_imported_from_other_pkg(self, simple_name: str) -> bool:
        """Indica se simple_name foi importado explicitamente de outro pacote diferente do compat/java.lang."""
        if not simple_name or "." in simple_name:
            return False
        _, imports = self._current_import_context()
        compat_fqn = self.BUILTIN_COMPAT_FQNS.get(simple_name)
        jl_fqn = f"java.lang.{simple_name}"
        for iname, is_wild in imports:
            if not is_wild and iname and iname.split(".")[-1] == simple_name:
                if iname not in (compat_fqn, jl_fqn):
                    return True
        return False

    def _resolve_expected_type_param_count(self, type_name: Optional[str]) -> Optional[int]:
        """
        Retorna a quantidade esperada de parâmetros de tipo (0 ou N) quando o tipo é conhecido,
        ou None quando o tipo não pode ser resolvido de forma confiável.
        """
        if not type_name:
            return None
        clean = self._strip_leading_type_annotations(type_name) or type_name
        stripped = self._strip_generics(clean)
        if not stripped:
            return None
        base, dims = self._split_type_dims(stripped)
        if not base or base in ("var", "null", "desconhecido"):
            return None
        if base in self.PRIMITIVE_TYPES or base == "void":
            return 0
        if dims > 0:
            return None

        if self._lookup_type_param_bounds(base) is not None:
            return 0

        tdecl = self._lookup_type_decl(base)
        if tdecl is not None:
            dkind, tnode = tdecl
            if dkind in ("enum", "annotation_interface"):
                return 0
            return len(getattr(tnode, "type_parameters", []) or [])

        ext = self._resolve_external_type(base)
        if ext is not None:
            return len(ext.type_parameters or [])

        simple = base.split(".")[-1]
        is_unqualified = "." not in base
        matches_compat = self.BUILTIN_COMPAT_FQNS.get(simple) == base or f"java.lang.{simple}" == base
        if is_unqualified:
            if self._is_explicitly_imported_from_other_pkg(simple):
                return None
            if simple in self.BUILTIN_TYPE_PARAMS:
                return len(self.BUILTIN_TYPE_PARAMS[simple])
            if (
                simple in self.BUILTIN_CLASS_TYPES
                or simple in self.BUILTIN_INTERFACE_TYPES
                or simple in self.BUILTIN_FINAL_TYPES
                or simple in self.KNOWN_EXCEPTION_PARENTS
                or simple == "Enum"
            ):
                return 0
        elif base in self.BUILTIN_TYPE_PARAMS or matches_compat:
            if base in self.BUILTIN_TYPE_PARAMS:
                return len(self.BUILTIN_TYPE_PARAMS[base])
            if simple in self.BUILTIN_TYPE_PARAMS:
                return len(self.BUILTIN_TYPE_PARAMS[simple])
            if (
                base in self.BUILTIN_CLASS_TYPES
                or base in self.BUILTIN_INTERFACE_TYPES
                or simple in self.BUILTIN_CLASS_TYPES
                or simple in self.BUILTIN_INTERFACE_TYPES
                or simple in self.BUILTIN_FINAL_TYPES
                or simple in self.KNOWN_EXCEPTION_PARENTS
            ):
                return 0

        return None

    def _is_static_nested_type(self, type_name: Optional[str]) -> bool:
        """Retorna True se `type_name` for um tipo membro estático (explícito ou implícito)."""
        if not type_name:
            return False
        meta = self._inheritance_analyzer.get_type_meta(type_name)
        if meta is not None:
            if not meta.get("is_nested"):
                return False
            if "static" in (meta.get("modifiers") or []) or meta.get("kind") in (
                "interface",
                "annotation_interface",
                "enum",
                "record",
            ):
                return True
            enc_key = meta.get("enclosing_key")
            if enc_key:
                enc_meta = self._inheritance_analyzer.get_type_meta(enc_key)
                if enc_meta is not None and enc_meta.get("kind") in ("interface", "annotation_interface"):
                    return True
            return False
        ext = self._resolve_external_type(type_name)
        if ext is not None and ext.is_nested:
            if "static" in (ext.modifiers or []) or ext.kind in (
                "interface",
                "annotation_interface",
                "enum",
                "record",
            ):
                return True
            if ext.enclosing_fqn:
                enc_ext = self._resolve_external_type(ext.enclosing_fqn)
                if enc_ext is not None and enc_ext.kind in ("interface", "annotation_interface"):
                    return True
            return False
        return False

    def _check_type_ref_arity(
        self,
        type_ref: Optional[ASTNode],
        resolved_name_override: Optional[str] = None,
    ) -> None:
        """Valida a aridade de argumentos genéricos explícitos por segmento conforme JLS §4.5."""
        if not isinstance(type_ref, TypeReference):
            return
        tname = getattr(type_ref, "name", "")
        if not tname:
            return
        line = getattr(type_ref, "line", 1)
        seg_targs = getattr(type_ref, "segment_type_arguments", None)
        parts = tname.split(".")

        if seg_targs and len(seg_targs) == len(parts) and not resolved_name_override:
            for idx in range(1, len(parts)):
                seg_name = ".".join(parts[: idx + 1])
                if self._is_static_nested_type(seg_name):
                    for prev_idx in range(idx):
                        if seg_targs[prev_idx] is not None:
                            prev_name = ".".join(parts[: prev_idx + 1])
                            self.errors.append(
                                SemanticError(
                                    f"Não é possível selecionar a classe estática '{seg_name}' a partir do tipo parametrizado '{prev_name}' (JLS §4.5).",
                                    line,
                                )
                            )
                            break
            for idx, sargs in enumerate(seg_targs):
                if sargs is None:
                    continue
                seg_name = ".".join(parts[: idx + 1])
                if len(sargs) == 0:
                    self.errors.append(
                        SemanticError(
                            f"Operador diamond '<>' não é permitido fora da instanciação de objeto com 'new' em '{seg_name}' (JLS §4.5.1 / §15.9).",
                            line,
                        )
                    )
                    continue
                expected = self._resolve_expected_type_param_count(seg_name)
                if expected is not None and len(sargs) != expected:
                    if expected == 0:
                        self.errors.append(
                            SemanticError(
                                f"Tipo '{seg_name}' não é genérico; não pode receber argumentos de tipo (JLS §4.5).",
                                line,
                            )
                        )
                    else:
                        self.errors.append(
                            SemanticError(
                                f"Quantidade incorreta de argumentos de tipo para '{seg_name}': esperado {expected}, encontrado {len(sargs)} (JLS §4.5).",
                                line,
                            )
                        )
            return

        targs = getattr(type_ref, "type_arguments", None) or []
        if not targs:
            return
        lookup_name = resolved_name_override or tname
        expected = self._resolve_expected_type_param_count(lookup_name)
        if expected is not None and len(targs) != expected:
            if expected == 0:
                self.errors.append(
                    SemanticError(
                        f"Tipo '{tname}' não é genérico; não pode receber argumentos de tipo (JLS §4.5).",
                        line,
                    )
                )
            else:
                self.errors.append(
                    SemanticError(
                        f"Quantidade incorreta de argumentos de tipo para '{tname}': esperado {expected}, encontrado {len(targs)} (JLS §4.5).",
                        line,
                    )
                )

    def _validate_type_args_against_bounds(
        self,
        owner_name: str,
        arg_strs: List[str],
        line: int,
        outer_subst: Optional[Dict[str, str]] = None,
        decls_override: Optional[List[Tuple[str, List[str]]]] = None,
        error_sink: Optional[List[SemanticError]] = None,
    ) -> Dict[str, str]:
        """Valida argumentos genéricos (concretos e wildcards) contra os bounds declarados (JLS §4.5 / §5.1.10)."""
        if not owner_name or not arg_strs:
            return {}
        decls = decls_override if decls_override is not None else self._type_param_decls_for_type(owner_name)
        if not decls or len(decls) != len(arg_strs):
            return {}
        target_errors = self.errors if error_sink is None else error_sink

        subst_map: Dict[str, str] = dict(outer_subst or {})
        temp_caps: List[str] = []
        parsed_args: List[Tuple[Optional[str], Optional[str]]] = []

        try:
            # Passo 1: atribui argumentos concretos e variáveis de captura temporárias (JLS §5.1.10)
            for (tp_name, _), arg_s in zip(decls, arg_strs):
                wk, wb = self._parse_wildcard_arg(arg_s)
                parsed_args.append((wk, wb))
                if not tp_name or not arg_s:
                    continue
                if wk is None:
                    subst_map[tp_name] = arg_s
                else:
                    self._capture_counter += 1
                    cap_name = f"CAP#{self._capture_counter}"
                    temp_caps.append(cap_name)
                    subst_map[tp_name] = cap_name
                    init_up = [wb] if (wk == "extends" and wb) else ["Object"]
                    init_low = wb if (wk == "super" and wb) else None
                    self._capture_vars[cap_name] = {
                        "name": cap_name,
                        "upper_bounds": init_up,
                        "lower_bound": init_low,
                    }

            # Passo 2: refina limites superiores das capturas considerando os bounds declarados substituídos
            for (tp_name, raw_bounds), (wk, wb) in zip(decls, parsed_args):
                if wk is None or not tp_name:
                    continue
                cap_name = subst_map.get(tp_name)
                if not cap_name or cap_name not in self._capture_vars:
                    continue
                decl_bs = [
                    self._substitute_type_vars(rb, subst_map) or rb
                    for rb in (raw_bounds or [])
                ] or ["Object"]
                if wk == "extends":
                    uppers = self._combine_upper_bounds(wb or "Object", decl_bs)
                    lower = None
                elif wk == "super":
                    uppers = decl_bs
                    lower = wb or "Object"
                else:
                    uppers = decl_bs
                    lower = None
                self._capture_vars[cap_name] = {
                    "name": cap_name,
                    "upper_bounds": uppers,
                    "lower_bound": lower,
                }

            # Passo 3: valida cada argumento contra seus bounds substituídos
            for (tp_name, raw_bounds), arg_s, (wk, wb) in zip(decls, arg_strs, parsed_args):
                if not arg_s:
                    continue
                if wk is None:
                    clean_arg = (self._strip_leading_type_annotations(arg_s) or arg_s).strip()
                    for raw_b in raw_bounds or []:
                        subst_b = self._substitute_type_vars(raw_b, subst_map) or raw_b
                        clean_b = (self._strip_leading_type_annotations(subst_b) or subst_b).strip()
                        if not clean_b:
                            continue
                        if clean_b in ("Object", "java.lang.Object") and clean_arg not in self.PRIMITIVE_TYPES and clean_arg != "void":
                            continue
                        if self._is_subtype(clean_arg, clean_b) is False:
                            target_errors.append(
                                SemanticError(
                                    f"Argumento de tipo '{clean_arg}' não está dentro do limite '{clean_b}' do parâmetro '{tp_name}' em '{owner_name}' (JLS §4.5).",
                                    line,
                                )
                            )
                            break
                    continue

                if wk == "super":
                    clean_l = (self._strip_leading_type_annotations(wb or "Object") or "Object").strip()
                    for raw_b in raw_bounds or []:
                        subst_b = self._substitute_type_vars(raw_b, subst_map) or raw_b
                        clean_b = (self._strip_leading_type_annotations(subst_b) or subst_b).strip()
                        if not clean_b or clean_b in ("Object", "java.lang.Object"):
                            continue
                        if self._is_subtype(clean_l, clean_b) is False:
                            target_errors.append(
                                SemanticError(
                                    f"Wildcard '? super {clean_l}' incompatível com o limite '{clean_b}' do parâmetro '{tp_name}' em '{owner_name}' (JLS §4.5).",
                                    line,
                                )
                            )
                            break
                    continue

                if wk == "extends":
                    clean_u = (self._strip_leading_type_annotations(wb or "Object") or "Object").strip()
                    if clean_u in ("Object", "java.lang.Object"):
                        continue
                    is_closed_u = self._is_final_or_closed_leaf(clean_u) is True
                    clean_bounds: List[str] = []
                    failed_bound = False
                    for raw_b in raw_bounds or []:
                        subst_b = self._substitute_type_vars(raw_b, subst_map) or raw_b
                        clean_b = (self._strip_leading_type_annotations(subst_b) or subst_b).strip()
                        if not clean_b or clean_b in ("Object", "java.lang.Object"):
                            continue
                        clean_bounds.append(clean_b)
                        if is_closed_u:
                            self_map = dict(subst_map)
                            if tp_name:
                                self_map[tp_name] = clean_u
                            self_b = (self._substitute_type_vars(raw_b, self_map) or raw_b).strip()
                            if self._is_subtype(clean_u, self_b) is False:
                                target_errors.append(
                                    SemanticError(
                                        f"Wildcard '? extends {clean_u}' possui interseção impossível com o limite '{clean_b}' do parâmetro '{tp_name}' em '{owner_name}' (JLS §4.5).",
                                        line,
                                    )
                                )
                                failed_bound = True
                                break
                            continue
                        if self._are_intersection_types_compatible(clean_u, clean_b) is False:
                            target_errors.append(
                                SemanticError(
                                    f"Wildcard '? extends {clean_u}' possui interseção impossível com o limite '{clean_b}' do parâmetro '{tp_name}' em '{owner_name}' (JLS §4.5).",
                                    line,
                                )
                            )
                            failed_bound = True
                            break
                    # Se há múltiplos bounds, verifica também interseção mútua entre eles quando substituídos
                    if not failed_bound and len(clean_bounds) > 1:
                        for idx_a in range(len(clean_bounds)):
                            if failed_bound:
                                break
                            for idx_b in range(idx_a + 1, len(clean_bounds)):
                                if self._are_intersection_types_compatible(clean_bounds[idx_a], clean_bounds[idx_b]) is False:
                                    target_errors.append(
                                        SemanticError(
                                            f"Wildcard '? extends {clean_u}' gera limites incompatíveis '{clean_bounds[idx_a]}' & '{clean_bounds[idx_b]}' para '{tp_name}' em '{owner_name}' (JLS §4.5).",
                                            line,
                                        )
                                    )
                                    failed_bound = True
                                    break
        finally:
            for cap_name in temp_caps:
                self._capture_vars.pop(cap_name, None)

        return subst_map

    def _check_type_ref_bounds(
        self,
        type_ref: Optional[ASTNode],
        resolved_name_override: Optional[str] = None,
        outer_subst: Optional[Dict[str, str]] = None,
    ) -> None:
        """Valida os limites (bounds) de argumentos genéricos por segmento ou tipo (JLS §4.5)."""
        if not isinstance(type_ref, TypeReference):
            return
        tname = getattr(type_ref, "name", "")
        if not tname:
            return
        line = getattr(type_ref, "line", 1)
        seg_targs = getattr(type_ref, "segment_type_arguments", None)
        parts = tname.split(".")

        if seg_targs and len(seg_targs) == len(parts) and not resolved_name_override:
            accumulated_subst: Dict[str, str] = dict(outer_subst or {})
            for idx, sargs in enumerate(seg_targs):
                if not sargs:
                    continue
                seg_name = ".".join(parts[: idx + 1])
                arg_strs = [self._normalize_type_str(a) or "" for a in sargs]
                if all(arg_strs):
                    seg_map = self._validate_type_args_against_bounds(
                        seg_name, arg_strs, line, outer_subst=accumulated_subst
                    )
                    accumulated_subst.update(seg_map)
            return

        targs = getattr(type_ref, "type_arguments", None) or []
        if not targs:
            return
        lookup_name = resolved_name_override or tname
        arg_strs = [self._normalize_type_str(a) or "" for a in targs]
        if all(arg_strs):
            self._validate_type_args_against_bounds(lookup_name, arg_strs, line, outer_subst=outer_subst)

    def _check_type_ref_annotations(
        self,
        type_ref: Optional[ASTNode],
        skip_type_access: bool = False,
        skip_arity: bool = False,
    ):
        """Valida recursivamente type annotations, acesso e aridade genérica em tipos e segmentos."""
        if type_ref is None:
            return
        if isinstance(type_ref, WildcardType):
            self._analyze_annotations(getattr(type_ref, "annotations", []), valid_targets={"TYPE_USE"})
            bound_t = getattr(type_ref, "bound_type", None)
            if bound_t is not None:
                self._check_type_ref_annotations(bound_t)
            return

        annos = getattr(type_ref, "annotations", [])
        is_void = getattr(type_ref, "name", "") == "void" and getattr(type_ref, "array_dimensions", 0) == 0
        if annos and not is_void:
            self._analyze_annotations(annos, valid_targets={"TYPE_USE"})

        for seg_annos in getattr(type_ref, "segment_annotations", []):
            if seg_annos:
                self._analyze_annotations(seg_annos, valid_targets={"TYPE_USE"})

        for da in getattr(type_ref, "dims_annotations", []):
            if da:
                self._analyze_annotations(da, valid_targets={"TYPE_USE"})

        for ea in getattr(type_ref, "ellipsis_annotations", []):
            self._analyze_annotations([ea], valid_targets={"TYPE_USE"})

        self._check_type_parameters_annotations(getattr(type_ref, "type_parameters", []))
        seg_targs = getattr(type_ref, "segment_type_arguments", None)
        visited_args: List[ASTNode] = []
        seen_ids: Set[int] = set()
        if seg_targs:
            for sargs in seg_targs:
                if sargs:
                    for targ in sargs:
                        if id(targ) not in seen_ids:
                            seen_ids.add(id(targ))
                            visited_args.append(targ)
        for targ in getattr(type_ref, "type_arguments", []) or []:
            if id(targ) not in seen_ids:
                seen_ids.add(id(targ))
                visited_args.append(targ)
        for targ in visited_args:
            self._check_type_ref_annotations(targ)

        if not skip_arity:
            self._check_type_ref_arity(type_ref)
            self._check_type_ref_bounds(type_ref)

        if not skip_type_access and isinstance(type_ref, TypeReference):
            raw_tname = self._normalize_type_str(type_ref)
            if raw_tname and not is_void and raw_tname != "var":
                t_base, _ = self._split_type_dims(self._strip_generics(raw_tname) or "")
                if (
                    t_base
                    and t_base not in self.PRIMITIVE_TYPES
                    and self._lookup_type_param_bounds(t_base) is None
                ):
                    self._inheritance_analyzer.check_type_access(t_base, getattr(type_ref, "line", 1))

    def _analyze_annotations(
        self,
        annos: List[ASTNode],
        valid_targets: Set[str],
        adjacent_type_ref: Optional[TypeReference] = None,
    ):
        """
        Valida uso de lista de annotations em uma posição alvo:
        - Repetibilidade (@Repeatable) e mistura proibida container + repetível
        - Aplicabilidade via @Target
        - Presença de elementos obrigatórios, desconhecimento/duplicidade de chaves e constância/tipo dos valores
        """
        if not annos:
            return

        grouped: Dict[str, List[Annotation]] = {}
        adj_annos = set(id(a) for a in getattr(adjacent_type_ref, "annotations", [])) if adjacent_type_ref is not None else set()
        adj_is_void = (
            adjacent_type_ref is not None
            and getattr(adjacent_type_ref, "name", "") == "void"
            and getattr(adjacent_type_ref, "array_dimensions", 0) == 0
        )

        for ann in annos:
            if not isinstance(ann, Annotation):
                continue
            simple_name = ann.name.split(".")[-1]
            grouped.setdefault(simple_name, []).append(ann)

            ann_id = id(ann)
            first_visit = ann_id not in self._validated_ann_targets
            self._validated_ann_targets.add(ann_id)

            effective_targets = set(valid_targets)
            if ann_id in adj_annos and not adj_is_void:
                effective_targets.add("TYPE_USE")

            defn = self._annotation_interfaces.get(simple_name)

            # 1. Validação de @Target quando @interface foi declarada na unidade e há contexto-alvo (anotações aninhadas em ElementValue têm effective_targets vazio)
            if effective_targets and first_visit and defn is not None:
                allowed = self._extract_target_elements(defn)
                if allowed is not None:
                    expanded_allowed = set(allowed)
                    if "TYPE_USE" in expanded_allowed:
                        expanded_allowed.update({"TYPE", "TYPE_PARAMETER"})
                    if "TYPE" in expanded_allowed:
                        expanded_allowed.add("ANNOTATION_TYPE")
                    if not (effective_targets & expanded_allowed):
                        self.errors.append(
                            SemanticError(
                                f"Anotação '@{ann.name}' não é aplicável ao alvo {sorted(effective_targets)} (permitido pelo @Target: {sorted(allowed)} — JLS §9.6.4.1).",
                                ann.line,
                            )
                        )

            # 2. Validação estrutural e semântica de argumentos da anotação (sem duplicar no par decl/type_ref)
            if not first_visit:
                continue

            elem_map = {e.name: e for e in defn.elements} if defn is not None else None
            provided_keys: Set[str] = set()

            if isinstance(ann, SingleElementAnnotation):
                if ann.element_value is not None:
                    expected_t = None
                    if elem_map is not None:
                        if "value" not in elem_map:
                            self.errors.append(
                                SemanticError(
                                    f"Anotação '@{ann.name}' não declara o elemento 'value' para uso abreviado (JLS §9.7.3).",
                                    ann.line,
                                )
                            )
                        else:
                            expected_t = elem_map["value"].effective_return_type
                            provided_keys.add("value")
                    self._validate_element_value(
                        ann.element_value,
                        expected_type=expected_t,
                        owner_desc=f"anotação '@{ann.name}'",
                    )
            elif isinstance(ann, NormalAnnotation):
                seen_pair_keys: Set[str] = set()
                for pair in ann.pairs:
                    if pair.name in seen_pair_keys:
                        self.errors.append(
                            SemanticError(
                                f"Elemento duplicado '{pair.name}' na anotação '@{ann.name}' (JLS §9.7.1).",
                                pair.line,
                            )
                        )
                    else:
                        seen_pair_keys.add(pair.name)

                    expected_t = None
                    if elem_map is not None:
                        if pair.name not in elem_map:
                            self.errors.append(
                                SemanticError(
                                    f"Elemento desconhecido '{pair.name}' na anotação '@{ann.name}' (JLS §9.7.1).",
                                    pair.line,
                                )
                            )
                        else:
                            expected_t = elem_map[pair.name].effective_return_type
                            provided_keys.add(pair.name)

                    self._validate_element_value(
                        pair.value,
                        expected_type=expected_t,
                        owner_desc=f"elemento '{pair.name}' de '@{ann.name}'",
                    )

            # 3. Elementos obrigatórios (sem default) ausentes
            if elem_map is not None:
                for el_name, el_decl in elem_map.items():
                    if el_decl.is_required and el_name not in provided_keys:
                        self.errors.append(
                            SemanticError(
                                f"Elemento obrigatório '{el_name}' ausente na anotação '@{ann.name}' (JLS §9.7).",
                                ann.line,
                            )
                        )

        # 4. Validação de repetibilidade (@Repeatable) no mesmo local
        for name, group in grouped.items():
            defn = self._annotation_interfaces.get(name)
            rep = self._extract_repeatable_container_name(defn) if defn is not None else None
            if len(group) > 1:
                if name in self.BUILTIN_NON_REPEATABLE_ANNOTATIONS:
                    self.errors.append(
                        SemanticError(
                            f"Anotação '@{name}' não é repetível (@Repeatable) e não pode aparecer múltiplas vezes no mesmo local (JLS §9.7.5).",
                            group[1].line,
                        )
                    )
                elif defn is not None and rep is None:
                    self.errors.append(
                        SemanticError(
                            f"Anotação duplicada '@{name}' requer meta-anotação '@Repeatable' para ser repetida (JLS §9.6.3 / §9.7.5).",
                            group[1].line,
                        )
                    )
            if rep is not None and rep[0] and rep[0] in grouped:
                self.errors.append(
                    SemanticError(
                        f"Não é permitido misturar a anotação repetível '@{name}' e seu container '@{rep[0]}' diretamente no mesmo local (JLS §9.7.5).",
                        grouped[rep[0]][0].line,
                    )
                )

    def _validate_element_value(
        self,
        ev: ElementValue,
        expected_type: Optional[str] = None,
        owner_desc: str = "anotação",
    ):
        """Valida constância em tempo de compilação e compatibilidade de tipos de um ElementValue."""
        if ev is None:
            return
        val = ev.value if isinstance(ev, ElementValue) else ev

        # 1. Anotação aninhada
        if isinstance(val, Annotation):
            self._analyze_annotations([val], valid_targets=set())
            if expected_type is not None:
                self._validate_element_value_compatible(val, expected_type, owner_desc, getattr(val, "line", ev.line))
            return

        # 2. Inicializador de array ({...})
        if isinstance(val, ArrayInitializer):
            for elem in val.elements:
                inner = elem.value if isinstance(elem, ElementValue) else elem
                if isinstance(inner, ArrayInitializer):
                    self.errors.append(
                        SemanticError(
                            f"Inicializadores de array aninhados '{{{{ ... }}}}' não são permitidos em {owner_desc} (JLS §9.7.1).",
                            getattr(elem, "line", ev.line),
                        )
                    )
                else:
                    sub_ev = elem if isinstance(elem, ElementValue) else ElementValue(value=elem, line=getattr(elem, "line", ev.line), column=1)
                    self._validate_element_value(sub_ev, expected_type=None, owner_desc=owner_desc)

            if expected_type is not None:
                self._validate_element_value_compatible(val, expected_type, owner_desc, ev.line)
            return

        # 3. Expressão condicional: não permite null, chamadas de método, new, atribuições, lambdas ou não-constantes
        self._check_annotation_constant_expr(val, owner_desc, ev.line)
        if expected_type is not None:
            self._validate_element_value_compatible(val, expected_type, owner_desc, ev.line)

    @staticmethod
    def _to_java_int(v: int) -> int:
        """Converte inteiro arbitrário para int Java 32 bits em complemento de dois."""
        v &= 0xFFFFFFFF
        return v - 0x100000000 if v >= 0x80000000 else v

    @staticmethod
    def _to_java_long(v: int) -> int:
        """Converte inteiro arbitrário para long Java 64 bits em complemento de dois."""
        v &= 0xFFFFFFFFFFFFFFFF
        return v - 0x10000000000000000 if v >= 0x8000000000000000 else v

    @staticmethod
    def _to_java_byte(v: int) -> int:
        """Converte inteiro arbitrário para byte Java 8 bits com sinal (-128..127)."""
        v &= 0xFF
        return v - 0x100 if v >= 0x80 else v

    @staticmethod
    def _to_java_short(v: int) -> int:
        """Converte inteiro arbitrário para short Java 16 bits com sinal (-32768..32767)."""
        v &= 0xFFFF
        return v - 0x10000 if v >= 0x8000 else v

    @staticmethod
    def _to_java_char(v: int) -> int:
        """Converte inteiro arbitrário para char Java 16 bits sem sinal (0..65535)."""
        return v & 0xFFFF

    @staticmethod
    def _to_java_float(v: float) -> float:
        """Arredonda float IEEE 754 para precisão simples de 32 bits conforme Java."""
        f = float(v)
        if math.isnan(f):
            return float("nan")
        if math.isinf(f):
            return math.copysign(float("inf"), f)
        try:
            return struct.unpack(">f", struct.pack(">f", f))[0]
        except OverflowError:
            return math.copysign(float("inf"), f)

    def _is_constant_variable_type(self, type_str: Optional[str]) -> bool:
        """Verifica se o tipo é primitivo ou String (condição necessária em JLS §4.12.4)."""
        if not type_str:
            return False
        t_clean = self._strip_leading_type_annotations(type_str) or type_str
        return t_clean in self.PRIMITIVE_TYPES or t_clean in ("String", "java.lang.String")

    def _resolve_constant_var_declaration(
        self, declared_type: Optional[str], is_final: bool, init_expr: Optional[ASTNode]
    ) -> Optional[Tuple[str, Any]]:
        """Retorna (tipo, valor) para variável constante JLS §4.12.4 ou None."""
        if not is_final or init_expr is None or not self._is_constant_variable_type(declared_type):
            return None
        res = self._eval_constant_expr(init_expr)
        if res is None:
            return None
        src_t, val = res
        t_clean = self._strip_leading_type_annotations(declared_type) or declared_type
        if t_clean == "java.lang.String":
            t_clean = "String"
        if t_clean in self.INTEGER_RANGES:
            if src_t not in ("byte", "short", "char", "int"):
                return None
            lo, hi = self.INTEGER_RANGES[t_clean]
            if not (lo <= val <= hi):
                return None
            return (t_clean, int(val))
        if t_clean == "int":
            return ("int", self._to_java_int(int(val))) if src_t in ("byte", "short", "char", "int") else None
        if t_clean == "long":
            return ("long", self._to_java_long(int(val))) if src_t in ("byte", "short", "char", "int", "long") else None
        if t_clean == "float":
            if src_t in ("byte", "short", "char", "int", "long", "float"):
                return ("float", self._to_java_float(float(val)))
            return None
        if t_clean == "double":
            if src_t in ("byte", "short", "char", "int", "long", "float", "double"):
                return ("double", float(val))
            return None
        if t_clean == "boolean":
            return ("boolean", bool(val)) if src_t == "boolean" else None
        if t_clean == "String":
            return ("String", str(val)) if src_t == "String" else None
        return None

    @staticmethod
    def _parse_java_char_literal(val: str) -> Optional[int]:
        """Converte o texto ou valor de literal char Java no código Unicode (0..65535)."""
        if val is None:
            return None
        if len(val) == 1:
            return ord(val)
        inner = val[1:-1] if val.startswith("'") and val.endswith("'") and len(val) >= 3 else val
        if len(inner) == 1:
            return ord(inner)
        escapes = {
            "\\n": 10, "\\r": 13, "\\t": 9, "\\b": 8, "\\f": 12,
            "\\'": 39, '\\"': 34, "\\\\": 92, "\\s": 32,
        }
        if inner in escapes:
            return escapes[inner]
        if inner.startswith("\\u") and len(inner) >= 6:
            try:
                return int(inner[2:].lstrip("u"), 16) & 0xFFFF
            except ValueError:
                return None
        if inner.startswith("\\") and len(inner) >= 2 and all(c in "01234567" for c in inner[1:]):
            v = int(inner[1:], 8)
            return v if 0 <= v <= 255 else None
        return None

    @staticmethod
    def _format_java_string_value(jtype: str, val: Any) -> str:
        """Formata valor constante primitivo ou String para concatenação de String Java."""
        if jtype == "String":
            return str(val)
        if jtype == "boolean":
            return "true" if val else "false"
        if jtype == "char":
            return chr(int(val))
        if jtype in ("byte", "short", "int", "long"):
            return str(int(val))
        if jtype in ("float", "double"):
            f = float(val)
            if math.isnan(f):
                return "NaN"
            if math.isinf(f):
                return "-Infinity" if f < 0 else "Infinity"
            return str(f)
        return str(val)

    def _cast_constant_value(self, src_t: str, val: Any, target_t: str) -> Optional[Tuple[str, Any]]:
        """Executa conversão de cast em expressão constante segundo JLS §5.1 / §5.5 / §15.29."""
        if target_t == "java.lang.String":
            target_t = "String"
        if target_t == "String":
            return ("String", str(val)) if src_t == "String" else None
        if target_t == "boolean":
            return ("boolean", bool(val)) if src_t == "boolean" else None
        if target_t not in self.NUMERIC_PRIMITIVE_TYPES or src_t not in self.NUMERIC_PRIMITIVE_TYPES:
            return None
        if target_t == "float":
            return ("float", self._to_java_float(float(val)))
        if target_t == "double":
            return ("double", float(val))
        if src_t in ("float", "double"):
            f = float(val)
            if math.isnan(f):
                iv = 0
            elif target_t == "long":
                if math.isinf(f):
                    iv = -(1 << 63) if f < 0 else (1 << 63) - 1
                else:
                    tr = math.trunc(f)
                    iv = max(-(1 << 63), min((1 << 63) - 1, tr))
            else:
                if math.isinf(f):
                    iv = -(1 << 31) if f < 0 else (1 << 31) - 1
                else:
                    tr = math.trunc(f)
                    iv = max(-(1 << 31), min((1 << 31) - 1, tr))
        else:
            iv = int(val)
        if target_t == "byte":
            return ("byte", self._to_java_byte(iv))
        if target_t == "short":
            return ("short", self._to_java_short(iv))
        if target_t == "char":
            return ("char", self._to_java_char(iv))
        if target_t == "int":
            return ("int", self._to_java_int(iv))
        if target_t == "long":
            return ("long", self._to_java_long(iv))
        return None

    def _promote_constant_binary_type(self, t1: str, t2: str) -> str:
        """Retorna tipo resultante da promoção numérica binária (JLS §5.6.2)."""
        if "double" in (t1, t2):
            return "double"
        if "float" in (t1, t2):
            return "float"
        if "long" in (t1, t2):
            return "long"
        return "int"

    def _eval_constant_field_in_type(self, type_name: str, field_name: str) -> Optional[Tuple[str, Any]]:
        """Busca e avalia campo constante final (ou constante de interface) declarado ou herdado em um tipo."""
        clean = self._strip_generics(self._strip_leading_type_annotations(type_name) or type_name) or type_name
        simple = self._simple_base_name(clean) or clean
        if not simple:
            return None
        key = (clean, field_name)
        if key in self._const_eval_stack:
            return None
        self._const_eval_stack.add(key)
        try:
            visited: Set[str] = set()
            queue: List[str] = [clean]
            while queue:
                cur = queue.pop(0)
                cur_base = self._strip_generics(cur) or cur
                cur_s = self._simple_base_name(cur_base) or ""
                cur_resolved = self._lookup_internal_type_key(cur_base)
                cur_ext = self._resolve_external_type(cur_base) if cur_resolved is None else None
                cur_key = cur_resolved or (cur_ext.fqn if cur_ext is not None else cur_s)
                if not cur_key or cur_key in visited:
                    continue
                visited.add(cur_key)
                tdecl = self._lookup_type_decl(cur_resolved or cur_s)
                if tdecl is not None:
                    tkind, tnode = tdecl
                    is_ifc = (tkind == "interface")
                    for member in getattr(tnode, "members", []):
                        if isinstance(member, FieldDeclaration):
                            is_fin = True if is_ifc else ("final" in getattr(member, "modifiers", []))
                            decls = getattr(member, "declarators", None) or []
                            if decls:
                                for d in decls:
                                    if getattr(d, "name", None) == field_name:
                                        return self._resolve_constant_var_declaration(
                                            getattr(d, "effective_type", None), is_fin, getattr(d, "initializer", None)
                                        )
                            elif getattr(member, "name", None) == field_name:
                                raw_t = getattr(member, "effective_type", None) or self._normalize_type_str(getattr(member, "type_ref", None))
                                return self._resolve_constant_var_declaration(raw_t, is_fin, getattr(member, "initializer", None))
                elif cur_ext is not None:
                    ef = cur_ext.fields.get(field_name)
                    if ef is not None and ef.constant_value is not None:
                        return ef.constant_value
                if cur_s in self.BUILTIN_CONSTANT_VALUES and field_name in self.BUILTIN_CONSTANT_VALUES[cur_s]:
                    if cur_ext is None or self._is_partial_external_stdlib(cur_ext):
                        return self.BUILTIN_CONSTANT_VALUES[cur_s][field_name]
                supers, _ = self._direct_supertypes(cur)
                queue.extend(supers)
            return None
        finally:
            self._const_eval_stack.discard(key)

    def _eval_constant_literal(self, node: Literal) -> Optional[Tuple[str, Any]]:
        """Avalia literal primitivo ou String segundo JLS §3.10 e §15.29."""
        kind = getattr(node, "kind", "")
        val = getattr(node, "value", None)
        if kind == "NULL" or (kind == "" and str(val) == "null"):
            return None
        if kind == "BOOLEAN":
            return ("boolean", str(val).lower() == "true")
        if kind in ("STRING", "TEXT_BLOCK"):
            return ("String", str(val))
        if kind == "CHAR":
            cp = self._parse_java_char_literal(str(val))
            return ("char", cp) if cp is not None else None
        val_s = str(val).strip()
        is_fp = (
            kind in ("FLOAT", "DOUBLE")
            or "." in val_s
            or ("e" in val_s.lower() and not val_s.startswith(("0x", "0X")))
            or ("p" in val_s.lower() and val_s.startswith(("0x", "0X")))
            or (val_s.endswith(("f", "F", "d", "D")) and not val_s.startswith(("0x", "0X")))
        )
        if kind in ("NUM", "INT", "LONG") and not is_fp:
            parsed = self._parse_java_int_literal(val_s)
            if parsed is None:
                return None
            num_val, is_long_lit, base = parsed
            is_long = (kind == "LONG") or is_long_lit
            if base == 10:
                max_val = ((1 << 63) - 1) if is_long else ((1 << 31) - 1)
            else:
                max_val = ((1 << 64) - 1) if is_long else ((1 << 32) - 1)
            if num_val > max_val:
                return None
            return ("long", self._to_java_long(num_val)) if is_long else ("int", self._to_java_int(num_val))
        is_float = (kind == "FLOAT") or val_s.endswith(("f", "F"))
        raw = val_s[:-1] if val_s.endswith(("f", "F", "d", "D")) else val_s
        clean = raw.replace("_", "")
        try:
            fval = float.fromhex(clean) if clean.startswith(("0x", "0X")) else float(clean)
        except (ValueError, OverflowError):
            return None
        if math.isinf(fval):
            return None
        if is_float:
            jf = self._to_java_float(fval)
            return None if math.isinf(jf) else ("float", jf)
        return ("double", fval)

    def _eval_constant_unary(self, expr: UnaryOp) -> Optional[Tuple[str, Any]]:
        """Avalia expressão unária constante (JLS §15.15 / §15.29)."""
        op = expr.op
        if op not in ("+", "-", "~", "!"):
            return None
        if op == "-" and isinstance(expr.operand, Literal) and not getattr(expr.operand, "parenthesized", False):
            lit = expr.operand
            val_s = str(getattr(lit, "value", "")).strip()
            kind = getattr(lit, "kind", "")
            if kind in ("NUM", "INT", "LONG"):
                parsed = self._parse_java_int_literal(val_s)
                if parsed is not None:
                    num_val, is_long_lit, base = parsed
                    is_long = (kind == "LONG") or is_long_lit
                    if base == 10 and not is_long and num_val == (1 << 31):
                        return ("int", -(1 << 31))
                    if base == 10 and is_long and num_val == (1 << 63):
                        return ("long", -(1 << 63))
        inner = self._eval_constant_expr(expr.operand)
        if inner is None:
            return None
        st, sv = inner
        if op == "!":
            return ("boolean", not bool(sv)) if st == "boolean" else None
        if st not in self.NUMERIC_PRIMITIVE_TYPES:
            return None
        promoted = "int" if st in ("byte", "short", "char", "int") else st
        if op == "~":
            if promoted == "int":
                return ("int", self._to_java_int(~int(sv)))
            if promoted == "long":
                return ("long", self._to_java_long(~int(sv)))
            return None
        if op == "+":
            if promoted == "int":
                return ("int", self._to_java_int(int(sv)))
            if promoted == "long":
                return ("long", self._to_java_long(int(sv)))
            if promoted == "float":
                return ("float", self._to_java_float(float(sv)))
            return ("double", float(sv))
        if promoted == "int":
            return ("int", self._to_java_int(-int(sv)))
        if promoted == "long":
            return ("long", self._to_java_long(-int(sv)))
        if promoted == "float":
            return ("float", self._to_java_float(-float(sv)))
        return ("double", -float(sv))

    @staticmethod
    def _java_int_div_mod(lv: int, rv: int, is_mod: bool) -> Optional[int]:
        """Divisão/módulo inteiro com truncamento para zero conforme JLS §15.17.2/§15.17.3."""
        if rv == 0:
            return None
        if is_mod:
            r = abs(lv) % abs(rv)
            return -r if lv < 0 else r
        q = abs(lv) // abs(rv)
        return -q if (lv < 0) ^ (rv < 0) else q

    @staticmethod
    def _ieee_float_div_mod(lv: float, rv: float, is_mod: bool) -> float:
        """Divisão/módulo IEEE 754 sem levantar ZeroDivisionError em Python."""
        if is_mod:
            if math.isnan(lv) or math.isnan(rv) or math.isinf(lv) or rv == 0.0:
                return float("nan")
            if math.isinf(rv):
                return lv
            return math.fmod(lv, rv)
        if math.isnan(lv) or math.isnan(rv):
            return float("nan")
        if rv == 0.0:
            if lv == 0.0:
                return float("nan")
            sign = math.copysign(1.0, lv) * math.copysign(1.0, rv)
            return math.copysign(float("inf"), sign)
        if math.isinf(lv) and math.isinf(rv):
            return float("nan")
        return lv / rv

    def _eval_constant_binary(self, expr: BinaryOp) -> Optional[Tuple[str, Any]]:
        """Avalia operação binária constante respeitando semântica e overflow Java (JLS §15.17–§15.24, §15.29)."""
        lres = self._eval_constant_expr(expr.left)
        rres = self._eval_constant_expr(expr.right)
        if lres is None or rres is None:
            return None
        lt, lv = lres
        rt, rv = rres
        op = expr.op

        if op == "+" and ("String" in (lt, rt)):
            return ("String", self._format_java_string_value(lt, lv) + self._format_java_string_value(rt, rv))
        if op in ("&&", "||"):
            if lt != "boolean" or rt != "boolean":
                return None
            return ("boolean", bool(lv) and bool(rv)) if op == "&&" else ("boolean", bool(lv) or bool(rv))
        if op in ("==", "!="):
            if lt == "String" and rt == "String":
                eq = (lv == rv)
            elif lt == "boolean" and rt == "boolean":
                eq = (bool(lv) == bool(rv))
            elif lt in self.NUMERIC_PRIMITIVE_TYPES and rt in self.NUMERIC_PRIMITIVE_TYPES:
                pt = self._promote_constant_binary_type(lt, rt)
                if pt == "double":
                    eq = float(lv) == float(rv)
                elif pt == "float":
                    eq = self._to_java_float(lv) == self._to_java_float(rv)
                elif pt == "long":
                    eq = self._to_java_long(int(lv)) == self._to_java_long(int(rv))
                else:
                    eq = self._to_java_int(int(lv)) == self._to_java_int(int(rv))
            else:
                return None
            return ("boolean", eq if op == "==" else not eq)
        if op in ("<", "<=", ">", ">="):
            if lt not in self.NUMERIC_PRIMITIVE_TYPES or rt not in self.NUMERIC_PRIMITIVE_TYPES:
                return None
            pt = self._promote_constant_binary_type(lt, rt)
            if pt == "double":
                a, b = float(lv), float(rv)
            elif pt == "float":
                a, b = self._to_java_float(lv), self._to_java_float(rv)
            elif pt == "long":
                a, b = self._to_java_long(int(lv)), self._to_java_long(int(rv))
            else:
                a, b = self._to_java_int(int(lv)), self._to_java_int(int(rv))
            if op == "<":
                return ("boolean", a < b)
            if op == "<=":
                return ("boolean", a <= b)
            if op == ">":
                return ("boolean", a > b)
            return ("boolean", a >= b)
        if op in ("&", "|", "^"):
            if lt == "boolean" and rt == "boolean":
                a, b = bool(lv), bool(rv)
                if op == "&":
                    return ("boolean", a and b)
                if op == "|":
                    return ("boolean", a or b)
                return ("boolean", a != b)
            if lt in self.INTEGRAL_PRIMITIVES and rt in self.INTEGRAL_PRIMITIVES:
                pt = self._promote_constant_binary_type(lt, rt)
                a, b = int(lv), int(rv)
                raw = (a & b) if op == "&" else ((a | b) if op == "|" else (a ^ b))
                return ("long", self._to_java_long(raw)) if pt == "long" else ("int", self._to_java_int(raw))
            return None
        if op in ("<<", ">>", ">>>"):
            if lt not in self.INTEGRAL_PRIMITIVES or rt not in self.INTEGRAL_PRIMITIVES:
                return None
            pt = "long" if lt == "long" else "int"
            a, b = int(lv), int(rv)
            if pt == "long":
                shift = b & 0x3F
                la = self._to_java_long(a)
                if op == "<<":
                    return ("long", self._to_java_long((la & 0xFFFFFFFFFFFFFFFF) << shift))
                if op == ">>":
                    return ("long", self._to_java_long(la >> shift))
                return ("long", self._to_java_long((la & 0xFFFFFFFFFFFFFFFF) >> shift))
            shift = b & 0x1F
            ia = self._to_java_int(a)
            if op == "<<":
                return ("int", self._to_java_int((ia & 0xFFFFFFFF) << shift))
            if op == ">>":
                return ("int", self._to_java_int(ia >> shift))
            return ("int", self._to_java_int((ia & 0xFFFFFFFF) >> shift))
        if op in ("+", "-", "*", "/", "%"):
            if lt not in self.NUMERIC_PRIMITIVE_TYPES or rt not in self.NUMERIC_PRIMITIVE_TYPES:
                return None
            pt = self._promote_constant_binary_type(lt, rt)
            if pt in ("int", "long"):
                wrap = self._to_java_long if pt == "long" else self._to_java_int
                a, b = wrap(int(lv)), wrap(int(rv))
                if op == "+":
                    return (pt, wrap(a + b))
                if op == "-":
                    return (pt, wrap(a - b))
                if op == "*":
                    return (pt, wrap(a * b))
                q_or_r = self._java_int_div_mod(a, b, is_mod=(op == "%"))
                return (pt, wrap(q_or_r)) if q_or_r is not None else None
            conv = self._to_java_float if pt == "float" else float
            fa, fb = conv(float(lv)), conv(float(rv))
            try:
                if op == "+":
                    res = fa + fb
                elif op == "-":
                    res = fa - fb
                elif op == "*":
                    res = fa * fb
                else:
                    res = self._ieee_float_div_mod(fa, fb, is_mod=(op == "%"))
            except OverflowError:
                res = float("inf")
            return (pt, conv(res))
        return None

    def _eval_constant_expr(self, expr: Optional[ASTNode]) -> Optional[Tuple[str, Any]]:
        """
        Avalia expressão constante em tempo de compilação segundo JLS §15.29.
        Retorna (tipo_java, valor) ou None quando a expressão depende de execução ou é inválida.
        """
        if expr is None:
            return None
        if isinstance(expr, Literal):
            return self._eval_constant_literal(expr)
        if isinstance(expr, UnaryOp):
            return self._eval_constant_unary(expr)
        if isinstance(expr, BinaryOp):
            return self._eval_constant_binary(expr)
        if isinstance(expr, CastExpression):
            tdims = getattr(expr.target_type, "array_dimensions", 0)
            if tdims or getattr(expr, "additional_bounds", None):
                return None
            tname = self._normalize_type_str(getattr(expr, "target_type", None)) or getattr(expr.target_type, "name", None)
            t_clean = self._strip_leading_type_annotations(tname) if tname else None
            if not t_clean:
                return None
            inner = self._eval_constant_expr(expr.expression)
            if inner is None:
                return None
            return self._cast_constant_value(inner[0], inner[1], t_clean)
        if isinstance(expr, ConditionalExpression):
            cres = self._eval_constant_expr(expr.condition)
            tres = self._eval_constant_expr(expr.then_expr)
            eres = self._eval_constant_expr(expr.else_expr)
            if cres is None or tres is None or eres is None or cres[0] != "boolean":
                return None
            tt, tv = tres
            et, ev = eres
            chosen_val = tv if cres[1] else ev
            if tt == et:
                return (tt, chosen_val)
            if tt not in self.NUMERIC_PRIMITIVE_TYPES or et not in self.NUMERIC_PRIMITIVE_TYPES:
                return None
            if {tt, et} == {"byte", "short"}:
                res_t = "short"
            elif tt in self.INTEGER_RANGES and et == "int" and self.INTEGER_RANGES[tt][0] <= ev <= self.INTEGER_RANGES[tt][1]:
                res_t = tt
            elif et in self.INTEGER_RANGES and tt == "int" and self.INTEGER_RANGES[et][0] <= tv <= self.INTEGER_RANGES[et][1]:
                res_t = et
            else:
                res_t = self._promote_constant_binary_type(tt, et)
            return self._cast_constant_value(tt if cres[1] else et, chosen_val, res_t)
        if isinstance(expr, Identifier):
            info = self._find_local_var_info(expr.name)
            if info is not None:
                return info.get("const_typed") if info.get("is_final") else None
            sym = self.symbols.lookup(expr.name)
            if sym is not None:
                if "const_typed" in sym and sym.get("is_compile_constant"):
                    return sym["const_typed"]
                if sym.get("category") in ("variavel", "parametro", "componente_record"):
                    return None
                if sym.get("category") in ("campo", "constante_interface"):
                    for enc in reversed(self._enclosing_type_names):
                        fval = self._eval_constant_field_in_type(enc, expr.name)
                        if fval is not None:
                            return fval
                    return None
                return None
            for enc in reversed(self._enclosing_type_names):
                fval = self._eval_constant_field_in_type(enc, expr.name)
                if fval is not None:
                    return fval
            return None
        if isinstance(expr, MemberAccess):
            if isinstance(expr.target, Identifier):
                tname = expr.target.name
                if self._find_local_var_info(tname) is not None:
                    return None
                sym = self.symbols.lookup(tname)
                if sym is not None and sym.get("category") in ("variavel", "parametro", "componente_record", "campo"):
                    return None
                return self._eval_constant_field_in_type(tname, expr.member_name)
            chain: List[str] = []
            cur: Optional[ASTNode] = expr.target
            while isinstance(cur, MemberAccess):
                chain.append(cur.member_name)
                cur = cur.target
            if isinstance(cur, Identifier) and chain:
                if self._find_local_var_info(cur.name) is not None:
                    return None
                sym = self.symbols.lookup(cur.name)
                if sym is not None and sym.get("category") in ("variavel", "parametro", "componente_record", "campo"):
                    return None
                owner = chain[0]
                return self._eval_constant_field_in_type(owner, expr.member_name)
            return None
        return None

    def _is_compile_time_constant_expr(self, expr: Optional[ASTNode]) -> bool:
        """Verifica se uma expressão é constante em tempo de compilação segundo JLS §15.29."""
        return self._eval_constant_expr(expr) is not None

    def _check_annotation_constant_expr(self, node: Optional[ASTNode], owner_desc: str, fallback_line: int):
        """Valida que uma expressão dentro de ElementValue não contenha construções não-constantes."""
        if node is None:
            return
        line = getattr(node, "line", fallback_line)

        if isinstance(node, Literal):
            if node.kind == "NULL" or str(node.value) == "null":
                self.errors.append(
                    SemanticError(
                        f"Valor 'null' não é permitido em {owner_desc} (JLS §9.7.1).",
                        line,
                    )
                )
            return

        if isinstance(node, ClassLiteral):
            return

        if isinstance(node, ObjectCreationExpression):
            self.errors.append(
                SemanticError(
                    f"Instanciação 'new' não é expressão constante válida para {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, MethodCall):
            self.errors.append(
                SemanticError(
                    f"Chamada de método '{node.method_name}(...)' não é expressão constante válida para {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, ArrayCreationExpression):
            self.errors.append(
                SemanticError(
                    f"Criação explícita de array 'new ...[]' não é permitida em {owner_desc}; use inicializador '{{...}}' (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, ArrayInitializer):
            self.errors.append(
                SemanticError(
                    f"Inicializador de array '{{...}}' inválido em {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, (Assignment, LambdaExpression, MethodReference)):
            self.errors.append(
                SemanticError(
                    f"Expressão não constante inválida em {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, Identifier):
            sym = self.symbols.lookup(node.name)
            if sym is not None:
                cat = sym.get("category")
                if cat in ("constante_enum", "constante_interface"):
                    return
                if sym.get("is_compile_constant", False):
                    return
                self.errors.append(
                    SemanticError(
                        f"Valor não constante '{node.name}' ({cat}) não pode ser usado em {owner_desc} (JLS §9.7.1).",
                        line,
                    )
                )
                return
            if node.name in self._static_imports or self._has_wildcard_static_import:
                return
            self.errors.append(
                SemanticError(
                    f"Identificador não declarado ou não constante '{node.name}' em {owner_desc} (JLS §9.7.1).",
                    line,
                )
            )
            return

        if isinstance(node, MemberAccess):
            if isinstance(node.target, Identifier):
                tname = node.target.name
                sym = self.symbols.lookup(tname)
                if sym is not None and sym.get("category") in ("variavel", "parametro", "componente_record", "campo"):
                    if not sym.get("is_compile_constant", False):
                        self.errors.append(
                            SemanticError(
                                f"Acesso a membro de instância ou variável '{tname}.{node.member_name}' não é expressão constante para {owner_desc} (JLS §9.7.1).",
                                line,
                            )
                        )
                        return
                enum_decl = self._enums.get(tname)
                if enum_decl is not None:
                    const_names = {c.name for c in enum_decl.constants}
                    if node.member_name not in const_names:
                        self.errors.append(
                            SemanticError(
                                f"Constante '{node.member_name}' não existe no enum '{tname}' em {owner_desc}.",
                                line,
                            )
                        )
                elif not tname[:1].isupper() and sym is None:
                    self.errors.append(
                        SemanticError(
                            f"Acesso '{tname}.{node.member_name}' não é constante em tempo de compilação válida para {owner_desc} (JLS §9.7.1).",
                            line,
                        )
                    )
            else:
                self._check_annotation_constant_expr(node.target, owner_desc, line)
            return

        if isinstance(node, UnaryOp):
            self._check_annotation_constant_expr(node.operand, owner_desc, line)
            return

        if isinstance(node, BinaryOp):
            self._check_annotation_constant_expr(node.left, owner_desc, line)
            self._check_annotation_constant_expr(node.right, owner_desc, line)
            return

        if isinstance(node, ConditionalExpression):
            self._check_annotation_constant_expr(node.condition, owner_desc, line)
            self._check_annotation_constant_expr(node.then_expr, owner_desc, line)
            self._check_annotation_constant_expr(node.else_expr, owner_desc, line)
            return

        if isinstance(node, CastExpression):
            self._check_annotation_constant_expr(node.expression, owner_desc, line)
            return

    def _validate_element_value_compatible(
        self,
        val: ASTNode,
        expected_type: str,
        owner_desc: str,
        line: int,
    ):
        """Valida compatibilidade estática entre um valor de anotação e o tipo esperado pelo elemento."""
        exp_clean = expected_type.strip()
        exp_no_gen_parts = []
        depth = 0
        for ch in exp_clean:
            if ch == "<":
                depth += 1
            elif ch == ">":
                if depth > 0:
                    depth -= 1
            elif depth == 0:
                exp_no_gen_parts.append(ch)
        exp_no_gen = "".join(exp_no_gen_parts).strip()

        # Shorthand de elemento único para tipo array unidimensional (JLS §9.7.5)
        if exp_no_gen.endswith("[]") and not isinstance(val, ArrayInitializer):
            self._validate_element_value_compatible(val, exp_clean[:-2], owner_desc, line)
            return

        if isinstance(val, ArrayInitializer):
            if not exp_no_gen.endswith("[]"):
                self.errors.append(
                    SemanticError(
                        f"Inicializador de array '{{...}}' incompatível com o tipo '{expected_type}' esperado em {owner_desc}.",
                        line,
                    )
                )
                return
            item_expected = exp_clean[:-2]
            for elem in val.elements:
                inner = elem.value if isinstance(elem, ElementValue) else elem
                if not isinstance(inner, ArrayInitializer):
                    self._validate_element_value_compatible(inner, item_expected, owner_desc, getattr(elem, "line", line))
            return

        exp_base = exp_no_gen.split(".")[-1]

        if isinstance(val, Annotation):
            ann_simple = val.name.split(".")[-1]
            if exp_base != ann_simple:
                self.errors.append(
                    SemanticError(
                        f"Anotação '@{val.name}' incompatível com o tipo esperado '{expected_type}' em {owner_desc}.",
                        getattr(val, "line", line),
                    )
                )
            return

        if exp_base in self._annotation_interfaces or exp_base in self.BUILTIN_ANNOTATION_TYPES:
            self.errors.append(
                SemanticError(
                    f"Era esperada uma anotação '@{exp_base}' compatível com '{expected_type}' em {owner_desc}.",
                    line,
                )
            )
            return

        if exp_base == "Class":
            if not isinstance(val, ClassLiteral):
                self.errors.append(
                    SemanticError(
                        f"Era esperado um literal de classe ('.class') compatível com '{expected_type}' em {owner_desc}.",
                        line,
                    )
                )
                return
            if "<" in exp_clean and ">" in exp_clean:
                inner_gen = exp_clean[exp_clean.find("<") + 1 : exp_clean.rfind(">")].strip()
                lit_name = val.type_ref.full_name
                if inner_gen.startswith("? extends "):
                    bound_type = inner_gen[len("? extends "):].strip().split(".")[-1]
                    if bound_type == "Number":
                        allowed_nums = {"Number", "Integer", "Long", "Double", "Float", "Short", "Byte", "BigDecimal", "BigInteger"}
                        if lit_name.split(".")[-1] not in allowed_nums or lit_name in self.PRIMITIVE_TYPES or lit_name == "void":
                            self.errors.append(
                                SemanticError(
                                    f"Literal de classe '{lit_name}.class' incompatível com '{expected_type}' em {owner_desc}.",
                                    line,
                                )
                            )
                elif inner_gen != "?" and not inner_gen.startswith("? "):
                    exact_t = inner_gen.split(".")[-1]
                    if lit_name.split(".")[-1] != exact_t and lit_name != inner_gen:
                        self.errors.append(
                            SemanticError(
                                f"Literal de classe '{lit_name}.class' incompatível com '{expected_type}' em {owner_desc}.",
                                line,
                            )
                        )
            return

        if exp_base in self._enums:
            if isinstance(val, MemberAccess) and isinstance(val.target, Identifier):
                t_enum = val.target.name.split(".")[-1]
                if t_enum != exp_base:
                    self.errors.append(
                        SemanticError(
                            f"Enum '{val.target.name}' incompatível com o tipo esperado '{expected_type}' em {owner_desc}.",
                            line,
                        )
                    )
            elif isinstance(val, Identifier) and (val.name in self._static_imports or self._has_wildcard_static_import):
                pass
            else:
                self.errors.append(
                    SemanticError(
                        f"Valor incompatível com o enum '{expected_type}' em {owner_desc}.",
                        line,
                    )
                )
            return

        inferred = self.infer_type(val)
        if not inferred:
            return

        if exp_base == "String":
            if inferred != "String":
                self.errors.append(
                    SemanticError(
                        f"Incompatibilidade de tipo em {owner_desc}: esperado 'String', encontrado '{inferred}'.",
                        line,
                    )
                )
            return

        if exp_base == "boolean":
            if inferred != "boolean":
                self.errors.append(
                    SemanticError(
                        f"Incompatibilidade de tipo em {owner_desc}: esperado 'boolean', encontrado '{inferred}'.",
                        line,
                    )
                )
            return

        if exp_base in ("byte", "short", "int", "long", "float", "double", "char"):
            # Conversão estreitante constante válida em Java para byte/short/char a partir de literal int
            if exp_base in ("byte", "short", "char") and isinstance(val, Literal) and inferred == "int":
                try:
                    n = int(str(val.value), 0)
                    bounds = {"byte": (-128, 127), "short": (-32768, 32767), "char": (0, 65535)}
                    lo, hi = bounds[exp_base]
                    if lo <= n <= hi:
                        return
                except ValueError:
                    pass
            if not self.is_assignable(exp_base, inferred):
                self.errors.append(
                    SemanticError(
                        f"Incompatibilidade de tipo em {owner_desc}: esperado '{expected_type}', encontrado '{inferred}'.",
                        line,
                    )
                )

    def _register_local_var(
        self,
        name: str,
        var_type: str,
        line: int,
        is_final: bool = False,
        has_initializer: bool = True,
        category: str = "variavel",
        is_compile_constant: bool = False,
    ) -> bool:
        """Registra variável/parâmetro local verificando conflito em escopos locais e de patterns envolventes (JLS §6.3 / §6.4.1 / §14.4.2)."""
        if name == "_":
            return False
        for pscope in reversed(self._active_pattern_scopes):
            if name in pscope:
                prev = pscope[name]
                self.errors.append(
                    SemanticError(
                        f"Variável '{name}' declarada novamente (já declarada como variável de pattern na linha {prev['line']}).",
                        line,
                    )
                )
                return False
        if self._local_var_scopes:
            for scope in reversed(self._local_var_scopes):
                if name in scope:
                    prev = scope[name]
                    self.errors.append(
                        SemanticError(
                            f"Variável '{name}' declarada novamente (já declarada na linha {prev['line']}).",
                            line,
                        )
                    )
                    return False
            info = {
                "type": var_type,
                "line": line,
                "is_final": is_final,
                "reassigned": False,
                "category": category,
                "has_initializer": has_initializer,
            }
            self._local_var_scopes[-1][name] = info
            vid = ("local", id(info))
            self._flow_tracked[vid] = {"name": name, "is_final": is_final, "kind": "local", "line": line}
            if has_initializer:
                self._flow_da.add(vid)
                self._flow_du.discard(vid)
            else:
                self._flow_da.discard(vid)
                self._flow_du.add(vid)
            self.symbols.declare(
                name,
                var_type,
                line,
                category=category,
                is_final=is_final,
                is_compile_constant=is_compile_constant,
            )
            return True

        prev_sym = self.symbols.lookup(name)
        if not self.symbols.declare(
            name,
            var_type,
            line,
            category=category,
            is_final=is_final,
            is_compile_constant=is_compile_constant,
        ):
            prev_line = f" (declarada na linha {prev_sym['line']})" if prev_sym and "line" in prev_sym else ""
            self.errors.append(
                SemanticError(f"Variável '{name}' declarada novamente{prev_line}.", line)
            )
            return False
        return True

    def _find_local_var_info(self, name: str) -> Optional[Dict[str, Any]]:
        for scope in reversed(self._active_pattern_scopes):
            if name in scope:
                return scope[name]
        for scope in reversed(self._local_var_scopes):
            if name in scope:
                return scope[name]
        return None

    def _lookup_var_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """Busca variável em escopos de pattern ativos, escopos locais, tabela de símbolos e campos herdados."""
        for pscope in reversed(self._active_pattern_scopes):
            if name in pscope:
                info = pscope[name]
                return {
                    "type": info.get("type", "Object"),
                    "line": info.get("line", 1),
                    "category": info.get("category", "variavel"),
                    "is_final": info.get("is_final", False),
                    "is_compile_constant": False,
                    "is_pattern_var": True,
                }
        sym = self.symbols.lookup(name)
        cur_cls_key = self._inheritance_analyzer.current_enclosing_key()
        if cur_cls_key and self._find_local_var_info(name) is None:
            fields, _ = self._collect_type_fields(cur_cls_key)
            if name in fields:
                finfo = fields[name]
                if finfo.get("owner_key") == cur_cls_key and sym is not None:
                    return sym
                if sym is None or sym.get("category") in (self.TYPE_SYMBOL_CATEGORIES | {"campo", "constante_enum", "constante_interface", "componente_record"}):
                    return finfo
        return sym

    def _mark_local_var_reassigned(self, name: str):
        if not name:
            return
        for scope in reversed(self._active_pattern_scopes):
            if name in scope:
                info = scope[name]
                if info.get("has_initializer", True):
                    info["reassigned"] = True
                else:
                    info["has_initializer"] = True
                return
        for scope in reversed(self._local_var_scopes):
            if name in scope:
                info = scope[name]
                if info.get("has_initializer", True):
                    info["reassigned"] = True
                else:
                    info["has_initializer"] = True
                return

    def _expr_contains_identifier(self, node: Optional[ASTNode], target_name: str) -> bool:
        """Verifica se uma expressão referencia o identificador alvo (usado para detectar autorreferência em 'var')."""
        if node is None or isinstance(node, (TypeReference, Annotation)):
            return False
        if isinstance(node, Identifier):
            return node.name == target_name or node.name.startswith(f"{target_name}.")
        if isinstance(node, MemberAccess):
            return self._expr_contains_identifier(node.target, target_name)
        if isinstance(node, MethodCall):
            if self._expr_contains_identifier(node.target, target_name):
                return True
            return any(self._expr_contains_identifier(arg, target_name) for arg in node.arguments)
        if isinstance(node, MethodReference):
            return self._expr_contains_identifier(node.target, target_name)
        if isinstance(node, (list, tuple)):
            return any(self._expr_contains_identifier(item, target_name) for item in node)
        if isinstance(node, ASTNode) and hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, (ASTNode, list, tuple)):
                    if self._expr_contains_identifier(val, target_name):
                        return True
        return False

    def _check_boolean_condition(self, cond: Optional[ASTNode], context_label: str, line: int) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Valida expressão de condição booleana e retorna (true_vars, false_vars) para escopo de patterns (JLS §6.3)."""
        tv, fv, _, _ = self._check_boolean_condition_with_states(cond, context_label, line)
        return tv, fv

    def _check_boolean_condition_with_states(
        self, cond: Optional[ASTNode], context_label: str, line: int
    ) -> Tuple[
        Dict[str, Dict[str, Any]],
        Dict[str, Dict[str, Any]],
        Tuple[Set[Any], Set[Any], bool],
        Tuple[Set[Any], Set[Any], bool],
    ]:
        """Valida condição booleana retornando (true_vars, false_vars, true_state, false_state) conforme JLS §6.3 e §16."""
        if cond is None:
            cur = self._flow_snapshot()
            return {}, {}, cur, cur
        flow = self._check_expression_flow(cond)
        inferred = self.infer_type(cond)
        if inferred is not None and inferred not in ("boolean", "Boolean", "Object", "desconhecido", "var"):
            self.errors.append(
                SemanticError(
                    f"Condição de '{context_label}' deve possuir tipo 'boolean' (encontrado '{inferred}').",
                    line,
                )
            )
        cur = self._flow_snapshot()
        true_st = flow.true_state if flow.true_state is not None else cur
        false_st = flow.false_state if flow.false_state is not None else cur
        c_val = self._eval_constant_boolean(cond)
        if not self._flow_suppress_errors:
            self._reachability_const_bools[id(cond)] = c_val
        if c_val is True:
            false_st = self._flow_unreachable()
        elif c_val is False:
            true_st = self._flow_unreachable()
        return flow.true_vars, flow.false_vars, true_st, false_st

    def _collect_all_enum_constant_names(self) -> Set[str]:
        """Coleta nomes de constantes de todos os enums pré-indexados na unidade."""
        names: Set[str] = set()
        for enum_decl in self._enums.values():
            for c in getattr(enum_decl, "constants", []):
                if getattr(c, "name", None):
                    names.add(c.name)
        return names

    def _switch_label_constant_key(self, const_expr: ASTNode) -> Any:
        """Normaliza constante de label 'case' para detecção de duplicidade."""
        res = self._eval_constant_expr(const_expr)
        if res is not None:
            ctype, cval = res
            if ctype in ("byte", "short", "char", "int"):
                return ("int", cval)
            if ctype == "long":
                return ("long", cval)
            if ctype == "String":
                return ("lit", "STRING", str(cval))
            if ctype == "boolean":
                return ("lit", "BOOLEAN", "true" if cval else "false")
            return ("lit", ctype.upper(), str(cval))
        if isinstance(const_expr, Literal):
            kind = getattr(const_expr, "kind", "")
            val = getattr(const_expr, "value", None)
            if kind in ("NUM", "INT", "LONG"):
                val_s = str(val)
                parsed = self._parse_java_int_literal(val_s)
                if parsed is not None:
                    num_val, is_long_lit, _ = parsed
                    if kind == "LONG" or is_long_lit:
                        return ("long", num_val)
                    return ("int", num_val)
                return ("lit", val_s)
            if kind in ("FLOAT", "DOUBLE", "CHAR", "STRING", "TEXT_BLOCK", "BOOLEAN", "NULL"):
                return ("lit", kind, str(val))
            return ("lit", kind, str(val))
        if isinstance(const_expr, Identifier):
            return ("id", const_expr.name)
        if isinstance(const_expr, MemberAccess) and isinstance(const_expr.target, Identifier):
            return ("member", const_expr.target.name, const_expr.member_name)
        return None

    def _check_switch_constant_expr(self, const_expr: ASTNode, lb_line: int, enum_const_names: Set[str]):
        """Valida que constante de case é literal, constante de enum ou constante em tempo de compilação."""
        if isinstance(const_expr, Literal):
            kind = getattr(const_expr, "kind", "")
            val_s = str(getattr(const_expr, "value", ""))
            err_line = getattr(const_expr, "line", lb_line)
            if kind in ("FLOAT", "DOUBLE") and not self.enable_preview_primitive_patterns:
                self.errors.append(
                    SemanticError(
                        "Tipo de ponto flutuante em constante de 'case' requer recurso preview (JEP 530) no modo padrão Java SE 26 (JLS §14.11.1).",
                        err_line,
                    )
                )
            elif kind == "BOOLEAN" and not self.enable_preview_primitive_patterns:
                self.errors.append(
                    SemanticError(
                        "Constante booleana em 'case' requer recurso preview (JEP 530) e está desabilitada no modo padrão Java SE 26 (JLS §14.11.1).",
                        err_line,
                    )
                )
            elif (kind == "LONG" or (kind in ("NUM", "INT") and val_s.lower().endswith("l"))) and not self.enable_preview_primitive_patterns:
                self.errors.append(
                    SemanticError(
                        "Constante do tipo 'long' em 'case' requer recurso preview (JEP 530) e está desabilitada no modo padrão Java SE 26 (JLS §14.11.1).",
                        err_line,
                    )
                )
            return
        if isinstance(const_expr, Identifier):
            sym = self._lookup_var_symbol(const_expr.name)
            if sym is not None and sym.get("is_pattern_var", False):
                self.errors.append(
                    SemanticError(
                        f"Expressão de 'case' deve ser constante em tempo de compilação; '{const_expr.name}' é variável de pattern (JLS §14.11.1).",
                        getattr(const_expr, "line", lb_line),
                    )
                )
                return
            if const_expr.name in enum_const_names or const_expr.name in self._static_imports or self._has_wildcard_static_import:
                return
            if sym is None:
                self.errors.append(
                    SemanticError(
                        f"Constante de 'case' inválida ou não declarada: '{const_expr.name}' (JLS §14.11.1).",
                        getattr(const_expr, "line", lb_line),
                    )
                )
            elif sym.get("category") not in ("constante_enum", "constante_interface") and not sym.get("is_compile_constant", False):
                self.errors.append(
                    SemanticError(
                        f"Expressão de 'case' deve ser constante em tempo de compilação; '{const_expr.name}' não é constante (JLS §14.11.1 / §15.29).",
                        getattr(const_expr, "line", lb_line),
                    )
                )
            return
        if isinstance(const_expr, MemberAccess) and isinstance(const_expr.target, Identifier):
            t_name = const_expr.target.name
            if t_name in self._enums:
                enum_decl = self._enums[t_name]
                valid_c = {c.name for c in getattr(enum_decl, "constants", [])}
                if const_expr.member_name not in valid_c:
                    self.errors.append(
                        SemanticError(
                            f"Constante '{const_expr.member_name}' não pertence ao enum '{t_name}' (JLS §14.11.1).",
                            getattr(const_expr, "line", lb_line),
                        )
                    )
            return
        if isinstance(const_expr, UnaryOp) and const_expr.op in ("+", "-", "~"):
            self._check_switch_constant_expr(const_expr.operand, lb_line, enum_const_names)
            return
        self.check_expression(const_expr)

    def _is_statement_expression(self, expr: ASTNode) -> bool:
        if isinstance(expr, ExpressionStatement):
            expr = expr.expression
        if isinstance(expr, (Assignment, MethodCall, ObjectCreationExpression)):
            return True
        if isinstance(expr, UnaryOp) and expr.op in ("++", "--", "post++", "post--"):
            return True
        return False

    def _record_unresolved(self, msg: str):
        """Registra verificação semântica parcial/adiada por ausência de tipos externos ou classpath."""
        if msg not in self.unresolved_checks:
            self.unresolved_checks.append(msg)

    @staticmethod
    def _split_type_dims(type_str: str) -> Tuple[str, int]:
        """Separa dimensões '[]' finais de uma string de tipo, retornando (base, dims)."""
        s = (type_str or "").strip()
        dims = 0
        while s.endswith("[]"):
            dims += 1
            s = s[:-2].strip()
        return s, dims

    @staticmethod
    def _strip_generics(type_str: Optional[str]) -> Optional[str]:
        """Remove argumentos genéricos <...> preservando sufixos de array []."""
        if not type_str:
            return type_str
        base, dims = SemanticAnalyzer._split_type_dims(type_str)
        out: List[str] = []
        depth = 0
        for ch in base:
            if ch == "<":
                depth += 1
            elif ch == ">":
                if depth > 0:
                    depth -= 1
            elif depth == 0:
                out.append(ch)
        cleaned = "".join(out).strip()
        if dims > 0:
            return cleaned + ("[]" * dims)
        return cleaned

    @staticmethod
    def _extract_generic_args(type_str: Optional[str]) -> Tuple[Optional[str], List[str], int]:
        """Retorna (nome_base_sem_generics, lista_args_genericos, dims)."""
        if not type_str:
            return None, [], 0
        s, dims = SemanticAnalyzer._split_type_dims(type_str)
        lt = s.find("<")
        if lt == -1 or not s.endswith(">"):
            return s, [], dims
        base = s[:lt].strip()
        inner = s[lt + 1:-1]
        args: List[str] = []
        cur: List[str] = []
        depth = 0
        for ch in inner:
            if ch == "<":
                depth += 1
                cur.append(ch)
            elif ch == ">":
                depth = max(0, depth - 1)
                cur.append(ch)
            elif ch == "," and depth == 0:
                part = "".join(cur).strip()
                if part:
                    args.append(part)
                cur = []
            else:
                cur.append(ch)
        tail = "".join(cur).strip()
        if tail:
            args.append(tail)
        return base, args, dims

    def _normalize_type_str(self, tref: Any) -> Optional[str]:
        """Normaliza TypeReference ou string para representação textual consistente."""
        if tref is None:
            return None
        if isinstance(tref, str):
            return tref.strip() or None
        if isinstance(tref, WildcardType):
            if tref.bound_kind == "extends" and tref.bound_type is not None:
                b = self._normalize_type_str(tref.bound_type) or "Object"
                return f"? extends {b}"
            if tref.bound_kind == "super" and tref.bound_type is not None:
                b = self._normalize_type_str(tref.bound_type) or "Object"
                return f"? super {b}"
            return "?"
        if isinstance(tref, TypeReference):
            if getattr(tref, "full_name", None):
                return tref.full_name
            name = getattr(tref, "name", "")
            targs = getattr(tref, "type_arguments", []) or []
            if name and targs:
                args_str = ", ".join(self._normalize_type_str(a) or "?" for a in targs)
                name = f"{name}<{args_str}>"
            dims = getattr(tref, "dimensions", 0) or getattr(tref, "array_dimensions", 0) or 0
            return f"{name}{'[]' * dims}" if name else None
        if hasattr(tref, "pretty"):
            return tref.pretty()
        return str(tref)

    def _extract_qualified_name(self, node: Optional[ASTNode]) -> Optional[str]:
        """Extrai nome qualificado encadeado (ex: java.util.Arrays, System.out) se composto apenas de identificadores/acessos a membros."""
        if node is None:
            return None
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, MemberAccess):
            prefix = self._extract_qualified_name(node.target)
            if prefix:
                return f"{prefix}.{node.member_name}"
        return None

    def _simple_base_name(self, type_str: Optional[str]) -> Optional[str]:
        """Extrai o nome simples sem generics e sem qualificador de pacote."""
        if not type_str:
            return None
        stripped = self._strip_generics(type_str)
        if not stripped:
            return None
        base, dims = self._split_type_dims(stripped)
        simple = base.split(".")[-1]
        return simple + ("[]" * dims if dims > 0 else "")

    def _lookup_type_decl(self, type_name: Optional[str]) -> Optional[Tuple[str, ASTNode]]:
        """Busca declaração de tipo em escopos locais e na unidade de compilação."""
        if not type_name:
            return None
        stripped = self._strip_generics(type_name)
        if not stripped:
            return None
        base, dims = self._split_type_dims(stripped)
        if dims > 0 or base in self.PRIMITIVE_TYPES:
            return None
        simple = base.split(".")[-1]
        for lscope in reversed(self._local_declared_type_scopes):
            if base in lscope:
                return lscope[base]
            if simple in lscope:
                return lscope[simple]
        resolved_key = self._inheritance_analyzer.resolve_type_key(base)
        if resolved_key:
            meta = self._inheritance_analyzer.get_type_meta(resolved_key)
            if meta is not None:
                return (meta["kind"], meta["node"])
        if base in self._declared_types:
            if "." in base or getattr(self._inheritance_analyzer, "_current_unit", None) is None or base not in self._inheritance_analyzer._simple_to_keys:
                return self._declared_types[base]
        if simple in self._declared_types:
            if "." in base or getattr(self._inheritance_analyzer, "_current_unit", None) is None or simple not in self._inheritance_analyzer._simple_to_keys:
                return self._declared_types[simple]
        return None

    def _direct_supertypes(self, type_name: str) -> Tuple[List[str], bool]:
        """Retorna (supertipos_diretos, possui_supertipo_ou_tipo_externo)."""
        stripped = self._strip_generics(type_name) or ""
        base, dims = self._split_type_dims(stripped)
        if dims > 0:
            elem_base = base
            supers = ["Object", "Cloneable", "Serializable"]
            if elem_base not in self.PRIMITIVE_TYPES and elem_base != "Object":
                p_supers, ext = self._direct_supertypes(elem_base)
                for ps in p_supers:
                    supers.append(f"{ps}{'[]' * dims}")
                return supers, ext
            return supers, False

        simple = base.split(".")[-1]
        if simple == "Object":
            return [], False

        cur_key = self._inheritance_analyzer.resolve_type_key(base) or base
        tdecl = self._lookup_type_decl(cur_key)
        if tdecl is not None:
            tkind, node = tdecl
            supers: List[str] = []

            def _qualify_sup(raw_s: Optional[str]) -> Optional[str]:
                if not raw_s:
                    return None
                rbase = self._strip_generics(raw_s) or raw_s
                rk = self._inheritance_analyzer.resolve_type_key(rbase, context_type=cur_key)
                if rk and "<" in raw_s:
                    return rk + raw_s[raw_s.find("<"):]
                return rk or raw_s

            if tkind == "class":
                ext = getattr(node, "extends_type", None)
                if ext is not None:
                    ext_s = _qualify_sup(self._normalize_type_str(ext))
                    if ext_s:
                        supers.append(ext_s)
                else:
                    supers.append("Object")
                for impl in getattr(node, "implements_types", []):
                    impl_s = _qualify_sup(self._normalize_type_str(impl))
                    if impl_s:
                        supers.append(impl_s)
            elif tkind == "interface":
                exts = getattr(node, "extends_types", [])
                for e in exts:
                    e_s = _qualify_sup(self._normalize_type_str(e))
                    if e_s:
                        supers.append(e_s)
                supers.append("Object")
            elif tkind == "record":
                supers.append("Record")
                for impl in getattr(node, "implements_types", []):
                    impl_s = _qualify_sup(self._normalize_type_str(impl))
                    if impl_s:
                        supers.append(impl_s)
                supers.append("Object")
            elif tkind == "enum":
                supers.append(f"Enum<{cur_key}>")
                for impl in getattr(node, "implements_types", []):
                    impl_s = _qualify_sup(self._normalize_type_str(impl))
                    if impl_s:
                        supers.append(impl_s)
                supers.append("Object")
            elif tkind == "annotation_interface":
                supers.extend(["Annotation", "Object"])
            return supers, False

        ext = self._resolve_external_type(type_name)
        if ext is not None:
            tvar_map = self._type_var_mapping_for_type(type_name)
            ext_supers: List[str] = []
            if ext.super_class:
                sc = self._format_ext_type(ext.super_class) or ext.super_class
                sc = self._substitute_type_vars(sc, tvar_map) or sc
                ext_supers.append(sc)
            for ifc in ext.interfaces:
                ic = self._format_ext_type(ifc) or ifc
                ic = self._substitute_type_vars(ic, tvar_map) or ic
                if ic not in ext_supers:
                    ext_supers.append(ic)
            if ext.kind == "interface" and "Object" not in ext_supers:
                ext_supers.append("Object")
            elif ext.kind != "interface" and ext.fqn != "java.lang.Object" and not ext_supers:
                ext_supers.append("Object")
            return ext_supers, False

        if simple in self.BUILTIN_TYPE_SUPERTYPES:
            return list(self.BUILTIN_TYPE_SUPERTYPES[simple]), False
        if simple in self.KNOWN_EXCEPTION_PARENTS:
            return [self.KNOWN_EXCEPTION_PARENTS[simple], "Object"], False
        return ["Object"], True

    def _is_known_type_ignoring_other_pkgs(self, type_name: Optional[str]) -> bool:
        """Indica se o tipo está acessível/visível no escopo léxico da unidade atual (sem vazamento entre pacotes)."""
        if not type_name:
            return False
        if self._is_capture_var(type_name) or self._is_wildcard_arg(type_name):
            return True
        stripped = self._strip_generics(type_name)
        if not stripped:
            return False
        raw_base, _ = self._split_type_dims(stripped)
        if self._lookup_type_param_bounds(raw_base) is not None:
            return True
        if raw_base in self.PRIMITIVE_TYPES:
            return True
        if (
            raw_base in self.BUILTIN_TYPE_SUPERTYPES
            or raw_base in self.KNOWN_EXCEPTION_PARENTS
            or raw_base in self.BUILTIN_METHODS
            or raw_base in self.BUILTIN_CLASS_TYPES
            or raw_base in self.BUILTIN_INTERFACE_TYPES
        ):
            return True
        s = self._simple_base_name(type_name)
        if s and (
            s in self.PRIMITIVE_TYPES
            or s in self.BUILTIN_TYPE_SUPERTYPES
            or s in self.KNOWN_EXCEPTION_PARENTS
            or s in self.BUILTIN_METHODS
            or s in self.BUILTIN_CLASS_TYPES
            or s in self.BUILTIN_INTERFACE_TYPES
        ):
            return True
        for lscope in reversed(self._local_declared_type_scopes):
            if raw_base in lscope or (s and s in lscope):
                return True
        if self._inheritance_analyzer.resolve_type_key(raw_base) is not None:
            return True
        return self._resolve_external_type(raw_base) is not None

    def _is_known_type(self, type_name: Optional[str]) -> bool:
        """Indica se o tipo está declarado na unidade ou pertence ao núcleo embutido conhecido."""
        if not type_name:
            return False
        if self._is_capture_var(type_name) or self._is_wildcard_arg(type_name):
            return True
        stripped = self._strip_generics(type_name)
        if not stripped:
            return False
        raw_base, _ = self._split_type_dims(stripped)
        if self._lookup_type_param_bounds(raw_base) is not None:
            return True
        if (
            raw_base in self.BUILTIN_TYPE_SUPERTYPES
            or raw_base in self.BUILTIN_METHODS
            or raw_base in self.BUILTIN_CLASS_TYPES
            or raw_base in self.BUILTIN_INTERFACE_TYPES
        ):
            return True
        s = self._simple_base_name(type_name)
        if not s:
            return False
        base, dims = self._split_type_dims(s)
        if base in self.PRIMITIVE_TYPES:
            return True
        if (
            base in self.BUILTIN_TYPE_SUPERTYPES
            or base in self.KNOWN_EXCEPTION_PARENTS
            or base in self.BUILTIN_METHODS
            or base in self.BUILTIN_CLASS_TYPES
            or base in self.BUILTIN_INTERFACE_TYPES
        ):
            return True
        if self._lookup_type_decl(raw_base) is not None or self._lookup_type_decl(base) is not None:
            return True
        return self._resolve_external_type(raw_base) is not None

    def _is_final_or_closed_leaf(self, type_name: Optional[str]) -> bool:
        """Indica se um tipo não admite subtipos desconhecidos (final, record, enum ou array de final/primitivo)."""
        if not type_name:
            return False
        s = self._simple_base_name(type_name)
        if not s:
            return False
        base, dims = self._split_type_dims(s)
        if dims > 0:
            return base in self.PRIMITIVE_TYPES or self._is_final_or_closed_leaf(base)
        if base in self.PRIMITIVE_TYPES or base in self.BUILTIN_FINAL_TYPES:
            return True
        tdecl = self._lookup_type_decl(type_name) or self._lookup_type_decl(base)
        if tdecl is not None:
            tkind, node = tdecl
            if tkind in ("record", "enum"):
                return True
            if tkind == "class" and "final" in getattr(node, "modifiers", []):
                return True
        ext = self._resolve_external_type(type_name)
        if ext is not None:
            return ext.is_final or ext.kind in ("record", "enum")
        return False

    def _is_class_kind(self, type_name: Optional[str]) -> Optional[bool]:
        """Retorna True se é class/record/enum, False se é interface, None se desconhecido."""
        if not type_name:
            return None
        s = self._simple_base_name(type_name)
        if not s or s.endswith("[]"):
            return None
        tdecl = self._lookup_type_decl(type_name) or self._lookup_type_decl(s)
        if tdecl is not None:
            tkind, _ = tdecl
            return tkind in ("class", "record", "enum")
        ext = self._resolve_external_type(type_name)
        if ext is not None:
            return ext.kind in ("class", "record", "enum")
        if s in self.BUILTIN_CLASS_TYPES or s in self.KNOWN_EXCEPTION_PARENTS:
            return True
        if s in self.BUILTIN_INTERFACE_TYPES:
            return False
        return None

    def _push_type_params(self, type_params: Optional[List[ASTNode]], is_type_level: bool = False):
        """Empilha parâmetros de tipo declarados com seus respectivos limites superiores."""
        if not type_params:
            return
        mapping: Dict[str, List[str]] = {}
        for tp in type_params:
            tp_name = getattr(tp, "name", None)
            if not tp_name:
                continue
            raw_bounds = [
                self._normalize_type_str(b)
                for b in (getattr(tp, "bounds", []) or [])
            ]
            bounds = [b for b in raw_bounds if b] or ["Object"]
            mapping[tp_name] = bounds
        if mapping:
            self._active_type_params.append((mapping, is_type_level))

    def _lookup_type_param_bounds(self, name: Optional[str]) -> Optional[List[str]]:
        """Retorna limites superiores declarados se 'name' for parâmetro de tipo ativo no escopo."""
        if not name:
            return None
        s, dims = self._strip_type_dims_full(self._strip_generics(name) or "")
        if dims > 0 or not s or s in self._capture_vars:
            return None
        for mapping, is_tl in reversed(self._active_type_params):
            if is_tl and self._in_static_context:
                continue
            if s in mapping:
                return list(mapping[s])
        return None

    def _parse_wildcard_arg(self, arg_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Analisa argumento de tipo retornando ('unbounded'|'extends'|'super'|None, limite_ou_tipo)."""
        if not arg_str:
            return None, arg_str
        s = self._strip_leading_type_annotations(arg_str.strip()) or arg_str.strip()
        if s == "?":
            return "unbounded", None
        if s.startswith("?"):
            rest = s[1:].strip()
            if rest.startswith("extends "):
                bound = self._strip_leading_type_annotations(rest[len("extends "):].strip()) or "Object"
                return "extends", bound
            if rest.startswith("super "):
                bound = self._strip_leading_type_annotations(rest[len("super "):].strip()) or "Object"
                return "super", bound
        return None, s

    def _is_wildcard_arg(self, arg_str: Optional[str]) -> bool:
        """Indica se a representação textual é um wildcard ('?', '? extends T', '? super T')."""
        return self._parse_wildcard_arg(arg_str)[0] is not None

    def _is_capture_var(self, type_str: Optional[str]) -> bool:
        """Indica se type_str (ou sua base sem []) representa uma variável de captura CAP#k."""
        if not type_str:
            return False
        stripped = self._strip_generics(type_str) or ""
        base, _ = self._split_type_dims(stripped)
        return base in self._capture_vars

    def _type_param_decls_for_type(self, simple_base: Optional[str]) -> List[Tuple[str, List[str]]]:
        """Retorna lista ordenada [(param_name, [bounds...])] declarados para um tipo genérico."""
        if not simple_base:
            return []
        clean = self._strip_leading_type_annotations(simple_base) or simple_base
        stripped = self._strip_generics(clean)
        if not stripped:
            return []
        base, dims = self._split_type_dims(stripped)
        if dims > 0 or not base or base in self.PRIMITIVE_TYPES or base in ("void", "var", "null", "desconhecido"):
            return []
        if self._lookup_type_param_bounds(base) is not None:
            return []

        resolved_key = self._inheritance_analyzer.resolve_type_key(base) or base
        tdecl = self._lookup_type_decl(resolved_key)
        if tdecl is None and resolved_key != base:
            tdecl = self._lookup_type_decl(base)
        if tdecl is not None:
            dkind, tnode = tdecl
            if dkind in ("enum", "annotation_interface"):
                return []
            decls: List[Tuple[str, List[str]]] = []
            for tp in (getattr(tnode, "type_parameters", []) or []):
                tp_name = getattr(tp, "name", None)
                if not tp_name:
                    continue
                raw_bounds = [
                    self._normalize_type_str(b)
                    for b in (getattr(tp, "bounds", []) or [])
                ]
                decls.append((tp_name, [b for b in raw_bounds if b] or ["Object"]))
            return decls

        ext = self._resolve_external_type(base)
        if ext is not None:
            if not ext.type_parameters:
                return []
            decls = []
            for tp_name, raw_bs in ext.type_parameters:
                fmt_bs = [self._format_ext_type(b) or b for b in (raw_bs or [])]
                decls.append((tp_name, [b for b in fmt_bs if b] or ["Object"]))
            return decls

        simple = base.split(".")[-1]
        is_unqualified = "." not in base
        matches_compat = self.BUILTIN_COMPAT_FQNS.get(simple) == base or f"java.lang.{simple}" == base
        if is_unqualified:
            if self._is_explicitly_imported_from_other_pkg(simple):
                return []
            if simple in self.BUILTIN_TYPE_PARAMS:
                return [(pname, ["Object"]) for pname in self.BUILTIN_TYPE_PARAMS[simple]]
        elif base in self.BUILTIN_TYPE_PARAMS:
            return [(pname, ["Object"]) for pname in self.BUILTIN_TYPE_PARAMS[base]]
        elif matches_compat and simple in self.BUILTIN_TYPE_PARAMS:
            return [(pname, ["Object"]) for pname in self.BUILTIN_TYPE_PARAMS[simple]]
        return []

    def _canonical_type_family_key(self, type_str: Optional[str]) -> Optional[str]:
        """Chave canônica (FQN externo ou chave interna ou nome simples) da família do tipo para interseções."""
        if not type_str:
            return None
        stripped = self._strip_generics(type_str)
        if not stripped:
            return None
        base, dims = self._split_type_dims(stripped)
        if not base:
            return None
        internal_key = self._inheritance_analyzer.resolve_type_key(base)
        if internal_key:
            return f"int:{internal_key}{'[]' * dims}"
        ext = self._resolve_external_type(base)
        if ext is not None:
            return f"ext:{ext.fqn}{'[]' * dims}"
        simple = self._simple_base_name(base) or base
        return f"sim:{simple}{'[]' * dims}"

    def _collect_param_supertypes(self, type_str: str) -> Dict[str, List[str]]:
        """Coleta supertipos parametrizados alcançáveis indexados pela família canônica do tipo."""
        result: Dict[str, List[str]] = {}
        queue: List[str] = [type_str]
        seen: Set[str] = set()
        while queue:
            cur = queue.pop(0)
            if not cur or cur in seen:
                continue
            seen.add(cur)
            _, args, _ = self._extract_generic_args(cur)
            if args:
                fam = self._canonical_type_family_key(cur)
                if fam:
                    bucket = result.setdefault(fam, [])
                    if cur not in bucket:
                        bucket.append(cur)
            supers, _ = self._direct_supertypes(cur)
            tvar_map = self._type_var_mapping_for_type(cur)
            for s in supers:
                s_sub = self._substitute_type_vars(s, tvar_map) or s
                if s_sub and s_sub not in seen:
                    queue.append(s_sub)
        return result

    def _type_args_intersect_compatible(
        self,
        sa: str,
        sb: str,
        visited: Set[Tuple[str, str]],
    ) -> Optional[bool]:
        """Verifica se existe instanciação comum compatível entre dois argumentos genéricos."""
        a = (self._strip_leading_type_annotations(sa) or sa).strip()
        b = (self._strip_leading_type_annotations(sb) or sb).strip()
        if not a or not b:
            return None
        if a == b:
            return True
        ka, ba = self._parse_wildcard_arg(a)
        kb, bb = self._parse_wildcard_arg(b)
        if ka == "unbounded" or kb == "unbounded":
            return True

        # Desempacota captura se um lado for CAP#k e o outro não for wildcard
        if self._is_capture_var(a) and kb is None and not self._is_capture_var(b):
            cap = self._capture_vars.get(self._split_type_dims(self._strip_generics(a) or a)[0], {})
            lb = cap.get("lower_bound")
            if lb and self._is_subtype(lb, b) is False:
                return False
            for ub in cap.get("upper_bounds", []) or []:
                if self._are_intersection_types_compatible(b, ub, visited) is False:
                    return False
            return True
        if self._is_capture_var(b) and ka is None and not self._is_capture_var(a):
            return self._type_args_intersect_compatible(b, a, visited)

        if ka is None and kb is None:
            if self._is_capture_var(a) or self._is_capture_var(b):
                return True
            if self._lookup_type_param_bounds(a) is not None or self._lookup_type_param_bounds(b) is not None:
                return self._are_intersection_types_compatible(a, b, visited)
            a_base, a_args, a_dims = self._extract_generic_args(a)
            b_base, b_args, b_dims = self._extract_generic_args(b)
            if a_dims != b_dims:
                return False
            if self._canonical_type_family_key(a_base) != self._canonical_type_family_key(b_base):
                if not self._is_known_type(a) or not self._is_known_type(b):
                    return None
                return False
            if len(a_args) != len(b_args):
                return False
            saw_none = False
            for xa, xb in zip(a_args, b_args):
                r = self._type_args_intersect_compatible(xa, xb, visited)
                if r is False:
                    return False
                if r is None:
                    saw_none = True
            return None if saw_none else True

        if ka == "extends" and kb is None:
            r = self._is_subtype(b, ba or "Object")
            return r
        if kb == "extends" and ka is None:
            return self._is_subtype(a, bb or "Object")
        if ka == "super" and kb is None:
            return self._is_subtype(ba or "Object", b)
        if kb == "super" and ka is None:
            return self._is_subtype(bb or "Object", a)
        if ka == "extends" and kb == "extends":
            return self._are_intersection_types_compatible(ba or "Object", bb or "Object", visited)
        if ka == "super" and kb == "extends":
            return self._is_subtype(ba or "Object", bb or "Object")
        if ka == "extends" and kb == "super":
            return self._is_subtype(bb or "Object", ba or "Object")
        return True  # dois '? super' possuem supertipo comum (ex: Object)

    def _are_intersection_types_compatible(
        self,
        t1: Optional[str],
        t2: Optional[str],
        visited: Optional[Set[Tuple[str, str]]] = None,
    ) -> Optional[bool]:
        """Verifica conforme JLS §4.5/§4.9 se dois tipos de referência admitem interseção não-vazia."""
        if not t1 or not t2:
            return None
        c1 = (self._strip_leading_type_annotations(t1) or t1).strip()
        c2 = (self._strip_leading_type_annotations(t2) or t2).strip()
        if not c1 or not c2:
            return None
        if c1 == c2 or c1 in ("Object", "java.lang.Object") or c2 in ("Object", "java.lang.Object"):
            return True

        vset = visited if visited is not None else set()
        vkey = (c1, c2) if c1 <= c2 else (c2, c1)
        if vkey in vset:
            return True
        vset.add(vkey)

        tp1_bounds = self._lookup_type_param_bounds(c1)
        if tp1_bounds is not None:
            saw_none = False
            for ub in tp1_bounds:
                r = self._are_intersection_types_compatible(ub, c2, vset)
                if r is False:
                    return False
                if r is None:
                    saw_none = True
            return None if saw_none else True

        tp2_bounds = self._lookup_type_param_bounds(c2)
        if tp2_bounds is not None:
            saw_none = False
            for ub in tp2_bounds:
                r = self._are_intersection_types_compatible(c1, ub, vset)
                if r is False:
                    return False
                if r is None:
                    saw_none = True
            return None if saw_none else True

        if self._is_capture_var(c1):
            cap1 = self._capture_vars.get(self._split_type_dims(self._strip_generics(c1) or c1)[0], {})
            saw_none = False
            for ub in cap1.get("upper_bounds", []) or []:
                r = self._are_intersection_types_compatible(ub, c2, vset)
                if r is False:
                    return False
                if r is None:
                    saw_none = True
            return None if saw_none else True

        if self._is_capture_var(c2):
            return self._are_intersection_types_compatible(c2, c1, vset)

        disj = self._are_types_disjoint(c1, c2)
        if disj is True:
            return False
        if disj is None:
            return None

        # Mesmo que _are_types_disjoint não seja True (ex: duas interfaces parametrizadas),
        # verifica conflito de argumentos em supertipos genéricos compartilhados (JLS §8.1.5 / §4.5).
        psups1 = self._collect_param_supertypes(c1)
        psups2 = self._collect_param_supertypes(c2)
        saw_unknown = False
        for fam, list1 in psups1.items():
            list2 = psups2.get(fam)
            if not list2:
                continue
            for pt1 in list1:
                _, a1, _ = self._extract_generic_args(pt1)
                for pt2 in list2:
                    _, a2, _ = self._extract_generic_args(pt2)
                    if len(a1) != len(a2):
                        continue
                    for xa, xb in zip(a1, a2):
                        r = self._type_args_intersect_compatible(xa, xb, vset)
                        if r is False:
                            return False
                        if r is None:
                            saw_unknown = True
        return None if saw_unknown else True

    def _combine_upper_bounds(self, explicit_bound: str, decl_bounds: List[str]) -> List[str]:
        """Combina limite explícito de '? extends T' com os limites declarados do parâmetro de tipo (glb)."""
        if not decl_bounds or decl_bounds == ["Object"]:
            return [explicit_bound]
        result: List[str] = [explicit_bound]
        for db in decl_bounds:
            if db == "Object":
                continue
            if self._is_subtype(explicit_bound, db) is True:
                continue
            if self._is_subtype(db, explicit_bound) is True:
                result = [x for x in result if x != explicit_bound]
                if db not in result:
                    result.append(db)
            elif db not in result:
                result.append(db)
        return result or ["Object"]

    def _capture_convert(self, type_str: Optional[str]) -> Optional[str]:
        """
        Aplica conversão de captura (capture conversion — JLS §5.1.10) no nível superior
        de um tipo parametrizado contendo wildcards, preservando limites superiores,
        inferiores e limites recursivos F-bounded.
        """
        if not type_str:
            return type_str
        clean = self._strip_leading_type_annotations(type_str) or type_str
        s, dims = self._strip_type_dims_full(clean)
        if dims > 0:
            return clean
        base, args, _ = self._extract_generic_args(s)
        if not base or not args or not any(self._is_wildcard_arg(a) for a in args):
            return clean

        simple = self._simple_base_name(base) or base
        decls = self._type_param_decls_for_type(base) or self._type_param_decls_for_type(simple)

        new_args: List[str] = []
        subst_map: Dict[str, str] = {}
        wildcard_indices: List[Tuple[int, str, Optional[str], str]] = []

        for idx, raw_arg in enumerate(args):
            pname = decls[idx][0] if idx < len(decls) else f"_T{idx}"
            wk, wb = self._parse_wildcard_arg(raw_arg)
            if wk is None:
                c_arg = raw_arg.strip()
                new_args.append(c_arg)
                subst_map[pname] = c_arg
            else:
                self._capture_counter += 1
                cap_name = f"CAP#{self._capture_counter}"
                new_args.append(cap_name)
                subst_map[pname] = cap_name
                wildcard_indices.append((idx, wk, wb, cap_name))

        for idx, wk, wb, cap_name in wildcard_indices:
            raw_decl_bounds = decls[idx][1] if idx < len(decls) else ["Object"]
            decl_bounds = [
                self._substitute_type_vars(b, subst_map) or b
                for b in raw_decl_bounds
            ] or ["Object"]
            if wk == "unbounded":
                uppers = decl_bounds
                lower = None
            elif wk == "extends":
                uppers = self._combine_upper_bounds(wb or "Object", decl_bounds)
                lower = None
            else:  # super
                uppers = decl_bounds
                lower = wb
            self._capture_vars[cap_name] = {
                "name": cap_name,
                "upper_bounds": uppers,
                "lower_bound": lower,
            }

        return f"{base}<{', '.join(new_args)}>"

    def _invariant_type_args_equal(self, a_str: str, b_str: str) -> bool:
        """Verifica igualdade invariante entre dois argumentos de tipo genérico (JLS §4.5.1)."""
        a_s = (self._strip_leading_type_annotations(a_str) or a_str).strip()
        b_s = (self._strip_leading_type_annotations(b_str) or b_str).strip()
        if a_s == b_s:
            return True
        ka, ba = self._parse_wildcard_arg(a_s)
        kb, bb = self._parse_wildcard_arg(b_s)
        if ka is not None or kb is not None:
            if ka != kb:
                return False
            if ka == "unbounded":
                return True
            return self._invariant_type_args_equal(ba or "", bb or "")
        if self._is_capture_var(a_s) or self._is_capture_var(b_s):
            return a_s == b_s
        a_base, a_args, a_dims = self._extract_generic_args(a_s)
        b_base, b_args, b_dims = self._extract_generic_args(b_s)
        if a_dims != b_dims:
            return False
        if self._simple_base_name(a_base) != self._simple_base_name(b_base):
            return False
        if len(a_args) != len(b_args):
            return False
        return all(self._invariant_type_args_equal(x, y) for x, y in zip(a_args, b_args))

    def _wildcard_arg_contained_in(self, sub_arg: str, sup_arg: str) -> Optional[bool]:
        """Verifica relação de contenção de argumentos de tipo sa <= sb segundo JLS §4.5.1."""
        sa_k, sa_b = self._parse_wildcard_arg(sub_arg)
        sb_k, sb_b = self._parse_wildcard_arg(sup_arg)

        if sb_k == "unbounded":
            return True

        if sb_k == "extends":
            target_ub = sb_b or "Object"
            if sa_k is None:
                return self._is_subtype(sub_arg.strip(), target_ub)
            if sa_k == "extends":
                return self._is_subtype(sa_b or "Object", target_ub)
            # '?' e '? super L' possuem limite superior implícito Object
            return self._is_subtype("Object", target_ub)

        if sb_k == "super":
            target_lb = sb_b or "Object"
            if sa_k is None:
                return self._is_subtype(target_lb, sub_arg.strip())
            if sa_k == "super":
                return self._is_subtype(target_lb, sa_b or "Object")
            return False

        # sb não é wildcard: exige invariância
        if sa_k is not None:
            return False
        return self._invariant_type_args_equal(sub_arg, sup_arg)

    def _generic_args_compatible(self, sub_full: str, sup_full: str) -> Optional[bool]:
        """Verifica compatibilidade entre argumentos genéricos com contenção de wildcards (JLS §4.5.1)."""
        _, sub_args, sub_dims = self._extract_generic_args(sub_full)
        _, sup_args, sup_dims = self._extract_generic_args(sup_full)
        if sub_dims != sup_dims:
            return False
        if not sub_args or not sup_args:
            return True
        if len(sub_args) != len(sup_args):
            return False
        saw_unknown = False
        for sa, sb in zip(sub_args, sup_args):
            res = self._wildcard_arg_contained_in(sa, sb)
            if res is False:
                return False
            if res is None:
                saw_unknown = True
        return None if saw_unknown else True

    def _is_subtype(self, sub: Optional[str], sup: Optional[str]) -> Optional[bool]:
        """Retorna True se sub <: sup, False se provadamente não, ou None se envolver hierarquia externa não resolvida."""
        if not sub or not sup:
            return None
        sub_clean = (self._strip_leading_type_annotations(sub) or sub).strip()
        sup_clean = (self._strip_leading_type_annotations(sup) or sup).strip()
        if sub_clean == sup_clean:
            return True

        sub_s = self._simple_base_name(sub_clean)
        sup_s = self._simple_base_name(sup_clean)
        if not sub_s or not sup_s:
            return None
        if sub_s in ("var", "desconhecido") or sup_s in ("var", "desconhecido"):
            return None
        if sub_s == "null":
            return sup_s not in self.PRIMITIVE_TYPES

        sub_base, sub_dims = self._split_type_dims(sub_s)
        sup_base, sup_dims = self._split_type_dims(sup_s)

        if sub_dims == 0 and sup_dims == 0 and (sub_base in self.PRIMITIVE_TYPES or sup_base in self.PRIMITIVE_TYPES):
            return sub_base == sup_base

        # Arrays (antes de variáveis de captura para tratar CAP#k[] corretamente)
        if sub_dims > 0 or sup_dims > 0:
            if sub_dims > 0 and sup_dims == 0:
                return sup_base in ("Object", "Cloneable", "Serializable")
            if sub_dims > sup_dims and sup_dims > 0:
                return sup_base in ("Object", "Cloneable", "Serializable")
            if sub_dims < sup_dims:
                return False
            if sub_base in self.PRIMITIVE_TYPES or sup_base in self.PRIMITIVE_TYPES:
                return sub_base == sup_base
            sub_elem_full = self._strip_leading_type_annotations(sub_clean)[:-2 * sub_dims].strip()
            sup_elem_full = self._strip_leading_type_annotations(sup_clean)[:-2 * sup_dims].strip()
            return self._is_subtype(sub_elem_full, sup_elem_full)

        visit_key = (sub_clean, sup_clean)
        if visit_key in self._subtype_visiting:
            return False
        self._subtype_visiting.add(visit_key)
        try:
            # Variável de captura CAP#k no lado esquerdo
            if self._is_capture_var(sub_base):
                if sup_base == "Object":
                    return True
                if self._is_capture_var(sup_base):
                    if sub_base == sup_base:
                        return True
                    sup_cap = self._capture_vars[sup_base]
                    lb = sup_cap.get("lower_bound")
                    if lb is not None:
                        return self._is_subtype(sub_clean, lb)
                    return False
                sub_cap = self._capture_vars[sub_base]
                saw_none = False
                for ub in sub_cap.get("upper_bounds", ["Object"]):
                    r = self._is_subtype(ub, sup_clean)
                    if r is True:
                        return True
                    if r is None:
                        saw_none = True
                return None if saw_none else False

            # Variável de captura CAP#k no lado direito
            if self._is_capture_var(sup_base):
                sup_cap = self._capture_vars[sup_base]
                lb = sup_cap.get("lower_bound")
                if lb is not None:
                    return self._is_subtype(sub_clean, lb)
                return False

            # Parâmetro de tipo ativo em escopo com limites declarados
            sub_tp_bounds = self._lookup_type_param_bounds(sub_base)
            if sub_tp_bounds is not None:
                if sub_base == sup_base or sup_base == "Object":
                    return True
                saw_none = False
                for ub in sub_tp_bounds:
                    r = self._is_subtype(ub, sup_clean)
                    if r is True:
                        return True
                    if r is None:
                        saw_none = True
                return None if saw_none else False

            if self._lookup_type_param_bounds(sup_base) is not None:
                return sub_base == sup_base

            sub_raw_b = self._strip_generics(sub_clean) or sub_clean
            sup_raw_b = self._strip_generics(sup_clean) or sup_clean
            same_qualified = ("." in sub_raw_b and "." in sup_raw_b and sub_raw_b != sup_raw_b)
            if sub_s == sup_s and not same_qualified:
                return self._generic_args_compatible(sub_clean, sup_clean)
            if sup_s == "Object":
                return True

            # Captura de nível superior para subtipos parametrizados com wildcards (JLS §4.10.2)
            eff_sub = self._capture_convert(sub_clean) or sub_clean
            queue: List[str] = [eff_sub]
            visited: Set[str] = set()
            saw_external = False
            while queue:
                cur = queue.pop(0)
                cur_b = self._strip_generics(cur) or cur
                cur_ext = self._resolve_external_type(cur_b)
                cur_simple = self._simple_base_name(cur) or ""
                cur_vkey = cur_ext.fqn if cur_ext is not None else (cur_b if "." in cur_b else cur_simple)
                if cur_vkey in visited:
                    continue
                visited.add(cur_vkey)
                cur_matches_sup = (
                    (cur_b == sup_raw_b) if ("." in cur_b and "." in sup_raw_b) else (cur_simple == sup_s)
                )
                if cur_matches_sup:
                    return self._generic_args_compatible(cur, sup_clean)
                supers, is_ext = self._direct_supertypes(cur)
                if is_ext:
                    saw_external = True
                tvar_map = self._type_var_mapping_for_type(cur)
                for s in supers:
                    s = self._substitute_type_vars(s, tvar_map) or s
                    s_b = self._strip_generics(s) or s
                    s_simple = self._simple_base_name(s) or ""
                    s_matches_sup = (
                        (s_b == sup_raw_b) if ("." in s_b and "." in sup_raw_b) else (s_simple == sup_s)
                    )
                    if s_matches_sup:
                        _, cur_gen_args, _ = self._extract_generic_args(s)
                        _, sup_gen_args, _ = self._extract_generic_args(sup_clean)
                        if cur_gen_args and sup_gen_args:
                            return self._generic_args_compatible(s, sup_clean)
                        return True
                    s_ext = self._resolve_external_type(s_b)
                    s_vkey = s_ext.fqn if s_ext is not None else (s_b if "." in s_b else s_simple)
                    if s_vkey not in visited:
                        queue.append(s)

            if saw_external:
                return None
            return False
        finally:
            self._subtype_visiting.discard(visit_key)

    def _get_sealed_permitted_types(self, type_name: str) -> List[str]:
        """Obtém os subtipos permitidos de um tipo 'sealed' (explícitos via 'permits' ou implícitos na unidade)."""
        tdecl = self._lookup_type_decl(type_name)
        if tdecl is None:
            return []
        tkind, node = tdecl
        if "sealed" not in getattr(node, "modifiers", []):
            return []
        permits = getattr(node, "permits_types", [])
        if permits:
            res: List[str] = []
            for p in permits:
                ps = self._normalize_type_str(p)
                if ps:
                    res.append(ps)
            return res

        target_simple = self._simple_base_name(type_name)
        implicit: List[str] = []
        seen: Set[str] = set()

        def check_candidate(cname: str, ckind: str, cnode: ASTNode):
            if cname in seen or cname == target_simple:
                return
            refs: List[ASTNode] = []
            if ckind == "class":
                if getattr(cnode, "extends_type", None) is not None:
                    refs.append(cnode.extends_type)
                refs.extend(getattr(cnode, "implements_types", []))
            elif ckind == "interface":
                refs.extend(getattr(cnode, "extends_types", []))
            elif ckind in ("record", "enum"):
                refs.extend(getattr(cnode, "implements_types", []))
            for r in refs:
                r_simple = self._simple_base_name(self._normalize_type_str(r))
                if r_simple == target_simple:
                    seen.add(cname)
                    implicit.append(cname)
                    break

        for scope in self._local_declared_type_scopes:
            for cname, (ckind, cnode) in scope.items():
                check_candidate(cname, ckind, cnode)
        for cname, (ckind, cnode) in self._declared_types.items():
            check_candidate(cname, ckind, cnode)
        return implicit

    def _are_preview_primitive_types_disjoint(self, s1: str, s2: str) -> Optional[bool]:
        """Verifica disjunção parcial para modo preview JEP 530 entre tipos primitivos e referências."""
        if s1 in self.PRIMITIVE_TYPES and s2 in self.PRIMITIVE_TYPES:
            if s1 == s2:
                return False
            if s1 == "boolean" or s2 == "boolean":
                return True
            return False

        prim, ref = (s1, s2) if s1 in self.PRIMITIVE_TYPES else (s2, s1)
        ref_base, ref_dims = self._split_type_dims(ref)
        if ref_dims > 0:
            return True
        if ref_base in ("Object", "Serializable", "Comparable"):
            return False
        if ref_base == "Number":
            return prim == "boolean"
        if ref_base in self.WRAPPER_TO_PRIMITIVE:
            wp = self.WRAPPER_TO_PRIMITIVE[ref_base]
            if prim == "boolean" or wp == "boolean":
                return prim != wp
            return False
        if not self._is_known_type(ref_base):
            return None
        return True

    def _are_types_disjoint(self, t1: Optional[str], t2: Optional[str]) -> Optional[bool]:
        """Retorna True se dois tipos são provadamente disjuntos (pattern inaplicável/incompatível), False ou None."""
        if not t1 or not t2:
            return None
        s1 = self._simple_base_name(t1)
        s2 = self._simple_base_name(t2)
        if not s1 or not s2 or "Object" in (s1, s2) or "var" in (s1, s2) or "desconhecido" in (s1, s2):
            return False
        if s1 in self.PRIMITIVE_TYPES or s2 in self.PRIMITIVE_TYPES:
            if not self.enable_preview_primitive_patterns:
                return s1 != s2
            return self._are_preview_primitive_types_disjoint(s1, s2)
        sub12 = self._is_subtype(t1, t2)
        sub21 = self._is_subtype(t2, t1)
        if sub12 is True or sub21 is True:
            return False

        b1, d1 = self._split_type_dims(s1)
        b2, d2 = self._split_type_dims(s2)
        if (d1 > 0 or d2 > 0) and d1 != d2:
            min_b = b2 if d1 > d2 else b1
            if min_b in ("Object", "Cloneable", "Serializable"):
                return False
            return True
        if d1 > 0 and d2 > 0:
            if b1 in self.PRIMITIVE_TYPES or b2 in self.PRIMITIVE_TYPES:
                return b1 != b2
            return self._are_types_disjoint(b1, b2)

        if self._is_final_or_closed_leaf(t1) or self._is_final_or_closed_leaf(t2):
            if sub12 is False and sub21 is False:
                return True

        k1 = self._is_class_kind(t1)
        k2 = self._is_class_kind(t2)
        if k1 is True and k2 is True and sub12 is False and sub21 is False:
            return True

        # Verifica hierarquia sealed fechada de t1 contra t2 e vice-versa
        for sealed_t, other_t in ((t1, t2), (t2, t1)):
            permits = self._get_sealed_permitted_types(sealed_t)
            if permits:
                all_disjoint = True
                for pt in permits:
                    d_res = self._are_types_disjoint(pt, other_t)
                    if d_res is not True:
                        all_disjoint = False
                        break
                if all_disjoint:
                    return True

        if not self._is_known_type(t1) or not self._is_known_type(t2):
            return None
        return False

    def _substitute_type_str(self, type_str: str, subst: Dict[str, str]) -> str:
        """Substitui parâmetros genéricos em um tipo de componente de record usando o mapa subst."""
        if not subst or not type_str:
            return type_str
        base, args, dims = self._extract_generic_args(type_str)
        if base in subst and not args:
            return subst[base] + ("[]" * dims)
        if args:
            new_args = [self._substitute_type_str(a, subst) for a in args]
            return f"{base}<{', '.join(new_args)}>{'[]' * dims}"
        return type_str

    def _get_record_component_types(
        self,
        rec_type_ref_or_name: Any,
        seen_records: Optional[Set[str]] = None,
    ) -> Optional[List[str]]:
        """Retorna os tipos (com substituição genérica quando possível) dos componentes de um record."""
        r_str = self._normalize_type_str(rec_type_ref_or_name)
        if not r_str:
            return None
        tdecl = self._lookup_type_decl(r_str)
        if tdecl is None or tdecl[0] != "record" or not isinstance(tdecl[1], RecordDeclaration):
            return None
        rnode = tdecl[1]
        subst: Dict[str, str] = {}
        _, gargs, _ = self._extract_generic_args(r_str)
        tparams = getattr(rnode, "type_parameters", []) or []
        if gargs and tparams:
            for tp, ga in zip(tparams, gargs):
                tp_name = getattr(tp, "name", None) or str(tp)
                if ga.strip() == "?":
                    subst[tp_name] = "Object"
                elif ga.strip().startswith("? extends "):
                    subst[tp_name] = ga.strip()[len("? extends "):].strip()
                elif ga.strip().startswith("? super "):
                    subst[tp_name] = "Object"
                else:
                    subst[tp_name] = ga.strip()
        elif tparams and not gargs:
            # Record bruto (raw): parâmetros genéricos substituem para Object
            for tp in tparams:
                tp_name = getattr(tp, "name", None) or str(tp)
                subst[tp_name] = "Object"

        comp_types: List[str] = []
        for comp in getattr(rnode, "components", []):
            ct = getattr(comp, "effective_type", None) or self._normalize_type_str(getattr(comp, "type_ref", None)) or "Object"
            comp_types.append(self._substitute_type_str(ct, subst))
        return comp_types

    def _check_pattern_type_compatibility(self, source_type: Optional[str], pat_type: Optional[str], line: int, is_component: bool):
        """Verifica aplicabilidade/compatibilidade entre o tipo alvo/seletor e o tipo de um pattern."""
        if not source_type or not pat_type or pat_type == "var":
            return
        disjoint = self._are_types_disjoint(source_type, pat_type)
        if disjoint is True:
            ctx = "componente de record" if is_component else "expressão/seletor"
            self.errors.append(
                SemanticError(
                    f"Tipos incompatíveis: {ctx} do tipo '{source_type}' não pode casar com pattern de tipo '{pat_type}' (JLS §14.30.3 / §15.20.2).",
                    line,
                )
            )
        elif disjoint is None and (not self._is_known_type(source_type) or not self._is_known_type(pat_type)):
            self._record_unresolved(
                f"Compatibilidade entre '{source_type}' e pattern '{pat_type}' envolve tipo externo não declarado na unidade."
            )

    def _analyze_pattern(
        self,
        pattern: Optional[ASTNode],
        selector_type: Optional[str] = None,
        is_component: bool = False,
        expected_comp_type: Optional[str] = None,
        seen_pattern_vars: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Valida sintaxe contextual, variáveis, record arity, generics e preview rules de um pattern (JLS §14.30)."""
        collected: Dict[str, Dict[str, Any]] = {}
        if pattern is None:
            return collected
        if seen_pattern_vars is None:
            seen_pattern_vars = {}

        if isinstance(pattern, MatchAllPattern):
            if not is_component:
                self.errors.append(
                    SemanticError(
                        "Pattern irrestrito '_' (match-all) só é permitido como componente dentro de um record pattern (JLS §14.30.1).",
                        getattr(pattern, "line", 1),
                    )
                )
            return collected

        if isinstance(pattern, TypePattern):
            p_line = getattr(pattern, "line", 1)
            tref = getattr(pattern, "type_ref", None)
            is_var = getattr(pattern, "is_var", False) or (tref is not None and getattr(tref, "name", "") == "var")
            is_unnamed = getattr(pattern, "is_unnamed", False) or getattr(pattern, "name", "") == "_"
            mods = getattr(pattern, "modifiers", []) or []
            is_final = getattr(pattern, "is_final", False) or ("final" in mods)
            for mod in mods:
                if mod != "final":
                    self.errors.append(
                        SemanticError(
                            f"Modificador '{mod}' não é permitido em TypePattern; apenas 'final' e anotações são válidos (JLS §14.30.1).",
                            p_line,
                        )
                    )
            self._analyze_annotations(
                getattr(pattern, "annotations", []),
                valid_targets={"LOCAL_VARIABLE"},
                adjacent_type_ref=tref,
            )
            if tref is not None and not is_var:
                self._check_type_ref_annotations(tref)

            if is_var and not is_component:
                self.errors.append(
                    SemanticError(
                        "Inferência de tipo 'var' em pattern só é permitida para componentes dentro de record pattern (JLS §14.30.1).",
                        p_line,
                    )
                )

            raw_type = self._normalize_type_str(tref) or getattr(pattern, "type_name", None)
            if raw_type == "void":
                self.errors.append(
                    SemanticError("O tipo 'void' não é permitido em pattern (JLS §14.30.1).", p_line)
                )

            target_source_type = expected_comp_type if is_component else selector_type
            resolved_var_type = (expected_comp_type or "Object") if is_var else (raw_type or "Object")

            raw_base, raw_dims = self._split_type_dims(self._strip_generics(raw_type) or "")
            if (not is_var) and raw_dims == 0 and raw_base in self.PRIMITIVE_TYPES:
                if not self.enable_preview_primitive_patterns:
                    ctx_msg = "componente de RecordPattern" if is_component else "nível superior"
                    self.errors.append(
                        SemanticError(
                            f"Pattern com tipo primitivo '{raw_type}' em {ctx_msg} pertence ao recurso preview (JEP 530) e está desabilitado no modo padrão Java SE 26 (JLS §14.30.1).",
                            p_line,
                        )
                    )
                elif target_source_type:
                    self._check_pattern_type_compatibility(target_source_type, raw_type, p_line, is_component=is_component)
            else:
                if not is_component and target_source_type:
                    src_base, src_dims = self._split_type_dims(self._strip_generics(target_source_type) or "")
                    if src_dims == 0 and src_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                        self.errors.append(
                            SemanticError(
                                f"Expressão/seletor de tipo primitivo '{target_source_type}' não suporta pattern matching no modo padrão Java SE 26 (JLS §14.30.3 / §15.20.2).",
                                p_line,
                            )
                        )
                    else:
                        self._check_pattern_type_compatibility(target_source_type, raw_type, p_line, is_component=False)
                elif is_component and not is_var and target_source_type:
                    self._check_pattern_type_compatibility(target_source_type, raw_type, p_line, is_component=True)

            vname = getattr(pattern, "name", None)
            if not is_unnamed and vname:
                if vname in seen_pattern_vars:
                    self.errors.append(
                        SemanticError(
                            f"Variável de pattern '{vname}' declarada novamente no mesmo pattern (linha {seen_pattern_vars[vname]} — JLS §14.30.1).",
                            p_line,
                        )
                    )
                else:
                    conflict = self._find_local_var_info(vname)
                    if conflict is not None:
                        self.errors.append(
                            SemanticError(
                                f"Variável de pattern '{vname}' conflita com variável ou parâmetro já em escopo na linha {conflict['line']} (JLS §6.3 / §6.4.1).",
                                p_line,
                            )
                        )
                    seen_pattern_vars[vname] = p_line
                    collected[vname] = {
                        "type": resolved_var_type,
                        "line": p_line,
                        "is_final": is_final,
                        "reassigned": False,
                        "has_initializer": True,
                        "category": "variavel",
                    }
            return collected

        if isinstance(pattern, RecordPattern):
            p_line = getattr(pattern, "line", 1)
            tref = getattr(pattern, "type_ref", None)
            if tref is not None and getattr(tref, "annotations", None):
                self.errors.append(
                    SemanticError(
                        "Anotações não são permitidas diretamente sobre o ReferenceType de um RecordPattern (JLS §14.30.1).",
                        p_line,
                    )
                )
            _err_before_record_tref = len(self.errors)
            if tref is not None:
                for ta in getattr(tref, "type_arguments", []):
                    self._check_type_ref_annotations(ta)
                self._check_type_ref_arity(tref)
                self._check_type_ref_bounds(tref)

            r_type = self._normalize_type_str(tref) or getattr(pattern, "type_name", None) or ""
            target_source_type = expected_comp_type if is_component else selector_type
            if target_source_type:
                src_base, src_dims = self._split_type_dims(self._strip_generics(target_source_type) or "")
                if src_dims == 0 and src_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                    self.errors.append(
                        SemanticError(
                            f"Expressão/seletor de tipo primitivo '{target_source_type}' não pode casar com record pattern '{r_type}' (JLS §14.30.1).",
                            p_line,
                        )
                    )
                else:
                    self._check_pattern_type_compatibility(target_source_type, r_type, p_line, is_component=is_component)

            tdecl = self._lookup_type_decl(r_type)
            comps = getattr(pattern, "components", []) or []
            if tdecl is not None:
                tkind, rnode = tdecl
                if tkind != "record" or not isinstance(rnode, RecordDeclaration):
                    self.errors.append(
                        SemanticError(
                            f"Tipo '{r_type}' é '{tkind}' e não um 'record'; record pattern inválido (JLS §14.30.1).",
                            p_line,
                        )
                    )
                    for cp in comps:
                        collected.update(
                            self._analyze_pattern(cp, is_component=True, expected_comp_type=None, seen_pattern_vars=seen_pattern_vars)
                        )
                    return collected

                expected_comps = getattr(rnode, "components", []) or []
                if len(comps) != len(expected_comps):
                    self.errors.append(
                        SemanticError(
                            f"Record pattern '{r_type}' espera {len(expected_comps)} componente(s), mas recebeu {len(comps)} (JLS §14.30.1).",
                            p_line,
                        )
                    )
                g_tparams = getattr(rnode, "type_parameters", []) or []
                _, g_args, _ = self._extract_generic_args(r_type)
                if len(self.errors) == _err_before_record_tref and g_args and g_tparams and len(g_args) != len(g_tparams):
                    self.errors.append(
                        SemanticError(
                            f"Número de argumentos genéricos incompatível em record pattern '{r_type}' (esperado {len(g_tparams)}, encontrado {len(g_args)}).",
                            p_line,
                        )
                    )
                comp_types = self._get_record_component_types(tref or r_type) or []
                for idx, cp in enumerate(comps):
                    exp_ct = comp_types[idx] if idx < len(comp_types) else None
                    collected.update(
                        self._analyze_pattern(
                            cp,
                            is_component=True,
                            expected_comp_type=exp_ct,
                            seen_pattern_vars=seen_pattern_vars,
                        )
                    )
            else:
                self._record_unresolved(
                    f"Record externo '{r_type}' não declarado na unidade atual: natureza de record, aridade e tipos dos componentes não puderam ser validados completamente."
                )
                for cp in comps:
                    collected.update(
                        self._analyze_pattern(cp, is_component=True, expected_comp_type=None, seen_pattern_vars=seen_pattern_vars)
                    )
            return collected

        return collected

    def _push_pattern_scope(self, pvars: Dict[str, Dict[str, Any]]):
        """Empilha um escopo temporário de variáveis de pattern."""
        self._active_pattern_scopes.append(dict(pvars))

    def _pop_pattern_scope(self):
        """Desempilha o escopo temporário de variáveis de pattern."""
        if self._active_pattern_scopes:
            self._active_pattern_scopes.pop()

    def _inject_pattern_vars_into_enclosing_block(self, pvars: Dict[str, Dict[str, Any]]):
        """Injeta variáveis de pattern válidas no escopo do bloco imediatamente envolvente (JLS §6.3.2)."""
        if not pvars:
            return
        if not self._active_pattern_scopes:
            self._active_pattern_scopes.append({})
        target = self._active_pattern_scopes[-1]
        for vname, vinfo in pvars.items():
            if vname == "_":
                continue
            existing_pat = None
            for pscope in reversed(self._active_pattern_scopes):
                if vname in pscope:
                    existing_pat = pscope[vname]
                    break
            existing_loc = None
            for lscope in reversed(self._local_var_scopes):
                if vname in lscope:
                    existing_loc = lscope[vname]
                    break
            if existing_pat is not None:
                self.errors.append(
                    SemanticError(
                        f"Variável de pattern '{vname}' já está em escopo neste bloco (linha {existing_pat['line']} — JLS §6.3).",
                        vinfo.get("line", 1),
                    )
                )
            elif existing_loc is not None:
                self.errors.append(
                    SemanticError(
                        f"Variável de pattern '{vname}' conflita com variável local na linha {existing_loc['line']} (JLS §6.3).",
                        vinfo.get("line", 1),
                    )
                )
            else:
                target[vname] = dict(vinfo)

    def _pattern_has_named_vars(self, pattern: Optional[ASTNode]) -> bool:
        """Retorna True se o pattern ou seus componentes declararem alguma variável nomeada (não '_')."""
        if isinstance(pattern, TypePattern):
            is_unnamed = getattr(pattern, "is_unnamed", False) or getattr(pattern, "name", "") == "_"
            return (not is_unnamed) and bool(getattr(pattern, "name", None))
        if isinstance(pattern, RecordPattern):
            return any(self._pattern_has_named_vars(c) for c in getattr(pattern, "components", []))
        return False

    def _eval_constant_boolean(self, expr: Optional[ASTNode]) -> Optional[bool]:
        """Avalia expressões booleanas constantes segundo JLS §15.29 (usado em guards, fluxos e constantes)."""
        res = self._eval_constant_expr(expr)
        if res is not None and res[0] == "boolean":
            return bool(res[1])
        return None

    def _eval_constant_scalar(self, expr: Optional[ASTNode]) -> Any:
        """Avalia expressão escalar constante em tempo de compilação (JLS §15.29)."""
        res = self._eval_constant_expr(expr)
        return res[1] if res is not None else None

    def _stmt_completes_normally(self, stmt: Optional[ASTNode]) -> bool:
        """Estimativa conservadora de conclusão normal de instruções segundo JLS §14.22 (para escopo JLS §6.3)."""
        if stmt is None or isinstance(stmt, EmptyStatement):
            return True
        if isinstance(stmt, (ReturnStatement, ThrowStatement, YieldStatement, BreakStatement, ContinueStatement)):
            return False
        if isinstance(stmt, Block):
            for s in stmt.statements:
                if not self._stmt_completes_normally(s):
                    return False
            return True
        if isinstance(stmt, LabeledStatement):
            inner_norm = self._stmt_completes_normally(stmt.statement)
            return inner_norm or self._contains_break_targeting(stmt.statement, target_label=stmt.label)
        if isinstance(stmt, IfStatement):
            c_val = self._eval_constant_boolean(stmt.condition)
            if stmt.else_branch is None:
                if c_val is True:
                    return self._stmt_completes_normally(stmt.then_branch)
                return True
            if c_val is True:
                return self._stmt_completes_normally(stmt.then_branch)
            if c_val is False:
                return self._stmt_completes_normally(stmt.else_branch)
            return self._stmt_completes_normally(stmt.then_branch) or self._stmt_completes_normally(stmt.else_branch)
        if isinstance(stmt, WhileStatement):
            c_val = self._eval_constant_boolean(stmt.condition)
            if c_val is True:
                return self._contains_break_targeting(stmt.body, target_label=None)
            return True
        if isinstance(stmt, DoWhileStatement):
            c_val = self._eval_constant_boolean(stmt.condition)
            if c_val is True:
                return self._contains_break_targeting(stmt.body, target_label=None)
            return self._stmt_completes_normally(stmt.body) or self._contains_continue_to_current_loop(stmt.body) or self._contains_break_targeting(stmt.body, target_label=None)
        if isinstance(stmt, ForStatement):
            if stmt.condition is None or self._eval_constant_boolean(stmt.condition) is True:
                return self._contains_break_targeting(stmt.body, target_label=None)
            return True
        if isinstance(stmt, TryStatement):
            if stmt.finally_block is not None and not self._stmt_completes_normally(stmt.finally_block):
                return False
            if self._stmt_completes_normally(stmt.body):
                return True
            return any(self._stmt_completes_normally(c.body) for c in getattr(stmt, "catches", []))
        if isinstance(stmt, SynchronizedStatement):
            return self._stmt_completes_normally(stmt.body)
        return True

    def _reachability_const_bool(self, expr: Optional[ASTNode]) -> Optional[bool]:
        """Retorna o valor booleano constante em tempo de compilação de uma condição para análise JLS §14.22."""
        if expr is None:
            return None
        if id(expr) in self._reachability_const_bools:
            return self._reachability_const_bools[id(expr)]
        return self._eval_constant_boolean(expr)

    def _check_reachability_in_expr(self, expr: Optional[ASTNode], visited: Optional[Set[int]] = None) -> None:
        """Verifica código inalcançável dentro de lambdas de bloco e switch expressions em expressões alcançáveis."""
        if expr is None or not isinstance(expr, ASTNode):
            return
        if isinstance(
            expr,
            (
                TypeReference,
                ClassDeclaration,
                InterfaceDeclaration,
                EnumDeclaration,
                RecordDeclaration,
                AnnotationInterfaceDeclaration,
                MethodDeclaration,
                ConstructorDeclaration,
                InstanceInitializer,
                StaticInitializer,
                FieldDeclaration,
            ),
        ):
            return
        if visited is None:
            visited = set()
        nid = id(expr)
        if nid in visited:
            return
        visited.add(nid)
        if isinstance(expr, LambdaExpression):
            if getattr(expr, "is_block_body", False) and isinstance(getattr(expr, "body", None), Block):
                self._check_stmt_reachability(expr.body, True)
            else:
                self._check_reachability_in_expr(getattr(expr, "body", None), visited)
            return
        if isinstance(expr, SwitchExpression):
            self._check_switch_reachability(expr, is_expression=True, reachable=True, visited=visited)
            return
        if hasattr(expr, "__dict__"):
            for key, val in expr.__dict__.items():
                if key == "anonymous_body":
                    continue
                if isinstance(val, ASTNode):
                    self._check_reachability_in_expr(val, visited)
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        if isinstance(item, ASTNode):
                            self._check_reachability_in_expr(item, visited)

    def _check_switch_reachability(
        self,
        switch_node: ASTNode,
        is_expression: bool,
        reachable: bool,
        visited: Optional[Set[int]] = None,
    ) -> Tuple[bool, Set[Optional[str]], Set[Optional[str]]]:
        """Analisa alcançabilidade interna e conclusão normal de switch statement/expression (JLS §14.22)."""
        self._check_reachability_in_expr(getattr(switch_node, "selector", getattr(switch_node, "expression", None)), visited)
        sb = getattr(switch_node, "switch_block", None)
        if sb is None:
            any_norm = False
            has_default = getattr(switch_node, "default_block", None) is not None
            brks: Set[Optional[str]] = set()
            conts: Set[Optional[str]] = set()
            for case_clause in list(getattr(switch_node, "cases", []) or []):
                stmts = list(getattr(case_clause, "statements", []) or [])
                cn, cb, cc = self._check_stmt_list_reachability(stmts, reachable)
                any_norm = any_norm or cn
                brks |= cb
                conts |= cc
            def_blk = getattr(switch_node, "default_block", None)
            if def_blk is not None:
                dn, db, dc = self._check_stmt_reachability(def_blk, reachable)
                last_norm = dn
                brks |= db
                conts |= dc
            else:
                last_norm = True if not getattr(switch_node, "cases", None) else any_norm
            completes = reachable and ((not has_default) or last_norm or (None in brks))
            return completes, (brks - {None}), conts

        brks = set()
        conts = set()
        has_default = False
        has_pattern_or_null = False
        sel_expr = getattr(switch_node, "expression", None)
        sel_type: Optional[str] = self._inferred_types.get(id(sel_expr)) if sel_expr is not None else None
        if sel_type is None and sel_expr is not None:
            saved_supp = self._flow_suppress_errors
            self._flow_suppress_errors = True
            try:
                sel_type = self.infer_type(sel_expr)
            finally:
                self._flow_suppress_errors = saved_supp

        def _is_legacy_switch_selector(t: Optional[str]) -> bool:
            if not t or t in ("var", "desconhecido", "null"):
                return True
            clean = self._strip_leading_type_annotations(t) or t
            stripped = self._strip_generics(clean) or ""
            base, dims = self._split_type_dims(stripped)
            if dims > 0:
                return False
            if base in (
                "char", "byte", "short", "int",
                "Character", "Byte", "Short", "Integer", "String",
                "java.lang.Character", "java.lang.Byte", "java.lang.Short", "java.lang.Integer", "java.lang.String",
            ):
                return True
            if self._lookup_type_param_bounds(base) is not None:
                return False
            tdecl = self._lookup_type_decl(base)
            if tdecl is not None:
                return tdecl[0] == "enum"
            meta = self._inheritance_analyzer.get_type_meta(base)
            if meta is not None:
                return meta.get("kind") == "enum"
            ext = self._resolve_external_type(base)
            if ext is not None:
                return ext.kind == "enum" or ext.super_class == "java.lang.Enum"
            if not self._is_known_type(base):
                return True
            return False

        def _scan_switch_label(lb: ASTNode) -> None:
            nonlocal has_default, has_pattern_or_null
            if isinstance(lb, DefaultLabel) or getattr(lb, "has_default", False):
                has_default = True
            if getattr(lb, "patterns", None) or getattr(lb, "is_null", False):
                has_pattern_or_null = True

        if sb.is_rule_based:
            any_rule_completes = False
            for rule in list(getattr(sb, "switch_rules", []) or []):
                for lb in list(getattr(rule, "labels", []) or []):
                    _scan_switch_label(lb)
                    guard = getattr(lb, "guard", None)
                    if guard is not None:
                        self._check_reachability_in_expr(getattr(guard, "expression", None), visited)
                if getattr(rule, "is_throw", False):
                    self._check_reachability_in_expr(getattr(rule, "body", None), visited)
                elif getattr(rule, "is_block", False) and isinstance(getattr(rule, "body", None), Block):
                    rn, rb, rc = self._check_stmt_reachability(rule.body, reachable)
                    any_rule_completes = any_rule_completes or rn
                    brks |= rb
                    conts |= rc
                elif getattr(rule, "body", None) is not None:
                    self._check_reachability_in_expr(rule.body, visited)
                    any_rule_completes = True
            is_enhanced = (not _is_legacy_switch_selector(sel_type)) or has_pattern_or_null
            no_default_fallback = (not is_enhanced) and (not has_default)
            completes = reachable and (
                (not sb.switch_rules)
                or no_default_fallback
                or any_rule_completes
                or (None in brks)
            )
            return completes, (brks - {None}), conts

        groups = list(getattr(sb, "statement_groups", []) or [])
        last_group_completes = True
        has_trailing_empty_labels = bool(getattr(sb, "trailing_labels", []))
        for lb in list(getattr(sb, "trailing_labels", []) or []):
            _scan_switch_label(lb)
        for grp in groups:
            for lb in list(getattr(grp, "labels", []) or []):
                _scan_switch_label(lb)
                guard = getattr(lb, "guard", None)
                if guard is not None:
                    self._check_reachability_in_expr(getattr(guard, "expression", None), visited)
            stmts = list(getattr(grp, "statements", []) or [])
            gn, gb, gc = self._check_stmt_list_reachability(stmts, reachable)
            last_group_completes = gn
            brks |= gb
            conts |= gc
        if not groups or has_trailing_empty_labels:
            last_group_completes = True
        is_enhanced = (not _is_legacy_switch_selector(sel_type)) or has_pattern_or_null
        no_default_fallback = (not is_enhanced) and (not has_default)
        completes = reachable and (
            (not groups)
            or has_trailing_empty_labels
            or no_default_fallback
            or last_group_completes
            or (None in brks)
        )
        return completes, (brks - {None}), conts

    def _check_stmt_list_reachability(
        self, stmts: List[ASTNode], reachable: bool
    ) -> Tuple[bool, Set[Optional[str]], Set[Optional[str]]]:
        """Verifica sequência de instruções emitindo erro na primeira instrução inalcançável (JLS §14.22)."""
        if not stmts:
            return reachable, set(), set()
        curr = reachable
        all_brks: Set[Optional[str]] = set()
        all_conts: Set[Optional[str]] = set()
        reported = False
        for s in stmts:
            if not curr:
                if not reported:
                    self.errors.append(
                        SemanticError("Instrução inalcançável (JLS §14.22).", getattr(s, "line", 1))
                    )
                    reported = True
                continue
            curr, sb, sc = self._check_stmt_reachability(s, True)
            all_brks |= sb
            all_conts |= sc
        return curr, all_brks, all_conts

    def _check_constructor_body_reachability(self, body: ConstructorBody) -> None:
        """Verifica alcançabilidade em corpo flexível de construtor (prólogo, invocação explícita e epílogo — JLS §14.22)."""
        prologue = list(getattr(body, "prologue", []) or [])
        curr, _, _ = self._check_stmt_list_reachability(prologue, True)
        inv = getattr(body, "constructor_invocation", None)
        epilogue = list(getattr(body, "epilogue", []) or [])
        if not curr:
            target_node = inv if inv is not None else (epilogue[0] if epilogue else None)
            if target_node is not None:
                self.errors.append(
                    SemanticError("Instrução inalcançável (JLS §14.22).", getattr(target_node, "line", 1))
                )
            return
        if inv is not None:
            for arg in list(getattr(inv, "arguments", []) or []):
                self._check_reachability_in_expr(arg)
        self._check_stmt_list_reachability(epilogue, True)

    def _check_stmt_reachability(
        self,
        stmt: Optional[ASTNode],
        reachable: bool,
        direct_labels: Optional[Set[str]] = None,
    ) -> Tuple[bool, Set[Optional[str]], Set[Optional[str]]]:
        """Implementa as regras de alcançabilidade e conclusão normal de instruções da JLS §14.22."""
        if stmt is None or not reachable:
            return reachable, set(), set()

        if isinstance(stmt, Block):
            return self._check_stmt_list_reachability(list(getattr(stmt, "statements", []) or []), reachable)

        if isinstance(stmt, LabeledStatement):
            lbl = getattr(stmt, "label", None)
            inner = getattr(stmt, "statement", None)
            pass_labels: Optional[Set[str]] = None
            if isinstance(inner, (LabeledStatement, WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement)):
                pass_labels = set(direct_labels or ())
                if lbl:
                    pass_labels.add(lbl)
            in_norm, in_brks, in_conts = self._check_stmt_reachability(inner, reachable, direct_labels=pass_labels)
            had_break = (lbl is not None) and (lbl in in_brks)
            rem_brks = in_brks - ({lbl} if lbl else set())
            rem_conts = in_conts - ({lbl} if lbl else set())
            return (in_norm or had_break), rem_brks, rem_conts

        if isinstance(stmt, IfStatement):
            self._check_reachability_in_expr(stmt.condition)
            t_norm, t_brks, t_conts = self._check_stmt_reachability(stmt.then_branch, reachable)
            if stmt.else_branch is None:
                return reachable, t_brks, t_conts
            e_norm, e_brks, e_conts = self._check_stmt_reachability(stmt.else_branch, reachable)
            return (t_norm or e_norm), (t_brks | e_brks), (t_conts | e_conts)

        if isinstance(stmt, WhileStatement):
            self._check_reachability_in_expr(stmt.condition)
            c_val = self._reachability_const_bool(stmt.condition)
            if c_val is False:
                if stmt.body is not None:
                    self.errors.append(
                        SemanticError(
                            "Instrução inalcançável (JLS §14.22).",
                            getattr(stmt.body, "line", getattr(stmt, "line", 1)),
                        )
                    )
                return True, set(), set()
            _, b_brks, b_conts = self._check_stmt_reachability(stmt.body, reachable)
            has_unlabeled_brk = None in b_brks
            consume = {None} | set(direct_labels or ())
            return ((c_val is not True) or has_unlabeled_brk), (b_brks - {None}), (b_conts - consume)

        if isinstance(stmt, DoWhileStatement):
            b_norm, b_brks, b_conts = self._check_stmt_reachability(stmt.body, reachable)
            self._check_reachability_in_expr(stmt.condition)
            c_val = self._reachability_const_bool(stmt.condition)
            consume = {None} | set(direct_labels or ())
            can_cont_this = bool(b_conts & consume)
            has_unlabeled_brk = None in b_brks
            completes = ((c_val is not True) and (b_norm or can_cont_this)) or has_unlabeled_brk
            return completes, (b_brks - {None}), (b_conts - consume)

        if isinstance(stmt, ForStatement):
            self._check_reachability_in_expr(stmt.init)
            self._check_reachability_in_expr(stmt.condition)
            self._check_reachability_in_expr(stmt.update)
            c_val = self._reachability_const_bool(stmt.condition) if stmt.condition is not None else True
            if c_val is False:
                if stmt.body is not None:
                    self.errors.append(
                        SemanticError(
                            "Instrução inalcançável (JLS §14.22).",
                            getattr(stmt.body, "line", getattr(stmt, "line", 1)),
                        )
                    )
                return True, set(), set()
            _, b_brks, b_conts = self._check_stmt_reachability(stmt.body, reachable)
            has_unlabeled_brk = None in b_brks
            consume = {None} | set(direct_labels or ())
            return ((c_val is not True) or has_unlabeled_brk), (b_brks - {None}), (b_conts - consume)

        if isinstance(stmt, EnhancedForStatement):
            self._check_reachability_in_expr(stmt.iterable)
            _, b_brks, b_conts = self._check_stmt_reachability(stmt.body, reachable)
            consume = {None} | set(direct_labels or ())
            return True, (b_brks - {None}), (b_conts - consume)

        if isinstance(stmt, SwitchStatement):
            return self._check_switch_reachability(stmt, is_expression=False, reachable=reachable)

        if isinstance(stmt, TryStatement):
            res_spec = getattr(stmt, "resource_specification", None)
            res_nodes = res_spec.resources if res_spec is not None else getattr(stmt, "resources", [])
            for r in list(res_nodes or []):
                self._check_reachability_in_expr(r)
            body_norm, brks, conts = self._check_stmt_reachability(stmt.body, reachable)
            any_catch_norm = False
            for c in list(getattr(stmt, "catches", []) or []):
                cn, cb, cc = self._check_stmt_reachability(c.body, reachable)
                any_catch_norm = any_catch_norm or cn
                brks |= cb
                conts |= cc
            fin = getattr(stmt, "finally_block", None)
            if fin is not None:
                fin_norm, fb, fc = self._check_stmt_reachability(fin, reachable)
                if not fin_norm:
                    return False, fb, fc
                return (body_norm or any_catch_norm), (brks | fb), (conts | fc)
            return (body_norm or any_catch_norm), brks, conts

        if isinstance(stmt, SynchronizedStatement):
            self._check_reachability_in_expr(stmt.lock)
            return self._check_stmt_reachability(stmt.body, reachable)

        if isinstance(stmt, BreakStatement):
            return False, {getattr(stmt, "label", None)}, set()

        if isinstance(stmt, ContinueStatement):
            return False, set(), {getattr(stmt, "label", None)}

        if isinstance(stmt, (ReturnStatement, ThrowStatement, YieldStatement)):
            self._check_reachability_in_expr(getattr(stmt, "expression", None))
            return False, set(), set()

        self._check_reachability_in_expr(stmt)
        return True, set(), set()

    def _stmt_completes_normally_jls1422(self, stmt: Optional[ASTNode], direct_labels: Optional[Set[str]] = None) -> bool:
        """Consulta pura de conclusão normal segundo JLS §14.22 sem emitir erros duplicados."""
        if stmt is None:
            return True
        if isinstance(stmt, (ReturnStatement, ThrowStatement, YieldStatement, BreakStatement, ContinueStatement)):
            return False
        if isinstance(stmt, Block):
            for s in list(getattr(stmt, "statements", []) or []):
                if not self._stmt_completes_normally_jls1422(s):
                    return False
            return True
        if isinstance(stmt, LabeledStatement):
            lbl = getattr(stmt, "label", None)
            inner = getattr(stmt, "statement", None)
            in_norm = self._stmt_completes_normally_jls1422(inner)
            return in_norm or (lbl is not None and self._contains_reachable_break(inner, target_label=lbl))
        if isinstance(stmt, IfStatement):
            if stmt.else_branch is None:
                return True
            return self._stmt_completes_normally_jls1422(stmt.then_branch) or self._stmt_completes_normally_jls1422(stmt.else_branch)
        if isinstance(stmt, WhileStatement):
            c_val = self._reachability_const_bool(stmt.condition)
            if c_val is False:
                return True
            return (c_val is not True) or self._contains_reachable_break(stmt.body, target_label=None)
        if isinstance(stmt, DoWhileStatement):
            c_val = self._reachability_const_bool(stmt.condition)
            return (
                (c_val is not True and (self._stmt_completes_normally_jls1422(stmt.body) or self._contains_continue_to_current_loop(stmt.body)))
                or self._contains_reachable_break(stmt.body, target_label=None)
            )
        if isinstance(stmt, ForStatement):
            c_val = self._reachability_const_bool(stmt.condition) if stmt.condition is not None else True
            if c_val is False:
                return True
            return (c_val is not True) or self._contains_reachable_break(stmt.body, target_label=None)
        if isinstance(stmt, TryStatement):
            fin = getattr(stmt, "finally_block", None)
            if fin is not None and not self._stmt_completes_normally_jls1422(fin):
                return False
            if self._stmt_completes_normally_jls1422(stmt.body):
                return True
            return any(self._stmt_completes_normally_jls1422(c.body) for c in list(getattr(stmt, "catches", []) or []))
        if isinstance(stmt, SynchronizedStatement):
            return self._stmt_completes_normally_jls1422(stmt.body)
        if isinstance(stmt, SwitchStatement):
            sb = getattr(stmt, "switch_block", None)
            if sb is None:
                has_def = getattr(stmt, "default_block", None) is not None
                if not has_def:
                    return True
                return self._stmt_completes_normally_jls1422(stmt.default_block) or self._contains_reachable_break(stmt, target_label=None)
            has_def = False
            if sb.is_rule_based:
                any_norm = False
                for r in list(getattr(sb, "switch_rules", []) or []):
                    if any(isinstance(lb, DefaultLabel) or getattr(lb, "has_default", False) for lb in list(getattr(r, "labels", []) or [])):
                        has_def = True
                    if getattr(r, "is_throw", False):
                        continue
                    if getattr(r, "is_block", False) and isinstance(getattr(r, "body", None), Block):
                        if self._stmt_completes_normally_jls1422(r.body):
                            any_norm = True
                    elif getattr(r, "body", None) is not None:
                        any_norm = True
                return (not has_def) or any_norm or not sb.switch_rules or self._contains_reachable_break(stmt, target_label=None)
            groups = list(getattr(sb, "statement_groups", []) or [])
            for lb in list(getattr(sb, "trailing_labels", []) or []):
                if isinstance(lb, DefaultLabel) or getattr(lb, "has_default", False):
                    has_def = True
            for g in groups:
                for lb in list(getattr(g, "labels", []) or []):
                    if isinstance(lb, DefaultLabel) or getattr(lb, "has_default", False):
                        has_def = True
            if not has_def or not groups or getattr(sb, "trailing_labels", []):
                return True
            last_norm = all(self._stmt_completes_normally_jls1422(s) for s in list(getattr(groups[-1], "statements", []) or []))
            return last_norm or self._contains_reachable_break(stmt, target_label=None)
        return True

    def _contains_reachable_break(
        self,
        node: Optional[ASTNode],
        target_label: Optional[str] = None,
        in_nested: bool = False,
    ) -> bool:
        """Verifica se há break alcançável direcionado ao bloco/laço alvo (JLS §14.22)."""
        if node is None:
            return False
        if isinstance(node, BreakStatement):
            if node.label is None:
                return (target_label is None) and (not in_nested)
            return target_label is not None and node.label == target_label
        if isinstance(node, (LambdaExpression, ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            return False
        if isinstance(node, Block):
            for s in list(getattr(node, "statements", []) or []):
                if self._contains_reachable_break(s, target_label, in_nested):
                    return True
                if not self._stmt_completes_normally_jls1422(s):
                    return False
            return False
        if isinstance(node, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement, SwitchStatement, SwitchExpression)):
            in_nested = True
        if isinstance(node, WhileStatement) and self._reachability_const_bool(node.condition) is False:
            return False
        if isinstance(node, ForStatement) and node.condition is not None and self._reachability_const_bool(node.condition) is False:
            return False
        if hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, ASTNode):
                    if self._contains_reachable_break(val, target_label, in_nested):
                        return True
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        if isinstance(item, ASTNode) and self._contains_reachable_break(item, target_label, in_nested):
                            return True
        return False

    def _contains_break_targeting(
        self,
        node: Optional[ASTNode],
        target_label: Optional[str] = None,
        extra_labels: Optional[Set[str]] = None,
        in_nested_loop_or_switch: bool = False,
    ) -> bool:
        """Verifica se há BreakStatement direcionado ao laço/label alvo."""
        if node is None:
            return False
        if isinstance(node, BreakStatement):
            if node.label is None:
                return (target_label is None) and (not in_nested_loop_or_switch)
            if target_label is not None and node.label == target_label:
                return True
            if extra_labels and node.label in extra_labels:
                return True
            return False
        if isinstance(node, (LambdaExpression, ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            return False
        if isinstance(node, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement, SwitchStatement, SwitchExpression)):
            in_nested_loop_or_switch = True
        if hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, ASTNode):
                    if self._contains_break_targeting(val, target_label, extra_labels, in_nested_loop_or_switch):
                        return True
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        if isinstance(item, ASTNode) and self._contains_break_targeting(item, target_label, extra_labels, in_nested_loop_or_switch):
                            return True
        return False

    def _contains_continue_to_current_loop(self, node: Optional[ASTNode], in_nested_loop: bool = False) -> bool:
        """Verifica se há ContinueStatement não rotulado direcionado ao laço atual."""
        if node is None:
            return False
        if isinstance(node, ContinueStatement):
            return (node.label is None) and (not in_nested_loop)
        if isinstance(node, (LambdaExpression, ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            return False
        if isinstance(node, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement)):
            in_nested_loop = True
        if hasattr(node, "__dict__"):
            for val in node.__dict__.values():
                if isinstance(val, ASTNode) and self._contains_continue_to_current_loop(val, in_nested_loop):
                    return True
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        if isinstance(item, ASTNode) and self._contains_continue_to_current_loop(item, in_nested_loop):
                            return True
        return False

    def _is_pattern_unconditional(self, pattern: Optional[ASTNode], target_type: Optional[str]) -> Optional[bool]:
        """Indica se um pattern casa incondicionalmente com qualquer valor não nulo de target_type (JLS §14.30.3)."""
        if pattern is None:
            return False
        if isinstance(pattern, MatchAllPattern):
            return True
        if isinstance(pattern, TypePattern):
            if getattr(pattern, "is_var", False) or (getattr(pattern, "type_ref", None) and getattr(pattern.type_ref, "name", "") == "var"):
                return True
            p_type = self._normalize_type_str(getattr(pattern, "type_ref", None)) or getattr(pattern, "type_name", None)
            if not target_type:
                return p_type == "Object"
            return self._is_subtype(target_type, p_type)
        if isinstance(pattern, RecordPattern):
            r_type = self._normalize_type_str(getattr(pattern, "type_ref", None)) or getattr(pattern, "type_name", None)
            if not target_type:
                return False
            sub = self._is_subtype(target_type, r_type)
            if sub is not True:
                return sub
            comp_types = self._get_record_component_types(getattr(pattern, "type_ref", None) or r_type)
            if comp_types is None or len(comp_types) != len(getattr(pattern, "components", [])):
                return None
            all_true = True
            for cp, ct in zip(pattern.components, comp_types):
                c_uncond = self._is_pattern_unconditional(cp, ct)
                if c_uncond is False:
                    return False
                if c_uncond is None:
                    all_true = False
            return True if all_true else None
        return False

    def _pattern_dominates(
        self,
        p1: Optional[ASTNode],
        p2: Optional[ASTNode],
        target_type: Optional[str] = None,
    ) -> Tuple[Optional[bool], bool]:
        """Verifica se p1 domina p2 segundo JLS §14.30.3. Retorna (domina_ou_None, houve_externo)."""
        if p1 is None or p2 is None:
            return False, False
        if isinstance(p1, MatchAllPattern):
            return True, False
        if isinstance(p1, TypePattern):
            if getattr(p1, "is_var", False) or (getattr(p1, "type_ref", None) and getattr(p1.type_ref, "name", "") == "var"):
                return True, False
            t1 = self._normalize_type_str(getattr(p1, "type_ref", None)) or getattr(p1, "type_name", None)
            if isinstance(p2, MatchAllPattern):
                if not target_type:
                    return (True, False) if self._simple_base_name(t1) == "Object" else (None, True)
                sub = self._is_subtype(target_type, t1)
                return sub, (sub is None)
            if isinstance(p2, TypePattern):
                is_var2 = getattr(p2, "is_var", False) or (getattr(p2, "type_ref", None) and getattr(p2.type_ref, "name", "") == "var")
                t2 = (target_type or "Object") if is_var2 else (self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None))
                if self.enable_preview_primitive_patterns and t1 == "Object" and t2 in self.PRIMITIVE_TYPES:
                    return True, False
                sub = self._is_subtype(t2, t1)
                return sub, (sub is None)
            if isinstance(p2, RecordPattern):
                t2 = self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None)
                sub = self._is_subtype(t2, t1)
                return sub, (sub is None)
            return False, False

        if isinstance(p1, RecordPattern):
            r1 = self._normalize_type_str(getattr(p1, "type_ref", None)) or getattr(p1, "type_name", None)
            c1 = getattr(p1, "components", []) or []
            if isinstance(p2, MatchAllPattern):
                if not target_type:
                    return False, False
                uncond = self._is_pattern_unconditional(p1, target_type)
                return uncond, (uncond is None)
            if isinstance(p2, TypePattern):
                is_var2 = getattr(p2, "is_var", False) or (getattr(p2, "type_ref", None) and getattr(p2.type_ref, "name", "") == "var")
                t2 = target_type if is_var2 else (self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None))
                if not t2:
                    return False, False
                uncond = self._is_pattern_unconditional(p1, t2)
                return uncond, (uncond is None)
            if isinstance(p2, RecordPattern):
                r2 = self._normalize_type_str(getattr(p2, "type_ref", None)) or getattr(p2, "type_name", None)
                c2 = getattr(p2, "components", []) or []
                sub = self._is_subtype(r2, r1)
                if sub is False:
                    return False, False
                if sub is None:
                    return None, True
                if len(c1) != len(c2):
                    return False, False
                comp_types = self._get_record_component_types(getattr(p2, "type_ref", None) or r2)
                saw_unres = False
                for idx, (sub_p1, sub_p2) in enumerate(zip(c1, c2)):
                    ct = comp_types[idx] if comp_types and idx < len(comp_types) else None
                    dom, unres = self._pattern_dominates(sub_p1, sub_p2, ct)
                    if unres:
                        saw_unres = True
                    if dom is False:
                        return False, saw_unres
                    if dom is None:
                        return None, True
                return True, False
        return False, False

    def _switch_constant_type(self, const_expr: ASTNode, selector_type: Optional[str] = None) -> Optional[str]:
        """Infere o tipo de uma constante de 'case' para verificação de dominância (JLS §14.11.1)."""
        if isinstance(const_expr, Literal):
            kind = getattr(const_expr, "kind", "")
            val_s = str(getattr(const_expr, "value", ""))
            if kind in ("STRING", "TEXT_BLOCK"):
                return "String"
            if kind == "LONG":
                return "Long" if selector_type not in self.PRIMITIVE_TYPES else "long"
            if kind in ("NUM", "INT"):
                if val_s.lower().endswith("l"):
                    return "Long" if selector_type not in self.PRIMITIVE_TYPES else "long"
                return "Integer" if selector_type not in self.PRIMITIVE_TYPES else "int"
            if kind == "FLOAT":
                return "Float" if selector_type not in self.PRIMITIVE_TYPES else "float"
            if kind == "DOUBLE":
                return "Double" if selector_type not in self.PRIMITIVE_TYPES else "double"
            if kind == "CHAR":
                return "Character" if selector_type not in self.PRIMITIVE_TYPES else "char"
            if kind == "BOOLEAN":
                return "Boolean" if selector_type not in self.PRIMITIVE_TYPES else "boolean"
            if kind == "NULL":
                return "null"
        if isinstance(const_expr, Identifier):
            if selector_type and self._simple_base_name(selector_type) in self._enums:
                ename = self._simple_base_name(selector_type)
                econsts = {c.name for c in getattr(self._enums[ename], "constants", [])}
                if const_expr.name in econsts:
                    return ename
            for ename, edecl in self._enums.items():
                if const_expr.name in {c.name for c in getattr(edecl, "constants", [])}:
                    return ename
            sym = self._lookup_var_symbol(const_expr.name)
            if sym and "type" in sym:
                t = sym["type"]
                return self._boxed_type(t) if (t in self.PRIMITIVE_TYPES and selector_type not in self.PRIMITIVE_TYPES) else t
        if isinstance(const_expr, MemberAccess) and isinstance(const_expr.target, Identifier):
            return const_expr.target.name
        if isinstance(const_expr, UnaryOp):
            return self._switch_constant_type(const_expr.operand, selector_type)
        return None

    @staticmethod
    def _boxed_type(prim: str) -> str:
        return {
            "byte": "Byte",
            "short": "Short",
            "int": "Integer",
            "long": "Long",
            "float": "Float",
            "double": "Double",
            "char": "Character",
            "boolean": "Boolean",
        }.get(prim, prim)

    def _pattern_dominates_constant(self, pattern: ASTNode, const_type: Optional[str]) -> Optional[bool]:
        """Indica se um pattern incondicional domina uma constante de tipo const_type."""
        if not const_type or const_type == "null":
            return False
        if isinstance(pattern, MatchAllPattern):
            return True
        if isinstance(pattern, TypePattern):
            p_type = self._normalize_type_str(getattr(pattern, "type_ref", None)) or getattr(pattern, "type_name", None)
            if not p_type:
                return False
            sub = self._is_subtype(const_type, p_type)
            if sub is None and const_type in self.PRIMITIVE_TYPES:
                return self._is_subtype(self._boxed_type(const_type), p_type)
            return sub
        return False

    def _max_pattern_depth(self, pat: Optional[ASTNode]) -> int:
        if not isinstance(pat, RecordPattern):
            return 0
        comps = getattr(pat, "components", []) or []
        if not comps:
            return 1
        return 1 + max(self._max_pattern_depth(c) for c in comps)

    def _is_vector_covered(
        self,
        types: List[str],
        matrix: List[List[ASTNode]],
        max_rec_depth: int,
        depth: int = 0,
    ) -> Tuple[bool, bool]:
        """
        Verifica cobertura/exaustividade de uma tupla de tipos `types` contra uma matriz de patterns
        (inclui tipos sealed, enums, booleans e records aninhados/recursivos — JLS §14.11.1.1).
        Retorna (coberto, encontrou_tipo_externo_nao_resolvido).
        """
        if not types:
            return (len(matrix) > 0), False
        if not matrix:
            return False, not self._is_known_type(types[0])

        t0 = types[0]
        rest_types = types[1:]
        t0_simple = self._simple_base_name(t0) or ""

        # Caso 1: Qualquer linha cujo pattern 0 seja incondicional para t0 e cubra rest_types garante cobertura se sufixos cobrirem
        # Primeiro separa as linhas wildcard/incondicionais para t0:
        uncond_suffixes: List[List[ASTNode]] = []
        for row in matrix:
            p0 = row[0]
            if self._is_pattern_unconditional(p0, t0) is True:
                uncond_suffixes.append(row[1:])
        if uncond_suffixes:
            cov_rest, unres_rest = self._is_vector_covered(rest_types, uncond_suffixes, max_rec_depth, depth)
            if cov_rest:
                return True, unres_rest

        # Caso 2: t0 é tipo sealed declarado na unidade -> precisa cobrir TODOS os subtipos permitidos
        tdecl = self._lookup_type_decl(t0_simple)
        if tdecl is not None and "sealed" in getattr(tdecl[1], "modifiers", []):
            permits = self._get_sealed_permitted_types(t0)
            if not permits:
                self._record_unresolved(
                    f"Tipo sealed '{t0}' não possui subtipos permitidos visíveis nesta unidade de compilação."
                )
                return False, True
            saw_unres = False
            for pt in permits:
                # Reutiliza matrix original: subtipo pt herda cobertura de patterns supertipo (p0 >= pt ou RecordPattern pt)
                sub_cov, sub_unres = self._is_vector_covered([pt] + rest_types, matrix, max_rec_depth, depth)
                if sub_unres:
                    saw_unres = True
                if not sub_cov:
                    return False, saw_unres
            return True, saw_unres

        # Caso 3: t0 é um record declarado -> desconstruir componentes [C1..Ck] apenas até max_rec_depth
        if tdecl is not None and tdecl[0] == "record" and isinstance(tdecl[1], RecordDeclaration) and depth < max_rec_depth + 1:
            comp_types = self._get_record_component_types(t0) or []
            k = len(comp_types)
            rec_matrix: List[List[ASTNode]] = []
            for row in matrix:
                p0 = row[0]
                if isinstance(p0, RecordPattern):
                    pr_name = self._normalize_type_str(getattr(p0, "type_ref", None)) or getattr(p0, "type_name", None)
                    if self._is_subtype(t0, pr_name) is True and len(getattr(p0, "components", [])) == k:
                        rec_matrix.append(list(p0.components) + row[1:])
                elif self._is_pattern_unconditional(p0, t0) is True:
                    rec_matrix.append([MatchAllPattern() for _ in range(k)] + row[1:])
            if rec_matrix:
                return self._is_vector_covered(comp_types + rest_types, rec_matrix, max_rec_depth, depth + 1)
            return False, False

        # Caso 4: Enum ou boolean em coluna interna de record não tem constante em pattern (só TypePattern/var/_),
        # mas se houve padrão incondicional já teria retornado no Caso 1.
        is_known = self._is_known_type(t0)
        return False, (not is_known)

    def _analyze_switch_block(self, switch_node: ASTNode, is_expression: bool = False, expected_type: Optional[str] = None):
        """Valida SwitchStatement e SwitchExpression (patterns, guards, dominância, escopo, yield e exaustividade)."""
        pending_labels = set(self._flow_pending_labels) if not is_expression else set()
        if not is_expression:
            self._flow_pending_labels = set()
        self.check_expression(switch_node.expression)
        sel_snap = self._flow_snapshot()
        sb = getattr(switch_node, "switch_block", None)
        selector_type = self.infer_type(switch_node.expression)
        selector_base = self._strip_generics(selector_type) if selector_type else None
        if selector_base in ("boolean", "long", "float", "double") and not self.enable_preview_primitive_patterns:
            self.errors.append(
                SemanticError(
                    f"Seletor de tipo '{selector_type}' em 'switch' requer recurso preview (JEP 530) e está desabilitado no modo padrão Java SE 26 (JLS §14.11).",
                    getattr(switch_node, "line", 1),
                )
            )

        self.symbols.enter_scope()
        if self._local_var_scopes is not None:
            self._local_var_scopes.append({})
        self._local_type_scopes.append({})
        self._local_declared_type_scopes.append({})
        self._active_pattern_scopes.append({})
        if not is_expression:
            self._switch_depth += 1
        if is_expression:
            self._switch_yield_exprs_stack.append([])
        sw_frame = self._flow_push_exit_frame("switch_expr" if is_expression else "switch", labels=pending_labels)

        enum_const_names = self._collect_all_enum_constant_names()
        seen_default_pos: Optional[Tuple[int, bool]] = None  # (line, is_null_default)
        seen_null_line: Optional[int] = None
        seen_constants: Dict[Any, int] = {}
        seen_enum_case_names: Set[str] = set()
        seen_boolean_literals: Set[bool] = set()
        seen_patterns_for_dominance: List[Tuple[ASTNode, bool, int]] = []
        unconditional_top_patterns: List[ASTNode] = []
        has_pattern_labels = False

        def validate_label_and_collect_vars(lb: ASTNode) -> Dict[str, Dict[str, Any]]:
            nonlocal seen_default_pos, seen_null_line, has_pattern_labels
            lb_line = getattr(lb, "line", getattr(switch_node, "line", 1))
            label_pvars: Dict[str, Dict[str, Any]] = {}

            if isinstance(lb, DefaultLabel):
                if seen_default_pos is not None:
                    self.errors.append(SemanticError("Múltiplos labels 'default' no mesmo switch (JLS §14.11.1).", lb_line))
                seen_default_pos = (lb_line, False)
                for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                    if prev_uncond and self._is_pattern_unconditional(prev_p, selector_type) is True:
                        self.errors.append(
                            SemanticError(
                                f"Label 'default' é dominado pelo pattern incondicional anterior na linha {prev_line} (JLS §14.11.1).",
                                lb_line,
                            )
                        )
                        break
                return label_pvars

            if isinstance(lb, CaseLabel):
                patterns = list(getattr(lb, "patterns", []) or [])
                guard = getattr(lb, "guard", None)
                if patterns:
                    has_pattern_labels = True

                # Verificações de ordenação relativas a 'default' e 'case null, default' anteriores
                if seen_default_pos is not None and not (lb.has_default and len(patterns) == 0 and len(lb.constants) == 0):
                    def_line, def_is_null_default = seen_default_pos
                    if def_is_null_default:
                        self.errors.append(
                            SemanticError(
                                f"Label 'case' na linha {lb_line} não pode aparecer após 'case null, default' (linha {def_line} — JLS §14.11.1).",
                                lb_line,
                            )
                        )
                    elif patterns or lb.is_null:
                        self.errors.append(
                            SemanticError(
                                f"Label com pattern ou 'case null' não pode aparecer após 'default' (linha {def_line} — JLS §14.11.1).",
                                lb_line,
                            )
                        )

                if lb.is_null:
                    if selector_base in self.PRIMITIVE_TYPES:
                        self.errors.append(
                            SemanticError(
                                f"'case null' não é permitido para seletor de tipo primitivo '{selector_type}' (JLS §14.11.1).",
                                lb_line,
                            )
                        )
                    if seen_null_line is not None:
                        self.errors.append(SemanticError("Múltiplos labels 'case null' no mesmo switch (JLS §14.11.1).", lb_line))
                    seen_null_line = lb_line

                if lb.has_default:
                    if seen_default_pos is not None:
                        self.errors.append(SemanticError("Múltiplos labels 'default' no mesmo switch (JLS §14.11.1).", lb_line))
                    seen_default_pos = (lb_line, bool(lb.is_null))
                    for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                        if prev_uncond and self._is_pattern_unconditional(prev_p, selector_type) is True:
                            self.errors.append(
                                SemanticError(
                                    f"Label 'case null, default' não pode coexistir após pattern incondicional na linha {prev_line} (JLS §14.11.1).",
                                    lb_line,
                                )
                            )
                            break

                # Regra JLS §14.11.1: múltiplos patterns no mesmo label não podem declarar variáveis nomeadas
                if len(patterns) > 1:
                    for p in patterns:
                        if self._pattern_has_named_vars(p):
                            self.errors.append(
                                SemanticError(
                                    "Múltiplos patterns no mesmo label 'case' não podem declarar variáveis de pattern nomeadas (JLS §14.11.1).",
                                    getattr(p, "line", lb_line),
                                )
                            )
                            break

                # Constantes em 'case'
                for c in lb.constants:
                    if lb.is_null and isinstance(c, Literal) and getattr(c, "kind", "") == "NULL":
                        continue
                    self._check_switch_constant_expr(c, lb_line, enum_const_names)
                    c_line = getattr(c, "line", lb_line)
                    c_type = self._switch_constant_type(c, selector_type)
                    for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                        if not prev_uncond:
                            continue
                        if self._pattern_dominates_constant(prev_p, c_type) is True:
                            self.errors.append(
                                SemanticError(
                                    f"Constante de 'case' é dominada pelo pattern anterior na linha {prev_line} (JLS §14.11.1).",
                                    c_line,
                                )
                            )
                            break
                    key = self._switch_label_constant_key(c)
                    if key is not None:
                        if key in seen_constants:
                            self.errors.append(
                                SemanticError(
                                    f"Constante de 'case' duplicada no switch (já definida na linha {seen_constants[key]} — JLS §14.11.1).",
                                    c_line,
                                )
                            )
                        else:
                            seen_constants[key] = c_line
                    if isinstance(c, Identifier):
                        seen_enum_case_names.add(c.name)
                    elif isinstance(c, MemberAccess):
                        seen_enum_case_names.add(c.member_name)
                    elif isinstance(c, Literal) and getattr(c, "kind", "") == "BOOLEAN":
                        seen_boolean_literals.add(str(c.value).lower() == "true")

                # Patterns + dominância entre patterns + análise do guard 'when'
                if patterns:
                    is_uncond_guard = True
                    if guard is not None:
                        g_const = self._eval_constant_boolean(guard.expression)
                        is_uncond_guard = (g_const is True)

                    guard_true_vars: Dict[str, Dict[str, Any]] = {}
                    for p in patterns:
                        p_line = getattr(p, "line", lb_line)
                        p_vars = self._analyze_pattern(p, selector_type=selector_type, is_component=False)
                        for vn, vi in p_vars.items():
                            if vn in label_pvars:
                                self.errors.append(
                                    SemanticError(
                                        f"Variável de pattern '{vn}' declarada em duplicidade no mesmo label de switch (JLS §14.11.1).",
                                        vi.get("line", p_line),
                                    )
                                )
                            else:
                                label_pvars[vn] = vi

                        for prev_p, prev_uncond, prev_line in seen_patterns_for_dominance:
                            if not prev_uncond:
                                continue
                            dom, unres = self._pattern_dominates(prev_p, p, selector_type)
                            if dom is True:
                                self.errors.append(
                                    SemanticError(
                                        f"Label de case é dominado pelo pattern anterior na linha {prev_line} (JLS §14.11.1 / §14.30.3).",
                                        p_line,
                                    )
                                )
                                break
                            if unres:
                                self._record_unresolved(
                                    f"Verificação parcial de dominância entre patterns nas linhas {prev_line} e {p_line} envolve tipo externo não resolvido."
                                )

                        seen_patterns_for_dominance.append((p, is_uncond_guard, p_line))
                        if is_uncond_guard:
                            unconditional_top_patterns.append(p)

                    if guard is not None:
                        g_line = getattr(guard, "line", lb_line)
                        self._push_pattern_scope(label_pvars)
                        try:
                            g_flow = self._check_expression_flow(guard.expression)
                            g_type = self.infer_type(guard.expression)
                            if g_type is not None and g_type not in ("boolean", "Boolean", "Object", "desconhecido", "var"):
                                self.errors.append(
                                    SemanticError(
                                        f"Condição do guard 'when' deve possuir tipo 'boolean' (encontrado '{g_type}' — JLS §14.11.1).",
                                        g_line,
                                    )
                                )
                            guard_true_vars = dict(g_flow.true_vars)
                        finally:
                            self._pop_pattern_scope()
                        for gvn, gvi in guard_true_vars.items():
                            if gvn not in label_pvars:
                                label_pvars[gvn] = gvi

            return label_pvars

        branch_exits: List[Tuple[Set[Any], Set[Any], bool]] = []
        normal_exits: List[Tuple[Set[Any], Set[Any], bool]] = []
        is_exhaustive_switch = False
        try:
            if sb is not None:
                if sb.is_rule_based:
                    for rule in sb.switch_rules:
                        self._flow_restore(sel_snap)
                        rule_pvars: Dict[str, Dict[str, Any]] = {}
                        for lb in rule.labels:
                            lb_vars = validate_label_and_collect_vars(lb)
                            rule_pvars.update(lb_vars)
                        self.symbols.enter_scope()
                        self._local_var_scopes.append({})
                        self._local_type_scopes.append({})
                        self._local_declared_type_scopes.append({})
                        self._push_pattern_scope(rule_pvars)
                        try:
                            if rule.is_throw:
                                self.analyze_statement(rule.body)
                            elif rule.is_block and isinstance(rule.body, Block):
                                self.analyze_block(rule.body)
                                if self._flow_reachable:
                                    branch_exits.append(self._flow_snapshot())
                                if is_expression and self._stmt_completes_normally(rule.body):
                                    self.errors.append(
                                        SemanticError(
                                            "Bloco de regra em switch expression não pode concluir normalmente sem 'yield' ou 'throw' (JLS §15.28.1).",
                                            getattr(rule, "line", 1),
                                        )
                                    )
                            elif rule.body is not None:
                                rule_inner = rule.body.expression if isinstance(rule.body, ExpressionStatement) else rule.body
                                if not is_expression and not self._is_statement_expression(rule_inner):
                                    self.errors.append(
                                        SemanticError(
                                            "Em switch statement com '->', o corpo deve ser bloco, 'throw' ou statement expression (JLS §14.11.1).",
                                            getattr(rule, "line", 1),
                                        )
                                    )
                                if is_expression:
                                    self._check_expression_with_target(rule_inner, expected_type)
                                    if self._flow_reachable:
                                        sw_frame["yields"].append(self._flow_snapshot())
                                    if self._switch_yield_exprs_stack:
                                        self._switch_yield_exprs_stack[-1].append((rule_inner, getattr(rule, "line", 1)))
                                else:
                                    self._check_expression_flow(rule_inner)
                                    if self._flow_reachable:
                                        branch_exits.append(self._flow_snapshot())
                        finally:
                            self._pop_pattern_scope()
                            self._local_declared_type_scopes.pop()
                            self._local_type_scopes.pop()
                            self._flow_cleanup_scope(self._local_var_scopes[-1])
                            self._local_var_scopes.pop()
                            self.symbols.exit_scope()
                else:
                    prev_grp_completes_normally = False
                    fallthrough_snap: Optional[Tuple[Set[Any], Set[Any], bool]] = None
                    num_groups = len(sb.statement_groups)
                    for g_idx, grp in enumerate(sb.statement_groups):
                        if fallthrough_snap is not None and fallthrough_snap[2]:
                            grp_entry_snap = self._flow_join_states(sel_snap, fallthrough_snap)
                        else:
                            grp_entry_snap = sel_snap
                        self._flow_restore(grp_entry_snap)

                        grp_pvars: Dict[str, Dict[str, Any]] = {}
                        has_named_pat_in_grp = False
                        grp_labels = list(getattr(grp, "labels", []) or [])
                        for lb in grp_labels:
                            lb_vars = validate_label_and_collect_vars(lb)
                            if any(
                                self._pattern_has_named_vars(p)
                                for p in (getattr(lb, "patterns", []) or [])
                            ):
                                has_named_pat_in_grp = True
                            for vn, vi in lb_vars.items():
                                if vn in grp_pvars:
                                    self.errors.append(
                                        SemanticError(
                                            f"Variável de pattern '{vn}' declarada em múltiplos labels do mesmo grupo de switch (JLS §14.11.1).",
                                            vi.get("line", getattr(lb, "line", 1)),
                                        )
                                    )
                                grp_pvars[vn] = vi

                        if len(grp_labels) > 1 and has_named_pat_in_grp:
                            self.errors.append(
                                SemanticError(
                                    "Múltiplos labels 'case' agrupados antes de um bloco não podem introduzir variáveis de pattern nomeadas (JLS §14.11.1).",
                                    getattr(grp_labels[-1], "line", getattr(grp, "line", 1)),
                                )
                            )
                        if prev_grp_completes_normally and has_named_pat_in_grp:
                            self.errors.append(
                                SemanticError(
                                    "Não é permitido fall-through de um grupo 'case' anterior para um label que declara variável de pattern (JLS §14.11.1).",
                                    getattr(grp_labels[0], "line", getattr(grp, "line", 1)) if grp_labels else getattr(grp, "line", 1),
                                )
                            )

                        self._push_pattern_scope(grp_pvars)
                        try:
                            stmts = list(getattr(grp, "statements", []) or [])
                            self._check_stmt_list_with_flow(stmts)
                        finally:
                            self._pop_pattern_scope()

                        if self._flow_reachable:
                            fallthrough_snap = self._flow_snapshot()
                            if g_idx == num_groups - 1:
                                normal_exits.append(fallthrough_snap)
                        else:
                            fallthrough_snap = None

                        if grp.statements:
                            last_completes = True
                            for s in grp.statements:
                                if not self._stmt_completes_normally(s):
                                    last_completes = False
                                    break
                            prev_grp_completes_normally = last_completes
                        else:
                            prev_grp_completes_normally = is_expression
                    if is_expression and sb.statement_groups and prev_grp_completes_normally:
                        self.errors.append(
                            SemanticError(
                                "Grupo 'case' em switch expression não pode concluir normalmente sem 'yield' ou 'throw' (JLS §15.28.1).",
                                getattr(sb.statement_groups[-1], "line", getattr(switch_node, "line", 1)),
                            )
                        )
            else:
                fallthrough_snap = None
                legacy_cases = list(getattr(switch_node, "cases", []))
                def_block = getattr(switch_node, "default_block", None)
                for c_idx, case_clause in enumerate(legacy_cases):
                    if isinstance(case_clause, SwitchCase):
                        if fallthrough_snap is not None and fallthrough_snap[2]:
                            self._flow_restore(self._flow_join_states(sel_snap, fallthrough_snap))
                        else:
                            self._flow_restore(sel_snap)
                        if case_clause.value is not None:
                            self._check_switch_constant_expr(case_clause.value, getattr(case_clause, "line", 1), enum_const_names)
                        self._check_stmt_list_with_flow(list(case_clause.statements))
                        if self._flow_reachable:
                            fallthrough_snap = self._flow_snapshot()
                            if c_idx == len(legacy_cases) - 1 and def_block is None:
                                normal_exits.append(fallthrough_snap)
                        else:
                            fallthrough_snap = None
                if def_block is not None:
                    seen_default_pos = (getattr(def_block, "line", 1), False)
                    if fallthrough_snap is not None and fallthrough_snap[2]:
                        self._flow_restore(self._flow_join_states(sel_snap, fallthrough_snap))
                    else:
                        self._flow_restore(sel_snap)
                    if isinstance(def_block, Block):
                        self.analyze_block(def_block)
                    else:
                        self.analyze_statement(def_block)
                    if self._flow_reachable:
                        normal_exits.append(self._flow_snapshot())

            # Regras de exaustividade (JLS §14.11.1.1 / §14.11.2 / §15.28.1)
            if is_expression and self._switch_yield_exprs_stack:
                yield_entries = self._switch_yield_exprs_stack.pop()
                yield_nodes = [yn for yn, _ in yield_entries if yn is not None]
                if expected_type and expected_type not in ("var", "desconhecido"):
                    for y_expr, y_line in yield_entries:
                        if y_expr is not None and not self._is_assignable_expr(expected_type, y_expr):
                            yt = self.infer_type(y_expr) or "poly-expression"
                            self.errors.append(
                                SemanticError(
                                    f"Valor produzido em ramo da switch expression ('{yt}') é incompatível com o tipo alvo '{expected_type}' (JLS §15.28.1).",
                                    y_line,
                                )
                            )
                    self._inferred_types[id(switch_node)] = expected_type
                else:
                    uni = self._unify_branch_types(yield_nodes, None)
                    for y_expr, y_line in yield_entries:
                        if y_expr is not None and self.infer_type(y_expr) == "void":
                            self.errors.append(
                                SemanticError(
                                    "Ramo de switch expression não pode produzir tipo 'void' (JLS §15.28.1).",
                                    y_line,
                                )
                            )
                    if uni:
                        self._inferred_types[id(switch_node)] = uni

            needs_exhaustiveness = is_expression or has_pattern_labels or (seen_null_line is not None)
            if needs_exhaustiveness:
                is_exhaustive, unresolved_exhaust = self._check_switch_exhaustiveness(
                    selector_type=selector_type,
                    has_default=(seen_default_pos is not None),
                    unconditional_patterns=unconditional_top_patterns,
                    seen_enum_case_names=seen_enum_case_names,
                    seen_boolean_literals=seen_boolean_literals,
                )
                is_exhaustive_switch = bool(is_exhaustive)
                if not is_exhaustive:
                    if unresolved_exhaust and has_pattern_labels and selector_type and not self._is_known_type(selector_type):
                        self._record_unresolved(
                            f"Exaustividade completa do switch sobre tipo externo '{selector_type}' não pôde ser verificada sem classpath completo."
                        )
                    elif is_expression:
                        self.errors.append(
                            SemanticError(
                                "Switch expression não é exaustiva: adicione 'default' ou cubra todos os casos possíveis (JLS §15.28.1).",
                                getattr(switch_node, "line", 1),
                            )
                        )
                    elif seen_null_line is not None and not has_pattern_labels:
                        self.errors.append(
                            SemanticError(
                                "Switch aprimorado com 'case null' requer exaustividade ('default' ou cobertura completa dos casos — JLS §14.11.2).",
                                getattr(switch_node, "line", 1),
                            )
                        )
                    else:
                        self.errors.append(
                            SemanticError(
                                "Switch statement com patterns requer exaustividade: adicione 'default' ou cubra todos os subtipos/componentes possíveis (JLS §14.11.2).",
                                getattr(switch_node, "line", 1),
                            )
                        )
            else:
                has_uncond_pat = any(
                    self._is_pattern_unconditional(p, selector_type) is True
                    for p in unconditional_top_patterns
                )
                is_exhaustive_switch = (
                    (seen_default_pos is not None)
                    or has_uncond_pat
                    or (selector_base == "boolean" and seen_boolean_literals == {True, False})
                )
        finally:
            if self._flow_exit_frames and self._flow_exit_frames[-1] is sw_frame:
                self._flow_exit_frames.pop()
            if not is_expression:
                self._switch_depth -= 1
            self._pop_pattern_scope()
            self._local_declared_type_scopes.pop()
            self._local_type_scopes.pop()
            if self._local_var_scopes:
                self._flow_cleanup_scope(self._local_var_scopes[-1])
                self._local_var_scopes.pop()
            self.symbols.exit_scope()

        if is_expression:
            if sw_frame["yields"]:
                self._flow_restore(self._flow_join_states(*sw_frame["yields"]))
            else:
                self._flow_restore(self._flow_unreachable())
        else:
            all_exits = branch_exits + normal_exits + sw_frame["breaks"]
            if not is_exhaustive_switch:
                all_exits.append(sel_snap)
            self._flow_restore(self._flow_join_states(*all_exits))

    def _check_switch_exhaustiveness(
        self,
        selector_type: Optional[str],
        has_default: bool,
        unconditional_patterns: List[ASTNode],
        seen_enum_case_names: Set[str],
        seen_boolean_literals: Set[bool],
    ) -> Tuple[bool, bool]:
        """Verifica se o conjunto de labels incondicionais do switch cobre exaustivamente selector_type."""
        if has_default:
            return True, False

        sel_simple = self._simple_base_name(selector_type) if selector_type else None
        # 1. Verifica cobertura por patterns incondicionais sobre selector_type (incluindo sealed + record)
        if unconditional_patterns:
            target_t = selector_type or "Object"
            # Enum pode combinar constantes de enum com patterns de subtipo/enum
            if sel_simple and sel_simple in self._enums:
                enum_decl = self._enums[sel_simple]
                all_consts = {c.name for c in getattr(enum_decl, "constants", [])}
                if all_consts and all_consts.issubset(seen_enum_case_names):
                    return True, False
            # Boolean pode combinar constantes true/false em preview (JEP 530) ou pattern Boolean
            if (
                self.enable_preview_primitive_patterns
                and sel_simple in ("boolean", "Boolean")
                and seen_boolean_literals == {True, False}
            ):
                return True, False

            max_depth = max((self._max_pattern_depth(p) for p in unconditional_patterns), default=0)
            matrix = [[p] for p in unconditional_patterns]
            cov, unres = self._is_vector_covered([target_t], matrix, max_rec_depth=max_depth)
            if cov:
                return True, unres
            return False, unres

        # 2. Switch sem patterns incondicionais: enum completo ou boolean completo
        if sel_simple and sel_simple in self._enums:
            enum_decl = self._enums[sel_simple]
            all_consts = {c.name for c in getattr(enum_decl, "constants", [])}
            if all_consts and all_consts.issubset(seen_enum_case_names):
                return True, False
            return False, False

        if self.enable_preview_primitive_patterns and sel_simple in ("boolean", "Boolean"):
            if seen_boolean_literals == {True, False}:
                return True, False
            return False, False

        is_known = self._is_known_type(selector_type) if selector_type else True
        return False, (not is_known)

    def _is_exception_subtype(self, sub_name: str, super_name: str) -> bool:
        """Verifica relação de subtipo conhecida entre exceções padrão para multicatch/catch."""
        sub_simple = sub_name.split(".")[-1]
        sup_simple = super_name.split(".")[-1]
        cur = sub_simple
        visited: Set[str] = set()
        while cur in self.KNOWN_EXCEPTION_PARENTS and cur not in visited:
            visited.add(cur)
            parent = self.KNOWN_EXCEPTION_PARENTS[cur]
            if parent == sup_simple:
                return True
            cur = parent
        return self._is_subtype(sub_name, super_name) is True

    def _analyze_local_variable_declaration(self, stmt: LocalVariableDeclaration, is_resource: bool = False):
        """Analisa declaração de variável local ou recurso, validando 'var', '_', modificadores e múltiplos declaradores."""
        l_annos = getattr(stmt, "annotations", [])
        l_tref = getattr(stmt, "type_ref", None)
        if l_annos:
            self._analyze_annotations(l_annos, valid_targets={"LOCAL_VARIABLE"}, adjacent_type_ref=l_tref)
        if l_tref is not None:
            self._check_type_ref_annotations(l_tref)
        for ldecl in getattr(stmt, "declarators", []):
            if hasattr(ldecl, "id") and getattr(ldecl.id, "dims_annotations", None):
                for da in ldecl.id.dims_annotations:
                    self._analyze_annotations(da, valid_targets={"TYPE_USE"})

        mods = getattr(stmt, "modifiers", [])
        for mod in mods:
            if mod != "final":
                self.errors.append(
                    SemanticError(f"Modificador '{mod}' não é permitido em declaração de variável local (JLS §14.4).", stmt.line)
                )

        is_final = ("final" in mods) or is_resource
        is_var = getattr(stmt, "is_var", False) or (l_tref is not None and getattr(l_tref, "name", None) == "var")

        raw_decls = getattr(stmt, "declarators", [])
        items: List[Tuple[str, Optional[ASTNode], int, int, Optional[str]]] = []
        if raw_decls:
            for ldecl in raw_decls:
                d_id = getattr(ldecl, "id", None)
                d_name = getattr(ldecl, "name", getattr(d_id, "name", stmt.name))
                d_init = getattr(ldecl, "initializer", None)
                d_dims = getattr(ldecl, "dims", getattr(d_id, "dims", 0))
                d_line = getattr(ldecl, "line", stmt.line)
                d_eff = getattr(ldecl, "effective_type", None)
                items.append((d_name, d_init, d_dims, d_line, d_eff))
        else:
            items.append((stmt.name, stmt.initializer, getattr(stmt, "dims", 0), stmt.line, None))

        if is_var:
            if l_tref is not None and getattr(l_tref, "type_arguments", None):
                self.errors.append(
                    SemanticError("'var' não pode possuir argumentos de tipo genérico (JLS §14.4.1).", stmt.line)
                )
            if l_tref is not None and getattr(l_tref, "dims", 0) > 0:
                self.errors.append(
                    SemanticError("'var' não pode ser combinado com colchetes de array 'var[]' (JLS §14.4.1).", stmt.line)
                )
            if len(items) > 1:
                self.errors.append(
                    SemanticError("'var' não é permitido em declarações com múltiplos declaradores (JLS §14.4.1).", stmt.line)
                )
            for d_name, d_init, d_dims, d_line, _ in items:
                if d_dims > 0:
                    self.errors.append(
                        SemanticError(
                            f"'var' não é permitido com dimensões '[]' no declarador '{d_name}' (JLS §14.4.1).",
                            d_line,
                        )
                    )
                if d_init is None:
                    self.errors.append(
                        SemanticError(
                            f"Variável '{d_name}' declarada com 'var' exige obrigatoriamente um inicializador (JLS §14.4.1).",
                            d_line,
                        )
                    )
                else:
                    if isinstance(d_init, ArrayInitializer):
                        self.errors.append(
                            SemanticError(
                                f"Inicializador de array '{{...}}' não é permitido diretamente com 'var' em '{d_name}' (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    elif isinstance(d_init, Literal) and getattr(d_init, "kind", "") == "NULL":
                        self.errors.append(
                            SemanticError(
                                f"Não é possível inferir o tipo de 'var {d_name}' a partir do literal 'null' (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    elif isinstance(d_init, (LambdaExpression, MethodReference)) or self._is_poly_expression(d_init):
                        self.errors.append(
                            SemanticError(
                                f"Não é possível inferir o tipo de 'var {d_name}' a partir de lambda, method reference ou expressão poly sem tipo alvo explícito (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    if d_name != "_" and self._expr_contains_identifier(d_init, d_name):
                        self.errors.append(
                            SemanticError(
                                f"Autorreferência à variável '{d_name}' não é permitida no inicializador de 'var' (JLS §14.4.1).",
                                d_line,
                            )
                        )
                    self.check_expression(d_init)
                inferred = self.infer_type(d_init) if d_init is not None else None
                if inferred == "void":
                    self.errors.append(
                        SemanticError(
                            f"Não é possível inferir tipo 'var' para '{d_name}' a partir de expressão 'void' (JLS §14.4.1).",
                            d_line,
                        )
                    )
                    inferred = None
                eff_type = inferred if inferred else "var"
                const_res = self._resolve_constant_var_declaration(eff_type, is_final, d_init)
                is_const = const_res is not None
                self._register_local_var(
                    d_name,
                    eff_type,
                    d_line,
                    is_final=is_final,
                    has_initializer=(d_init is not None),
                    category="variavel",
                    is_compile_constant=is_const,
                )
                if is_const and self._local_var_scopes:
                    info = self._local_var_scopes[-1].get(d_name)
                    if info is not None:
                        info["const_typed"] = const_res
                        if const_res[0] in ("byte", "short", "char", "int"):
                            info["const_value"] = int(const_res[1])
                    sym = self.symbols.lookup(d_name)
                    if sym is not None:
                        sym["const_typed"] = const_res
            return

        base_type = getattr(l_tref, "full_name", stmt.type_name) if l_tref is not None else stmt.type_name
        if base_type == "void":
            self.errors.append(
                SemanticError("O tipo 'void' não é válido para declaração de variável local (JLS §14.4).", stmt.line)
            )
        if is_resource and len(items) > 1:
            self.errors.append(
                SemanticError("Declaração de recurso em try-with-resources aceita apenas um declarador (JLS §14.20.3).", stmt.line)
            )

        for d_name, d_init, d_dims, d_line, d_eff in items:
            eff_type = d_eff if d_eff else (base_type + ("[]" * d_dims if d_dims else ""))
            if is_resource and d_init is None:
                self.errors.append(
                    SemanticError(
                        f"Recurso '{d_name}' em try-with-resources deve possuir inicializador (JLS §14.20.3).",
                        d_line,
                    )
                )
            if d_init is not None:
                self._check_expression_with_target(d_init, eff_type)
                self.check_assignment_type(eff_type, d_init, d_name, d_line)
            const_res = self._resolve_constant_var_declaration(eff_type, is_final, d_init)
            is_const = const_res is not None
            self._register_local_var(
                d_name,
                eff_type,
                d_line,
                is_final=is_final,
                has_initializer=(d_init is not None),
                category="variavel",
                is_compile_constant=is_const,
            )
            # Variável constante (JLS §4.12.4): guarda valor constante tipado para propagação e estreitamento (JLS §5.2)
            if is_const and self._local_var_scopes:
                info = self._local_var_scopes[-1].get(d_name)
                if info is not None:
                    info["const_typed"] = const_res
                    if const_res[0] in ("byte", "short", "char", "int"):
                        info["const_value"] = int(const_res[1])
                sym = self.symbols.lookup(d_name)
                if sym is not None:
                    sym["const_typed"] = const_res

    def _check_stmt_list_with_flow(self, stmts: List[ASTNode]):
        """Analisa sequência de instruções propagando variáveis de pattern introduzidas no bloco (JLS §6.3.2)."""
        for stmt in stmts:
            post_vars = self._analyze_statement_with_flow(stmt)
            if post_vars:
                self._inject_pattern_vars_into_enclosing_block(post_vars)

    def _flow_begin_speculative(self) -> Dict[str, Any]:
        """Salva estado semântico antes de simulação especulativa (Passo 1) de laço ou re-checagem poly."""
        frame_lens = [
            (
                f,
                len(f["breaks"]),
                len(f["continues"]),
                len(f["yields"]),
                len(f["returns"]),
                len(f["pending_breaks"]),
                len(f["pending_continues"]),
                len(f["pending_yields"]),
                len(f["pending_returns"]),
            )
            for f in self._flow_exit_frames
        ]
        saved = {
            "err_len": len(self.errors),
            "unres_len": len(self.unresolved_checks),
            "cap_len": len(self._pending_lambda_captures),
            "flags": self._snapshot_local_var_flags(),
            "suppress": self._flow_suppress_errors,
            "frame_lens": frame_lens,
        }
        self._flow_suppress_errors = True
        return saved

    def _flow_end_speculative(self, saved: Dict[str, Any]):
        """Restaura estado semântico descartando diagnósticos e efeitos colaterais de passo especulativo."""
        del self.errors[saved["err_len"]:]
        del self.unresolved_checks[saved["unres_len"]:]
        del self._pending_lambda_captures[saved["cap_len"]:]
        for f, bl, cl, yl, rl, pbl, pcl, pyl, prl in saved["frame_lens"]:
            del f["breaks"][bl:]
            del f["continues"][cl:]
            del f["yields"][yl:]
            del f["returns"][rl:]
            del f["pending_breaks"][pbl:]
            del f["pending_continues"][pcl:]
            del f["pending_yields"][pyl:]
            del f["pending_returns"][prl:]
        self._restore_local_var_flags(saved["flags"])
        self._flow_suppress_errors = saved["suppress"]

    def _flow_execute_loop_passes(
        self,
        labels: Set[str],
        entry_snap: Tuple[Set[Any], Set[Any], bool],
        step_fn,
    ) -> Any:
        """Executa análise de laço em 2 passos (back-edge DU + passo final DA/DU) segundo JLS §16.2.9–§16.2.12."""
        spec = self._flow_begin_speculative()
        p1_frame = self._flow_push_exit_frame("loop", labels)
        try:
            self._flow_restore(entry_snap)
            back_snap, _, _ = step_fn(p1_frame)
        finally:
            if self._flow_exit_frames and self._flow_exit_frames[-1] is p1_frame:
                self._flow_exit_frames.pop()
            self._flow_end_speculative(spec)

        header_snap = self._flow_join_states(entry_snap, back_snap)
        real_frame = self._flow_push_exit_frame("loop", labels)
        try:
            self._flow_restore(header_snap)
            _, post_snap, extra = step_fn(real_frame)
        finally:
            if self._flow_exit_frames and self._flow_exit_frames[-1] is real_frame:
                self._flow_exit_frames.pop()
        self._flow_restore(post_snap)
        return extra

    def _analyze_statement_with_flow(
        self,
        stmt: ASTNode,
        enclosing_labels: Optional[Set[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Analisa uma instrução e retorna variáveis de pattern introduzidas no escopo imediatamente posterior."""
        if stmt is None:
            return {}

        if isinstance(stmt, LabeledStatement):
            line = getattr(stmt, "line", 1)
            next_labels = set(enclosing_labels or ())
            next_labels.add(stmt.label)
            if stmt.label in self._active_labels:
                prev_line = self._active_labels[stmt.label][1]
                self.errors.append(
                    SemanticError(
                        f"Label '{stmt.label}' declarado novamente no mesmo escopo envolvente (linha {prev_line} — JLS §14.7).",
                        line,
                    )
                )
                return self._analyze_statement_with_flow(stmt.statement, enclosing_labels=next_labels)
            target = stmt.statement
            while isinstance(target, LabeledStatement):
                target = target.statement
            is_iterative = isinstance(target, (WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement))
            direct_consumes = isinstance(stmt.statement, (LabeledStatement, WhileStatement, DoWhileStatement, ForStatement, EnhancedForStatement, SwitchStatement))
            self._active_labels[stmt.label] = (is_iterative, line)
            prev_pending = set(self._flow_pending_labels)
            self._flow_pending_labels.add(stmt.label)
            lbl_frame = None
            if not direct_consumes:
                lbl_frame = self._flow_push_exit_frame("label", self._flow_pending_labels)
                self._flow_pending_labels = set()
            try:
                post_vars = self._analyze_statement_with_flow(stmt.statement, enclosing_labels=next_labels)
            finally:
                if lbl_frame is not None:
                    if self._flow_exit_frames and self._flow_exit_frames[-1] is lbl_frame:
                        self._flow_exit_frames.pop()
                    if lbl_frame["breaks"]:
                        self._flow_restore(self._flow_join_states(self._flow_snapshot(), *lbl_frame["breaks"]))
                self._flow_pending_labels = prev_pending
                self._active_labels.pop(stmt.label, None)
            if self._contains_break_targeting(stmt.statement, target_label=stmt.label):
                return {}
            return post_vars

        if isinstance(stmt, IfStatement):
            true_vars, false_vars, true_st, false_st = self._check_boolean_condition_with_states(
                stmt.condition, "if", getattr(stmt, "line", 1)
            )
            self._flow_restore(true_st)
            self._push_pattern_scope(true_vars)
            try:
                self.analyze_statement(stmt.then_branch)
                then_out = self._flow_snapshot()
            finally:
                self._pop_pattern_scope()

            if stmt.else_branch is not None:
                self._flow_restore(false_st)
                self._push_pattern_scope(false_vars)
                try:
                    self.analyze_statement(stmt.else_branch)
                    else_out = self._flow_snapshot()
                finally:
                    self._pop_pattern_scope()
                self._flow_restore(self._flow_join_states(then_out, else_out))
                then_norm = self._stmt_completes_normally(stmt.then_branch)
                else_norm = self._stmt_completes_normally(stmt.else_branch)
                if not then_norm and else_norm:
                    return dict(false_vars)
                if then_norm and not else_norm:
                    return dict(true_vars)
                return {}

            self._flow_restore(self._flow_join_states(then_out, false_st))
            if not self._stmt_completes_normally(stmt.then_branch):
                return dict(false_vars)
            return {}

        if isinstance(stmt, WhileStatement):
            labels = set(self._flow_pending_labels)
            self._flow_pending_labels = set()
            entry_snap = self._flow_snapshot()
            self._loop_depth += 1
            try:
                def while_step(frame: Dict[str, Any]):
                    tv, fv, tst, fst = self._check_boolean_condition_with_states(
                        stmt.condition, "while", getattr(stmt, "line", 1)
                    )
                    self._flow_restore(tst)
                    self._push_pattern_scope(tv)
                    try:
                        self.analyze_statement(stmt.body)
                        body_out = self._flow_snapshot()
                    finally:
                        self._pop_pattern_scope()
                    back = self._flow_join_states(body_out, *frame["continues"])
                    post = self._flow_join_states(fst, *frame["breaks"])
                    return back, post, fv

                false_vars = self._flow_execute_loop_passes(labels, entry_snap, while_step)
            finally:
                self._loop_depth -= 1
            if false_vars and not self._contains_break_targeting(stmt.body, target_label=None, extra_labels=enclosing_labels):
                return dict(false_vars)
            return {}

        if isinstance(stmt, ForStatement):
            labels = set(self._flow_pending_labels)
            self._flow_pending_labels = set()
            self.symbols.enter_scope()
            push_local = bool(self._local_var_scopes)
            if push_local:
                self._local_var_scopes.append({})
            self._active_pattern_scopes.append({})
            self._loop_depth += 1
            false_vars: Dict[str, Dict[str, Any]] = {}
            try:
                if stmt.init is not None:
                    self.analyze_statement(stmt.init)
                after_init = self._flow_snapshot()

                def for_step(frame: Dict[str, Any]):
                    tv: Dict[str, Dict[str, Any]] = {}
                    fv: Dict[str, Dict[str, Any]] = {}
                    if stmt.condition is not None:
                        tv, fv, tst, fst = self._check_boolean_condition_with_states(
                            stmt.condition, "for", getattr(stmt, "line", 1)
                        )
                    else:
                        tst = self._flow_snapshot()
                        fst = self._flow_unreachable()
                    self._flow_restore(tst)
                    self._push_pattern_scope(tv)
                    try:
                        if stmt.body is not None:
                            self.analyze_statement(stmt.body)
                        body_out = self._flow_snapshot()
                        before_update = self._flow_join_states(body_out, *frame["continues"])
                        self._flow_restore(before_update)
                        if stmt.update is not None:
                            if isinstance(stmt.update, StatementExpressionList):
                                for uexpr in stmt.update.expressions:
                                    self.check_expression(uexpr)
                            else:
                                self.check_expression(stmt.update)
                        back = self._flow_snapshot()
                    finally:
                        self._pop_pattern_scope()
                    post = self._flow_join_states(fst, *frame["breaks"])
                    return back, post, fv

                false_vars = self._flow_execute_loop_passes(labels, after_init, for_step)
            finally:
                self._loop_depth -= 1
                self._pop_pattern_scope()
                if push_local:
                    self._flow_cleanup_scope(self._local_var_scopes[-1])
                    self._local_var_scopes.pop()
                self.symbols.exit_scope()
            if false_vars and not self._contains_break_targeting(stmt.body, target_label=None, extra_labels=enclosing_labels):
                return dict(false_vars)
            return {}

        self.analyze_statement(stmt)
        return {}

    def analyze_block(self, block_node: Block):
        """Analisa instruções dentro de um bloco de código com controle de escopo local e flow-scoping S7."""
        if not block_node or not hasattr(block_node, "statements"):
            return
        self.symbols.enter_scope()
        push_local = bool(self._local_var_scopes)
        if push_local:
            self._local_var_scopes.append({})
        self._active_pattern_scopes.append({})
        self._local_type_scopes.append({})
        self._local_declared_type_scopes.append({})
        for stmt in block_node.statements:
            if isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
                self._index_local_type_decl(stmt)
        try:
            self._check_stmt_list_with_flow(block_node.statements)
        finally:
            self._local_declared_type_scopes.pop()
            self._local_type_scopes.pop()
            self._pop_pattern_scope()
            if push_local:
                self._flow_cleanup_scope(self._local_var_scopes[-1])
                self._local_var_scopes.pop()
            self.symbols.exit_scope()

    def analyze_statement(self, stmt: ASTNode):
        """Analisa uma declaração ou instrução isolada com validações contextuais completas (S6/S7)."""
        if stmt is None:
            return

        if isinstance(stmt, (Declaration, LocalVariableDeclaration)):
            self._analyze_local_variable_declaration(stmt, is_resource=False)

        elif isinstance(stmt, StatementExpressionList):
            for expr in stmt.expressions:
                self.check_expression(expr)

        elif isinstance(stmt, Assignment):
            self._check_assignment(stmt)

        elif isinstance(stmt, LabeledStatement):
            self._analyze_statement_with_flow(stmt)

        elif isinstance(stmt, ReturnStatement):
            line = getattr(stmt, "line", 1)
            if self._in_compact_constructor:
                self.errors.append(
                    SemanticError("Instrução 'return' não é permitida dentro de um construtor compacto de record (JLS §8.10.4.2).", line)
                )
            elif self._callable_kind == "initializer":
                self.errors.append(
                    SemanticError("Instrução 'return' não é permitida dentro de um bloco inicializador (JLS §8.6 / §8.7 / §14.17).", line)
                )
            elif self._switch_expr_depth > 0:
                self.errors.append(
                    SemanticError("Instrução 'return' não é permitida dentro de uma switch expression (JLS §14.17).", line)
                )
            elif self._callable_kind == "constructor":
                if stmt.expression is not None:
                    self.errors.append(
                        SemanticError("Construtor não pode retornar valor com expressão em 'return' (JLS §8.8.4 / §14.17).", line)
                    )
            elif self._callable_kind == "lambda":
                if self._lambda_return_exprs_stack:
                    self._lambda_return_exprs_stack[-1].append(stmt.expression)
                if self._current_return_type == "void" and stmt.expression is not None:
                    self.errors.append(
                        SemanticError("Expressão lambda com retorno 'void' não pode retornar valor em 'return' (JLS §15.27.3).", line)
                    )
                elif self._current_return_type not in (None, "void") and stmt.expression is None:
                    self.errors.append(
                        SemanticError(
                            f"Expressão lambda com tipo de retorno '{self._current_return_type}' deve retornar valor em 'return' (JLS §15.27.3).",
                            line,
                        )
                    )
            elif self._callable_kind == "method":
                if self._current_return_type == "void" and stmt.expression is not None:
                    self.errors.append(
                        SemanticError("Método 'void' não pode retornar valor em 'return' (JLS §14.17).", line)
                    )
                elif self._current_return_type not in (None, "void") and stmt.expression is None:
                    self.errors.append(
                        SemanticError(
                            f"Método com tipo de retorno '{self._current_return_type}' deve retornar valor em 'return' (JLS §14.17).",
                            line,
                        )
                    )
            if stmt.expression is not None:
                ret_target = self._current_return_type if self._current_return_type not in (None, "void") else None
                if ret_target:
                    self._check_expression_with_target(stmt.expression, ret_target)
                    if not self._is_type_variable(ret_target) and not self._is_assignable_expr(ret_target, stmt.expression):
                        expr_t = self.infer_type(stmt.expression)
                        self.errors.append(
                            SemanticError(
                                f"Tipo retornado incompatível: esperado '{ret_target}', encontrado '{expr_t}' (JLS §14.17 / §15.27.3).",
                                line,
                            )
                        )
                else:
                    self.check_expression(stmt.expression)
            self._flow_record_return()

        elif isinstance(stmt, YieldStatement):
            line = getattr(stmt, "line", 1)
            if self._switch_expr_depth <= 0:
                self.errors.append(
                    SemanticError("Instrução 'yield' só é permitida dentro de uma switch expression (JLS §14.21).", line)
                )
                self.check_expression(stmt.expression)
            else:
                exp_t = self._switch_expected_type_stack[-1] if self._switch_expected_type_stack else None
                self._check_expression_with_target(stmt.expression, exp_t)
                if self._switch_yield_exprs_stack:
                    self._switch_yield_exprs_stack[-1].append((stmt.expression, line))
            self._flow_record_yield()

        elif isinstance(stmt, BreakStatement):
            line = getattr(stmt, "line", 1)
            if stmt.label:
                if stmt.label not in self._active_labels:
                    self.errors.append(
                        SemanticError(
                            f"Label '{stmt.label}' não encontrado ou fora de alcance para 'break' (JLS §14.15).",
                            line,
                        )
                    )
            elif self._loop_depth <= 0 and self._switch_depth <= 0:
                self.errors.append(
                    SemanticError("Instrução 'break' fora de laço ou switch (JLS §14.15).", line)
                )
            self._flow_record_break(stmt.label)

        elif isinstance(stmt, ContinueStatement):
            line = getattr(stmt, "line", 1)
            if stmt.label:
                if stmt.label not in self._active_labels:
                    self.errors.append(
                        SemanticError(
                            f"Label '{stmt.label}' não encontrado ou fora de alcance para 'continue' (JLS §14.16).",
                            line,
                        )
                    )
                elif not self._active_labels[stmt.label][0]:
                    self.errors.append(
                        SemanticError(
                            f"Instrução 'continue {stmt.label}' só pode referenciar um laço iterativo (JLS §14.16).",
                            line,
                        )
                    )
            elif self._loop_depth <= 0:
                self.errors.append(
                    SemanticError("Instrução 'continue' fora de laço (JLS §14.16).", line)
                )
            self._flow_record_continue(stmt.label)

        elif isinstance(stmt, (IfStatement, WhileStatement, ForStatement)):
            self._analyze_statement_with_flow(stmt)

        elif isinstance(stmt, DoWhileStatement):
            labels = set(self._flow_pending_labels)
            self._flow_pending_labels = set()
            entry_snap = self._flow_snapshot()
            self._loop_depth += 1
            try:
                def do_while_step(frame: Dict[str, Any]):
                    self.analyze_statement(stmt.body)
                    body_out = self._flow_snapshot()
                    before_cond = self._flow_join_states(body_out, *frame["continues"])
                    self._flow_restore(before_cond)
                    _, _, tst, fst = self._check_boolean_condition_with_states(
                        stmt.condition, "do-while", getattr(stmt, "line", 1)
                    )
                    post = self._flow_join_states(fst, *frame["breaks"])
                    return tst, post, None

                self._flow_execute_loop_passes(labels, entry_snap, do_while_step)
            finally:
                self._loop_depth -= 1

        elif isinstance(stmt, EnhancedForStatement):
            labels = set(self._flow_pending_labels)
            self._flow_pending_labels = set()
            self.symbols.enter_scope()
            push_local = bool(self._local_var_scopes)
            if push_local:
                self._local_var_scopes.append({})
            self._loop_depth += 1
            try:
                # Avalia expressão iterável antes de registrar a variável do cabeçalho
                self.check_expression(stmt.iterable)
                var = stmt.variable
                v_annos = getattr(var, "annotations", [])
                v_tref = getattr(var, "type_ref", None)
                self._analyze_annotations(
                    v_annos,
                    valid_targets={"LOCAL_VARIABLE"},
                    adjacent_type_ref=v_tref,
                )
                self._check_type_ref_annotations(v_tref)
                for vm in getattr(var, "modifiers", []):
                    if vm != "final":
                        self.errors.append(
                            SemanticError(f"Modificador '{vm}' inválido em variável de for-each (JLS §14.14.2).", getattr(var, "line", stmt.line))
                        )
                v_is_var = getattr(var, "is_var", False) or (v_tref is not None and getattr(v_tref, "name", None) == "var")
                v_dims = getattr(var, "dims", 0)
                if v_is_var and (v_dims > 0 or (v_tref is not None and getattr(v_tref, "dims", 0) > 0)):
                    self.errors.append(
                        SemanticError("'var' não pode ser combinado com colchetes de array '[]' em for-each (JLS §14.14.2).", getattr(var, "line", stmt.line))
                    )
                if hasattr(var, "name") and var.name != "_":
                    t_name = "var" if v_is_var else getattr(var, "effective_type", getattr(var, "type_name", "Object"))
                    self._register_local_var(
                        var.name,
                        t_name,
                        getattr(var, "line", stmt.line),
                        is_final=("final" in getattr(var, "modifiers", [])),
                        has_initializer=True,
                        category="variavel",
                    )
                after_header = self._flow_snapshot()

                def foreach_step(frame: Dict[str, Any]):
                    if stmt.body is not None:
                        self.analyze_statement(stmt.body)
                    body_out = self._flow_snapshot()
                    back = self._flow_join_states(body_out, *frame["continues"])
                    # Em for-each (0+ iterações), após o laço combinamos o header atual (já com DU de back-edge) e breaks
                    post = self._flow_join_states(self._flow_join_states(after_header, back), *frame["breaks"])
                    return back, post, None

                if stmt.body is not None:
                    self._flow_execute_loop_passes(labels, after_header, foreach_step)
            finally:
                self._loop_depth -= 1
                if push_local:
                    self._flow_cleanup_scope(self._local_var_scopes[-1])
                    self._local_var_scopes.pop()
                self.symbols.exit_scope()

        elif isinstance(stmt, SwitchStatement):
            self._analyze_switch_block(stmt, is_expression=False)

        elif isinstance(stmt, TryStatement):
            entry_snap = self._flow_snapshot()
            has_finally = stmt.finally_block is not None
            tf_frame = self._flow_push_exit_frame("try_finally") if has_finally else None
            try_writes: Set[Any] = set()
            self._flow_write_trackers.append(try_writes)
            try_frame = self._exception_analyzer.push_try_frame()
            try:
                res_spec = getattr(stmt, "resource_specification", None)
                res_nodes = res_spec.resources if res_spec is not None else stmt.resources
                has_resources = bool(res_nodes)
                if has_resources:
                    self.symbols.enter_scope()
                    push_res = bool(self._local_var_scopes)
                    if push_res:
                        self._local_var_scopes.append({})
                    try:
                        res_close_targets: List[Tuple[Optional[str], int]] = []
                        for res in res_nodes:
                            res_line = getattr(res, "line", stmt.line)
                            if isinstance(res, Resource):
                                if res.is_reference:
                                    self.check_expression(res.variable_access)
                                    res_close_targets.append((self.infer_type(res.variable_access), res_line))
                                    if isinstance(res.variable_access, Identifier):
                                        rname = res.variable_access.name
                                        linfo = self._find_local_var_info(rname)
                                        sym = self.symbols.lookup(rname)
                                        if linfo is not None and not linfo.get("is_final", False) and linfo.get("reassigned", False):
                                            self.errors.append(
                                                SemanticError(
                                                    f"Recurso '{rname}' em try-with-resources deve ser 'final' ou efetivamente final (JLS §14.20.3).",
                                                    getattr(res, "line", stmt.line),
                                                )
                                            )
                                        elif sym is not None and sym.get("category") == "campo" and not sym.get("is_final", False):
                                            self.errors.append(
                                                SemanticError(
                                                    f"Campo '{rname}' referenciado em try-with-resources deve ser 'final' ou efetivamente final (JLS §14.20.3).",
                                                    getattr(res, "line", stmt.line),
                                                )
                                            )
                                    elif isinstance(res.variable_access, MemberAccess) and isinstance(res.variable_access.target, Identifier) and res.variable_access.target.name == "this":
                                        sym = self.symbols.lookup(res.variable_access.member_name)
                                        if sym is not None and sym.get("category") == "campo" and not sym.get("is_final", False):
                                            self.errors.append(
                                                SemanticError(
                                                    f"Campo 'this.{res.variable_access.member_name}' em try-with-resources deve ser 'final' (JLS §14.20.3).",
                                                    getattr(res, "line", stmt.line),
                                                )
                                            )
                                elif res.declaration is not None:
                                    self._analyze_local_variable_declaration(res.declaration, is_resource=True)
                                    decls = getattr(res.declaration, "declarators", None) or []
                                    for d in decls:
                                        dsym = self.symbols.lookup(d.name) if getattr(d, "name", None) else None
                                        dt = dsym.get("type") if dsym else None
                                        if not dt and getattr(res.declaration, "type_ref", None) is not None:
                                            dt = self._normalize_type_str(res.declaration.type_ref)
                                        res_close_targets.append((dt, getattr(d, "line", res_line)))
                            else:
                                self._analyze_local_variable_declaration(res, is_resource=True)
                                decls = getattr(res, "declarators", None) or []
                                for d in decls:
                                    dsym = self.symbols.lookup(d.name) if getattr(d, "name", None) else None
                                    dt = dsym.get("type") if dsym else None
                                    if not dt and getattr(res, "type_ref", None) is not None:
                                        dt = self._normalize_type_str(res.type_ref)
                                    res_close_targets.append((dt, getattr(d, "line", res_line)))
                        for res_t, res_ln in res_close_targets:
                            if not res_t or res_t in ("var", "desconhecido"):
                                self._exception_analyzer.mark_unresolved_thrower()
                                continue
                            clean_res_t = self._strip_leading_type_annotations(res_t) or res_t
                            if (
                                clean_res_t in self.PRIMITIVE_TYPES
                                or clean_res_t == "void"
                                or self._is_subtype(clean_res_t, "AutoCloseable") is False
                            ):
                                self.errors.append(
                                    SemanticError(
                                        f"Recurso de tipo '{clean_res_t}' em try-with-resources não implementa 'java.lang.AutoCloseable' (JLS §14.20.3).",
                                        res_ln,
                                    )
                                )
                                continue
                            close_sigs, is_known_res, is_decl_res = self._collect_type_methods(res_t, "close")
                            zero_close = [
                                cs for cs in close_sigs
                                if not cs.get("static") and len(cs.get("params", [])) == 0
                            ]
                            if zero_close:
                                self._exception_analyzer.emit_thrown(
                                    zero_close[0].get("throws", []),
                                    res_ln,
                                    f"fechamento automático de '{res_t}.close()'",
                                )
                            elif not is_known_res and not is_decl_res:
                                self._exception_analyzer.mark_unresolved_thrower()
                        if stmt.body is not None:
                            self.analyze_block(stmt.body)
                        try_out = self._flow_snapshot()
                    finally:
                        if push_res:
                            self._flow_cleanup_scope(self._local_var_scopes[-1])
                            self._local_var_scopes.pop()
                        self.symbols.exit_scope()
                else:
                    if stmt.body is not None:
                        self.analyze_block(stmt.body)
                    try_out = self._flow_snapshot()
            finally:
                if self._flow_write_trackers and self._flow_write_trackers[-1] is try_writes:
                    self._flow_write_trackers.pop()
                self._exception_analyzer.pop_try_frame()

            try_and_catch_writes: Set[Any] = set(try_writes)
            self._flow_write_trackers.append(try_and_catch_writes)
            catch_in_snap = (set(entry_snap[0]), set(entry_snap[1]) - try_writes, entry_snap[2])
            catch_outs: List[Tuple[Set[Any], Set[Any], bool]] = []
            caught_exceptions: List[Tuple[str, int]] = []
            try:
                for catch_c in stmt.catches:
                    self._flow_restore(catch_in_snap)
                    self.symbols.enter_scope()
                    push_catch = bool(self._local_var_scopes)
                    if push_catch:
                        self._local_var_scopes.append({})
                    try:
                        c_param = catch_c.parameter
                        c_types = catch_c.catch_types
                        if c_param is not None:
                            self._analyze_annotations(
                                getattr(c_param, "annotations", []),
                                valid_targets={"PARAMETER"},
                                adjacent_type_ref=getattr(c_param, "type_ref", None),
                            )
                            for cm in getattr(c_param, "modifiers", []):
                                if cm != "final":
                                    self.errors.append(
                                        SemanticError(f"Modificador '{cm}' inválido em parâmetro de catch (JLS §14.20).", getattr(c_param, "line", catch_c.line))
                                    )
                        for ct in c_types:
                            self._check_type_ref_annotations(ct)
                            if getattr(ct, "name", None) == "var":
                                self.errors.append(
                                    SemanticError("'var' não é permitido como tipo de parâmetro de catch (JLS §14.20).", getattr(ct, "line", catch_c.line))
                                )
                        self._exception_analyzer.validate_catch_and_reachability(
                            c_types,
                            catch_c.line,
                            caught_exceptions,
                            try_frame,
                        )

                        if c_param is not None and c_param.name != "_":
                            is_catch_final = ("final" in getattr(c_param, "modifiers", [])) or (len(c_types) > 1)
                            catch_type_label = " | ".join(t.full_name for t in c_types) if c_types else (
                                c_param.type_ref.name if getattr(c_param, "type_ref", None) else "Throwable"
                            )
                            self._register_local_var(
                                c_param.name,
                                catch_type_label,
                                getattr(c_param, "line", catch_c.line),
                                is_final=is_catch_final,
                                has_initializer=True,
                                category="parametro",
                            )
                            rethrow_types = self._exception_analyzer.compute_precise_rethrow_types(c_types, try_frame)
                            if rethrow_types is not None:
                                c_linfo = self._find_local_var_info(c_param.name)
                                if c_linfo is not None:
                                    c_linfo["precise_rethrow_types"] = rethrow_types
                        if catch_c.body is not None:
                            self.analyze_block(catch_c.body)
                        catch_outs.append(self._flow_snapshot())
                    finally:
                        if push_catch:
                            self._flow_cleanup_scope(self._local_var_scopes[-1])
                            self._local_var_scopes.pop()
                        self.symbols.exit_scope()
            finally:
                if self._flow_write_trackers and self._flow_write_trackers[-1] is try_and_catch_writes:
                    self._flow_write_trackers.pop()

            self._exception_analyzer.propagate_try_uncaught(
                try_frame,
                [ex_name for ex_name, _ in caught_exceptions],
            )

            after_tc = self._flow_join_states(try_out, *catch_outs)
            if has_finally and tf_frame is not None:
                if self._flow_exit_frames and self._flow_exit_frames[-1] is tf_frame:
                    self._flow_exit_frames.pop()
                finally_writes: Set[Any] = set()
                self._flow_write_trackers.append(finally_writes)
                try:
                    finally_in = (set(entry_snap[0]), set(entry_snap[1]) - try_and_catch_writes, entry_snap[2])
                    self._flow_restore(finally_in)
                    self.analyze_block(stmt.finally_block)
                    finally_out = self._flow_snapshot()
                finally:
                    if self._flow_write_trackers and self._flow_write_trackers[-1] is finally_writes:
                        self._flow_write_trackers.pop()

                finally_completes = finally_out[2]
                finally_da_added = (finally_out[0] - entry_snap[0]) if finally_completes else set()
                self._flow_forward_abrupt_through_finally(
                    tf_frame["pending_breaks"],
                    tf_frame["pending_continues"],
                    finally_da_added,
                    finally_writes,
                    finally_completes,
                    pending_yields=tf_frame["pending_yields"],
                    pending_returns=tf_frame["pending_returns"],
                )
                if finally_completes and after_tc[2]:
                    self._flow_restore((after_tc[0] | finally_da_added, after_tc[1] - finally_writes, True))
                else:
                    self._flow_restore(self._flow_unreachable())
            else:
                self._flow_restore(after_tc)

        elif isinstance(stmt, SynchronizedStatement):
            self.check_expression(stmt.lock)
            lock_t = self.infer_type(stmt.lock)
            if lock_t and (lock_t in self.PRIMITIVE_TYPES or lock_t == "void"):
                self.errors.append(
                    SemanticError(
                        f"Expressão de bloqueio em 'synchronized' deve possuir tipo de referência (encontrado '{lock_t}' — JLS §14.19).",
                        getattr(stmt, "line", 1),
                    )
                )
            if stmt.body is not None:
                self.analyze_block(stmt.body)

        elif isinstance(stmt, ThrowStatement):
            self.check_expression(stmt.expression)
            exc_t = self.infer_type(stmt.expression)
            line = getattr(stmt, "line", 1)
            if exc_t:
                if self._exception_analyzer.is_valid_throwable(exc_t) is False:
                    self.errors.append(
                        SemanticError(
                            f"Expressão em 'throw' deve ser subtipo de 'Throwable' (encontrado '{exc_t}' — JLS §14.18).",
                            line,
                        )
                    )
                else:
                    emit_types = [exc_t]
                    if isinstance(stmt.expression, Identifier):
                        linfo = self._find_local_var_info(stmt.expression.name)
                        if (
                            linfo is not None
                            and not linfo.get("reassigned", False)
                            and "precise_rethrow_types" in linfo
                        ):
                            emit_types = list(linfo["precise_rethrow_types"])
                    self._exception_analyzer.emit_thrown(emit_types, line, "instrução 'throw'")
            self._flow_reachable = False

        elif isinstance(stmt, AssertStatement):
            self._check_boolean_condition(stmt.condition, "assert", getattr(stmt, "line", 1))
            if stmt.message is not None:
                self.check_expression(stmt.message)

        elif isinstance(stmt, ExpressionStatement):
            self.check_expression(stmt.expression)

        elif isinstance(stmt, Block):
            self.analyze_block(stmt)

        elif isinstance(stmt, EmptyStatement):
            pass

        elif isinstance(stmt, (ClassDeclaration, InterfaceDeclaration, EnumDeclaration, RecordDeclaration, AnnotationInterfaceDeclaration)):
            saved_compact = self._in_compact_constructor
            self._in_compact_constructor = False
            try:
                self._analyze_type_declaration(stmt, is_nested=True, is_local=True)
            finally:
                self._in_compact_constructor = saved_compact

    def _record_unresolved(self, reason: str):
        """Registra verificação pendente por ausência de classpath completo sem duplicatas."""
        if reason and reason not in self.unresolved_checks:
            self.unresolved_checks.append(reason)

    def _current_enclosing_type(self) -> Optional[str]:
        """Retorna o nome do tipo declarador mais interno em análise."""
        return self._enclosing_type_names[-1] if self._enclosing_type_names else None

    def _resolve_param_effective_type(self, param: ASTNode) -> str:
        """Retorna o tipo efetivo de parâmetro formal (tratando varargs como array dentro do corpo)."""
        raw = getattr(param, "effective_type", None)
        if not raw and getattr(param, "type_ref", None) is not None:
            raw = getattr(param.type_ref, "full_name", getattr(param.type_ref, "name", "Object"))
        raw = raw or "Object"
        if getattr(param, "is_varargs", False):
            if raw.endswith("..."):
                return raw[:-3] + "[]"
            if not raw.endswith("[]"):
                return raw + "[]"
        return raw

    @staticmethod
    def _strip_leading_type_annotations(type_str: Optional[str]) -> Optional[str]:
        """Remove anotações de tipo prefixadas mantendo genéricos e dimensões de array."""
        if not type_str:
            return None
        s = type_str.strip()
        while s.startswith("@"):
            idx = 1
            while idx < len(s) and (s[idx].isalnum() or s[idx] in "._$"):
                idx += 1
            if idx < len(s) and s[idx] == "(":
                depth = 1
                idx += 1
                in_str = False
                while idx < len(s) and depth > 0:
                    ch = s[idx]
                    if ch == '"' and s[idx - 1] != "\\":
                        in_str = not in_str
                    elif not in_str:
                        if ch == "(":
                            depth += 1
                        elif ch == ")":
                            depth -= 1
                    idx += 1
            s = s[idx:].lstrip()
        return s or None

    @staticmethod
    def _strip_type_dims_full(type_str: Optional[str]) -> Tuple[str, int]:
        """Separa dimensões de array finais preservando argumentos genéricos do tipo base."""
        if not type_str:
            return "", 0
        s = type_str.strip()
        dims = 0
        while s.endswith("[]"):
            dims += 1
            s = s[:-2].strip()
        return s, dims

    def _is_type_variable(self, type_str: Optional[str]) -> bool:
        """Identifica variáveis de tipo genérico não instanciadas (ex: T, E, R)."""
        if not type_str:
            return False
        if self._is_capture_var(type_str):
            return False
        s, dims = self._strip_type_dims_full(self._strip_generics(type_str))
        if not s or "." in s:
            return False
        if self._lookup_type_param_bounds(s) is not None:
            return True
        if s in self.PRIMITIVE_TYPES or s in self.BUILTIN_TYPE_SUPERTYPES or s in self.KNOWN_EXCEPTION_PARENTS:
            return False
        if self._lookup_type_decl(s) is not None:
            return False
        if self._resolve_external_type(type_str) is not None:
            return False
        return len(s) <= 2 and s[0].isupper()

    def _unbox_type(self, type_str: Optional[str]) -> Optional[str]:
        """Realiza unboxing para o primitivo correspondente quando aplicável (JLS §5.1.8)."""
        if not type_str:
            return None
        s = self._simple_base_name(type_str)
        if not s or s.endswith("[]"):
            return None
        if s in self.PRIMITIVE_TYPES:
            return s
        return self.WRAPPER_TO_PRIMITIVE.get(s)

    def _box_type(self, type_str: Optional[str]) -> Optional[str]:
        """Realiza boxing de tipo primitivo para sua classe wrapper (JLS §5.1.7)."""
        if not type_str:
            return None
        s = self._simple_base_name(type_str)
        if s in self.PRIMITIVE_TO_WRAPPER:
            return self.PRIMITIVE_TO_WRAPPER[s]
        return type_str

    def _unboxed_numeric(self, type_str: Optional[str]) -> Optional[str]:
        """Retorna o tipo primitivo numérico se type_str for primitivo numérico ou wrapper correspondente."""
        prim = self._unbox_type(type_str)
        if prim in self.NUMERIC_PRIMITIVE_TYPES:
            return prim
        return None

    def _is_integral_type(self, type_str: Optional[str]) -> bool:
        """Retorna True se type_str for tipo integral primitivo ou wrapper integral."""
        return self._unbox_type(type_str) in self.INTEGRAL_PRIMITIVES

    def _is_boolean_type(self, type_str: Optional[str]) -> bool:
        """Retorna True se type_str for boolean ou Boolean."""
        return self._unbox_type(type_str) == "boolean"

    def _unary_numeric_promotion(self, type_str: Optional[str]) -> Optional[str]:
        """Aplica promoção numérica unária da JLS §5.6 (byte/short/char -> int)."""
        prim = self._unboxed_numeric(type_str)
        if prim is None:
            return None
        if prim in ("byte", "short", "char", "int"):
            return "int"
        return prim

    def _binary_numeric_promotion(self, left: Optional[str], right: Optional[str]) -> Optional[str]:
        """Aplica promoção numérica binária da JLS §5.6."""
        lp = self._unboxed_numeric(left)
        rp = self._unboxed_numeric(right)
        if lp is None or rp is None:
            return None
        if "double" in (lp, rp):
            return "double"
        if "float" in (lp, rp):
            return "float"
        if "long" in (lp, rp):
            return "long"
        return "int"

    def _eval_constant_int_literal(self, expr: Optional[ASTNode]) -> Optional[int]:
        """Avalia expressões constantes byte/short/char/int para checagem de narrowing (JLS §5.2 / §15.29)."""
        res = self._eval_constant_expr(expr)
        if res is not None and res[0] in ("byte", "short", "char", "int"):
            return int(res[1])
        return None

    def _is_constant_narrowing_compatible(self, target_prim: str, expr: Optional[ASTNode]) -> bool:
        """Verifica se expressão constante de tipo byte/short/char/int cabe em byte/short/char (JLS §5.2)."""
        if target_prim not in self.INTEGER_RANGES or expr is None:
            return False
        res = self._eval_constant_expr(expr)
        if res is None:
            return False
        src_t, const_val = res
        if src_t not in ("byte", "short", "char", "int"):
            return False
        lo, hi = self.INTEGER_RANGES[target_prim]
        return lo <= const_val <= hi

    def _is_assignable_expr(self, target_type: Optional[str], expr: Optional[ASTNode]) -> bool:
        """Verifica compatibilidade de atribuição incluindo boxing, unboxing e narrowing constante."""
        if not target_type or expr is None:
            return True
        if isinstance(expr, (LambdaExpression, MethodReference)):
            sam, _ = self._resolve_functional_interface(target_type)
            return sam is not None
        t_clean = self._strip_leading_type_annotations(target_type)
        wrapper_to_narrow = {"Byte": "byte", "Short": "short", "Character": "char"}
        t_base = self._simple_base_name(t_clean) or t_clean
        if isinstance(expr, ConditionalExpression):
            c_res = self._eval_constant_expr(expr)
            if c_res is not None:
                if t_clean in self.INTEGER_RANGES:
                    return self._is_constant_narrowing_compatible(t_clean, expr)
                if t_base in wrapper_to_narrow:
                    return self._is_constant_narrowing_compatible(wrapper_to_narrow[t_base], expr)
            return self._is_assignable_expr(target_type, expr.then_expr) and self._is_assignable_expr(target_type, expr.else_expr)
        expr_type = self.infer_type(expr)
        if expr_type is None:
            return True
        if self.is_assignable(target_type, expr_type):
            return True
        if t_clean in self.INTEGER_RANGES and self._is_constant_narrowing_compatible(t_clean, expr):
            return True
        if t_base in wrapper_to_narrow and self._is_constant_narrowing_compatible(wrapper_to_narrow[t_base], expr):
            return True
        return False

    def _lub_type(self, t1: Optional[str], t2: Optional[str]) -> Optional[str]:
        """Computa o tipo unificado aproximado para ternário e switch expression (JLS §15.25 / §15.28)."""
        if not t1:
            return t2
        if not t2:
            return t1
        if t1 == "var":
            return t2
        if t2 == "var":
            return t1
        if t1 == t2:
            return t1
        if t1 == "null":
            return "Object" if t2 in self.PRIMITIVE_TYPES else t2
        if t2 == "null":
            return "Object" if t1 in self.PRIMITIVE_TYPES else t1

        p1 = self._unbox_type(t1)
        p2 = self._unbox_type(t2)
        if p1 in self.NUMERIC_PRIMITIVE_TYPES and p2 in self.NUMERIC_PRIMITIVE_TYPES:
            if t1 == "boolean" or t2 == "boolean":
                return "Object"
            if t1 not in self.PRIMITIVE_TYPES and t2 not in self.PRIMITIVE_TYPES:
                # Ambos wrappers numéricos (ex: Integer e Double) -> Number
                return "Number"
            if {p1, p2} == {"byte", "short"}:
                return "short"
            if p1 in ("byte", "short", "char") and p2 == "int":
                return "int"
            if p2 in ("byte", "short", "char") and p1 == "int":
                return "int"
            return self._binary_numeric_promotion(p1, p2)
        if p1 == "boolean" and p2 == "boolean":
            return "boolean" if ("boolean" in (t1, t2)) else "Boolean"

        b1 = self._box_type(t1) if t1 in self.PRIMITIVE_TYPES else t1
        b2 = self._box_type(t2) if t2 in self.PRIMITIVE_TYPES else t2
        if self._is_subtype(b1, b2) is True:
            return b2
        if self._is_subtype(b2, b1) is True:
            return b1

        # Busca superclasse comum mais próxima na hierarquia conhecida
        ancestors1: List[str] = []
        queue = [b1]
        seen: Set[str] = set()
        while queue:
            cur = queue.pop(0)
            cs = self._simple_base_name(cur) or ""
            if cs in seen:
                continue
            seen.add(cs)
            ancestors1.append(cs)
            supers, _ = self._direct_supertypes(cur)
            queue.extend(supers)
        queue2 = [b2]
        seen2: Set[str] = set()
        while queue2:
            cur = queue2.pop(0)
            cs = self._simple_base_name(cur) or ""
            if cs in seen2:
                continue
            seen2.add(cs)
            if cs in ancestors1 and cs != "Object":
                return cs
            supers, _ = self._direct_supertypes(cur)
            queue2.extend(supers)
        return "Object"

    def _substitute_type_vars(self, type_str: Optional[str], mapping: Dict[str, str]) -> Optional[str]:
        """Substitui parâmetros de tipo genérico (T, E, K, V, R) por seus argumentos concretos."""
        if not type_str or not mapping:
            return type_str
        clean = self._strip_leading_type_annotations(type_str)
        kind, bound = self._parse_wildcard_arg(clean)
        if kind is not None:
            if kind == "unbounded" or not bound:
                return "?"
            new_bound = self._substitute_type_vars(bound, mapping) or bound
            return f"? {kind} {new_bound}"
        s, dims = self._strip_type_dims_full(clean)
        base, args, _ = self._extract_generic_args(s)
        if not args:
            res = mapping.get(base or s, s)
            return f"{res}{'[]' * dims}" if dims else res
        new_args = [self._substitute_type_vars(a, mapping) or a for a in args]
        base_res = mapping.get(base or "", base or "")
        joined = ", ".join(new_args)
        res = f"{base_res}<{joined}>"
        return f"{res}{'[]' * dims}" if dims else res

    def _type_var_mapping_for_type(self, type_str: Optional[str]) -> Dict[str, str]:
        """Constrói mapeamento parametro_generico -> argumento para um tipo parametrizado."""
        if not type_str:
            return {}
        base, args, _ = self._extract_generic_args(type_str)
        if not base or not args:
            return {}
        param_names = [pname for pname, _ in self._type_param_decls_for_type(base)]
        return {pname: arg for pname, arg in zip(param_names, args)}

    def _check_lambda_capture_boundaries(self):
        """Valida ao sair de método/construtor/inicializador se variáveis capturadas foram reatribuídas (JLS §15.27.2)."""
        reported: Set[int] = set()
        for var_name, var_info, cap_line in self._pending_lambda_captures:
            info_id = id(var_info)
            if info_id in reported:
                continue
            if var_info.get("reassigned", False):
                reported.add(info_id)
                self.errors.append(
                    SemanticError(
                        f"Variável local ou parâmetro '{var_name}' capturado em expressão lambda deve ser 'final' ou efetivamente final (JLS §15.27.2).",
                        cap_line,
                    )
                )
        self._pending_lambda_captures = []

    def _collect_type_fields(self, type_str: str) -> Tuple[Dict[str, Dict[str, Any]], bool]:
        """Coleta campos declarados e herdados de um tipo junto com flag de hierarquia fechada."""
        fields: Dict[str, Dict[str, Any]] = {}
        visited: Set[str] = set()
        eff_root = self._capture_convert(type_str) or type_str
        root_base = self._strip_generics(eff_root) or eff_root
        root_internal = self._lookup_internal_type_key(root_base)
        root_ext_init = self._resolve_external_type(eff_root) if root_internal is None else None
        root_key = root_internal or (root_ext_init.fqn if root_ext_init is not None else (self._simple_base_name(eff_root) or ""))
        root_pkg = self._inheritance_analyzer.get_type_package(root_key)
        queue: List[str] = [eff_root]
        fully_known = True

        while queue:
            cur = queue.pop(0)
            cur_base = self._strip_generics(cur) or cur
            cur_simple = self._simple_base_name(cur) or ""
            cur_internal = self._lookup_internal_type_key(cur_base)
            cur_ext = self._resolve_external_type(cur_base) if cur_internal is None else None
            cur_key = cur_internal or (cur_ext.fqn if cur_ext is not None else cur_simple)
            if not cur_key or cur_key in visited or cur_simple.endswith("[]"):
                continue
            visited.add(cur_key)
            if self._is_capture_var(cur_simple):
                cap = self._capture_vars.get(cur_simple, {})
                for ub in (cap.get("upper_bounds") or ["Object"]):
                    queue.append(self._capture_convert(ub) or ub)
                continue
            tp_bounds = self._lookup_type_param_bounds(cur_simple)
            if tp_bounds is not None:
                for ub in (tp_bounds or ["Object"]):
                    queue.append(self._capture_convert(ub) or ub)
                continue
            tvar_map = self._type_var_mapping_for_type(cur)

            if cur_ext is not None:
                is_inherited_ext = (cur_key != root_key and cur_simple != self._simple_base_name(eff_root))
                for fname, ef in cur_ext.fields.items():
                    if is_inherited_ext and ef.access == "private":
                        continue
                    fields.setdefault(fname, self._ext_field_to_dict(ef, cur_ext, tvar_map))

            if cur_simple in self.BUILTIN_FIELDS and (cur_ext is None or self._is_partial_external_stdlib(cur_ext)):
                for fname, (ftype, is_st, is_fin) in self.BUILTIN_FIELDS[cur_simple].items():
                    fields.setdefault(
                        fname,
                        {
                            "type": self._substitute_type_vars(ftype, tvar_map),
                            "is_static": is_st,
                            "is_final": is_fin,
                            "category": "campo",
                            "owner": cur_simple,
                            "owner_key": cur_simple,
                            "access": "public",
                        },
                    )

            tdecl = self._lookup_type_decl(cur_key)
            if tdecl is not None:
                tkind, tnode = tdecl
                cur_pkg = self._inheritance_analyzer.get_type_package(cur_key)
                is_inherited_owner = (cur_key != root_key)
                if tkind == "enum":
                    for const in getattr(tnode, "constants", []):
                        if getattr(const, "name", None):
                            fields.setdefault(
                                const.name,
                                {
                                    "type": cur_simple,
                                    "is_static": True,
                                    "is_final": True,
                                    "category": "constante_enum",
                                    "owner": cur_simple,
                                    "owner_key": cur_key,
                                    "access": "public",
                                },
                            )
                elif tkind == "record":
                    for comp in getattr(tnode, "components", []):
                        if getattr(comp, "name", None):
                            ctype = self._substitute_type_vars(comp.effective_type, tvar_map)
                            fields.setdefault(
                                comp.name,
                                {
                                    "type": ctype,
                                    "is_static": False,
                                    "is_final": True,
                                    "category": "componente_record",
                                    "owner": cur_simple,
                                    "owner_key": cur_key,
                                    "access": "public",
                                },
                            )
                for member in getattr(tnode, "members", []):
                    if isinstance(member, FieldDeclaration):
                        is_ifc_const = (tkind == "interface")
                        is_st = True if is_ifc_const else ("static" in getattr(member, "modifiers", []))
                        is_fin = True if is_ifc_const else ("final" in getattr(member, "modifiers", []))
                        f_access = self._inheritance_analyzer.effective_access(
                            getattr(member, "modifiers", []),
                            owner_kind=tkind,
                            member_kind="campo",
                        )
                        if is_inherited_owner:
                            if f_access == "private":
                                continue
                            if f_access == "package" and cur_pkg != root_pkg:
                                continue
                        cat = "constante_interface" if is_ifc_const else "campo"
                        decls = getattr(member, "declarators", None) or []
                        if decls:
                            for d in decls:
                                if getattr(d, "name", None) and d.name != "_":
                                    ftype = self._substitute_type_vars(d.effective_type, tvar_map)
                                    fields.setdefault(
                                        d.name,
                                        {
                                            "type": ftype,
                                            "is_static": is_st,
                                            "is_final": is_fin,
                                            "category": cat,
                                            "owner": cur_simple,
                                            "owner_key": cur_key,
                                            "access": f_access,
                                        },
                                    )
                        elif getattr(member, "name", None) and member.name != "_":
                            raw_t = getattr(member, "effective_type", None) or self._normalize_type_str(getattr(member, "type_ref", None)) or "Object"
                            ftype = self._substitute_type_vars(raw_t, tvar_map)
                            fields.setdefault(
                                member.name,
                                {
                                    "type": ftype,
                                    "is_static": is_st,
                                    "is_final": is_fin,
                                    "category": cat,
                                    "owner": cur_simple,
                                    "owner_key": cur_key,
                                    "access": f_access,
                                },
                            )
            elif cur_ext is not None:
                pass
            elif cur_simple not in self.BUILTIN_TYPE_SUPERTYPES and cur_simple not in self.KNOWN_EXCEPTION_PARENTS:
                fully_known = False

            supers, is_ext = self._direct_supertypes(cur)
            if is_ext:
                fully_known = False
            for s in supers:
                sub_s = self._substitute_type_vars(s, tvar_map) or s
                queue.append(sub_s)

        return fields, fully_known

    def _extract_method_sig(
        self,
        member: MethodDeclaration,
        owner_name: str,
        tvar_map: Optional[Dict[str, str]] = None,
        owner_kind: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extrai assinatura normalizada de um nó MethodDeclaration."""
        params: List[str] = []
        is_varargs = False
        raw_params = list(getattr(member, "parameters", []) or [])
        for idx, p in enumerate(raw_params):
            p_is_va = bool(getattr(p, "is_varargs", False))
            raw_t = getattr(p, "effective_type", None)
            if not raw_t and getattr(p, "type_ref", None) is not None:
                raw_t = self._normalize_type_str(p.type_ref)
            raw_t = raw_t or "Object"
            if p_is_va and idx == len(raw_params) - 1:
                is_varargs = True
                if raw_t.endswith("..."):
                    raw_t = raw_t[:-3]
                elif raw_t.endswith("[]"):
                    raw_t = raw_t[:-2]
            if tvar_map:
                raw_t = self._substitute_type_vars(raw_t, tvar_map) or raw_t
            params.append(raw_t)

        ret_t = getattr(member, "effective_return_type", None) or self._normalize_type_str(getattr(member, "return_type", None)) or "void"
        if tvar_map:
            ret_t = self._substitute_type_vars(ret_t, tvar_map) or ret_t
        tparams = []
        tparam_bounds: Dict[str, List[str]] = {}
        for tp in (getattr(member, "type_parameters", []) or []):
            tp_name = getattr(tp, "name", "")
            if not tp_name:
                continue
            tparams.append(tp_name)
            raw_b = [self._normalize_type_str(b) for b in (getattr(tp, "bounds", []) or [])]
            tparam_bounds[tp_name] = [b for b in raw_b if b] or ["Object"]
        throws_list: List[str] = []
        for tt in (getattr(member, "throws_types", []) or []):
            tn = self._normalize_type_str(tt)
            if tn:
                if tvar_map:
                    tn = self._substitute_type_vars(tn, tvar_map) or tn
                throws_list.append(tn)
        mods = list(getattr(member, "modifiers", []) or [])
        eff_okind = owner_kind
        if not eff_okind:
            tdecl = self._lookup_type_decl(owner_name)
            if tdecl is not None:
                eff_okind = tdecl[0]
            elif isinstance(member, InterfaceMethodDeclaration) or "default" in mods:
                eff_okind = "interface"
            else:
                eff_okind = "class"
        m_kind = "construtor" if isinstance(member, (ConstructorDeclaration, CompactConstructorDeclaration, NormalCanonicalConstructor)) else "metodo"
        is_iface_abstract = (eff_okind == "interface") and not any(m in mods for m in ("default", "static", "private"))
        owner_key = self._inheritance_analyzer.resolve_type_key(owner_name) or owner_name
        return {
            "name": getattr(member, "name", ""),
            "params": params,
            "ret": ret_t,
            "static": "static" in mods,
            "varargs": is_varargs,
            "tparams": tparams,
            "tparam_bounds": tparam_bounds,
            "throws": throws_list,
            "owner": self._simple_base_name(owner_name) or owner_name,
            "owner_key": owner_key,
            "owner_kind": eff_okind,
            "access": self._inheritance_analyzer.effective_access(mods, owner_kind=eff_okind, member_kind=m_kind),
            "is_abstract": ("abstract" in mods) or is_iface_abstract,
            "is_final": "final" in mods,
            "is_default": "default" in mods,
            "node": member,
        }

    def _collect_type_methods(self, type_str: str, method_name: str) -> Tuple[List[Dict[str, Any]], bool, bool]:
        """Coleta assinaturas de método no tipo e em sua hierarquia."""
        methods: List[Dict[str, Any]] = []
        seen_sigs: Set[Tuple[Any, ...]] = set()
        seen_raw_sigs: Set[Tuple[Any, ...]] = set()
        visited: Set[str] = set()
        eff_root = self._capture_convert(type_str) or type_str
        root_base = self._strip_generics(eff_root) or eff_root
        root_simple = self._simple_base_name(eff_root) or ""
        root_key = self._inheritance_analyzer.resolve_type_key(root_base) or root_simple
        root_ext = self._resolve_external_type(eff_root) if self._lookup_type_decl(root_key) is None else None
        is_declared = False
        root_is_var = self._is_capture_var(root_simple) or (self._lookup_type_param_bounds(root_simple) is not None)
        if root_ext is not None:
            root_key = root_ext.fqn
            is_declared = True
        queue: List[str] = [eff_root]
        fully_known = True
        if self._lookup_type_decl(root_key) is not None:
            is_declared = True

        # Arrays herdam apenas métodos de Object (e clone)
        _, root_dims = self._strip_type_dims_full(eff_root)
        if root_dims > 0:
            queue = ["Object"]

        while queue:
            cur = queue.pop(0)
            cur_base = self._strip_generics(cur) or cur
            cur_simple = self._simple_base_name(cur) or ""
            cur_internal = self._lookup_internal_type_key(cur_base)
            cur_ext = self._resolve_external_type(cur_base) if cur_internal is None else None
            cur_key = cur_internal or (cur_ext.fqn if cur_ext is not None else cur_simple)
            if not cur_key or cur_key in visited:
                continue
            visited.add(cur_key)
            if self._is_capture_var(cur_simple):
                cap = self._capture_vars.get(cur_simple, {})
                for ub in (cap.get("upper_bounds") or ["Object"]):
                    queue.append(self._capture_convert(ub) or ub)
                continue
            tp_bounds = self._lookup_type_param_bounds(cur_simple)
            if tp_bounds is not None:
                for ub in (tp_bounds or ["Object"]):
                    queue.append(self._capture_convert(ub) or ub)
                continue
            tvar_map = self._type_var_mapping_for_type(cur)

            tdecl = self._lookup_type_decl(cur_key)
            if tdecl is not None:
                if root_is_var:
                    is_declared = True
                tkind, tnode = tdecl
                is_inherited_owner = (cur_key != root_key)
                if tkind == "record":
                    for comp in getattr(tnode, "components", []):
                        if comp.name == method_name:
                            ret = self._substitute_type_vars(comp.effective_type.replace("...", "[]"), tvar_map)
                            key = ((), False)
                            if key not in seen_sigs:
                                seen_sigs.add(key)
                                methods.append({
                                    "name": method_name,
                                    "params": [],
                                    "ret": ret,
                                    "static": False,
                                    "varargs": False,
                                    "tparams": [],
                                    "throws": [],
                                    "owner": cur_simple,
                                    "owner_key": cur_key,
                                    "owner_kind": "record",
                                    "access": "public",
                                    "is_final": False,
                                    "is_default": False,
                                })
                elif tkind == "enum":
                    if method_name == "values":
                        key = ((), False)
                        if key not in seen_sigs:
                            seen_sigs.add(key)
                            methods.append({
                                "name": "values",
                                "params": [],
                                "ret": f"{cur_simple}[]",
                                "static": True,
                                "varargs": False,
                                "tparams": [],
                                "throws": [],
                                "owner": cur_simple,
                                "owner_key": cur_key,
                                "owner_kind": "enum",
                                "access": "public",
                                "is_final": False,
                                "is_default": False,
                            })
                    elif method_name == "valueOf":
                        key = (("String",), False)
                        if key not in seen_sigs:
                            seen_sigs.add(key)
                            methods.append({
                                "name": "valueOf",
                                "params": ["String"],
                                "ret": cur_simple,
                                "static": True,
                                "varargs": False,
                                "tparams": [],
                                "throws": [],
                                "owner": cur_simple,
                                "owner_key": cur_key,
                                "owner_kind": "enum",
                                "access": "public",
                                "is_final": False,
                                "is_default": False,
                            })

                for member in getattr(tnode, "members", []):
                    if isinstance(member, (MethodDeclaration, InterfaceMethodDeclaration)) and member.name == method_name:
                        sig = self._extract_method_sig(member, cur_simple, tvar_map, owner_kind=tkind)
                        sig["owner_key"] = cur_key
                        if is_inherited_owner:
                            if sig.get("access") == "private":
                                continue
                            if tkind == "interface" and sig.get("static"):
                                continue
                        key = self._sig_dedup_key(sig["params"], sig["varargs"], sig)
                        if key not in seen_sigs:
                            seen_sigs.add(key)
                            seen_raw_sigs.add(self._sig_dedup_key(sig["params"], sig["varargs"]))
                            methods.append(sig)
            else:
                if cur_ext is not None:
                    is_inherited_ext = (cur_key != root_key)
                    for minfo in cur_ext.methods.get(method_name, []):
                        if is_inherited_ext and minfo.access == "private":
                            continue
                        if is_inherited_ext and cur_ext.kind == "interface" and minfo.static:
                            continue
                        msig = self._ext_method_to_sig(minfo, cur_ext, tvar_map)
                        key = self._sig_dedup_key(msig["params"], msig["varargs"], msig)
                        if key not in seen_sigs:
                            seen_sigs.add(key)
                            seen_raw_sigs.add(self._sig_dedup_key(msig["params"], msig["varargs"]))
                            methods.append(msig)
                if cur_simple in self.BUILTIN_METHODS and (cur_ext is None or self._is_partial_external_stdlib(cur_ext)):
                    for bsig in self.BUILTIN_METHODS[cur_simple].get(method_name, []):
                        bparams = []
                        for bp in bsig["params"]:
                            clean_p = bp[:-3] if bp.endswith("...") else bp
                            bparams.append(self._substitute_type_vars(clean_p, tvar_map) or clean_p)
                        bret = self._substitute_type_vars(bsig["ret"], tvar_map) or bsig["ret"]
                        bthrows = [self._substitute_type_vars(bt, tvar_map) or bt for bt in bsig.get("throws", [])]
                        if (cur_simple != root_simple) and cur_simple in self.BUILTIN_INTERFACE_TYPES and bsig.get("static"):
                            continue
                        key = self._sig_dedup_key(bparams, bsig["varargs"])
                        if key not in seen_raw_sigs and key not in seen_sigs:
                            seen_raw_sigs.add(key)
                            seen_sigs.add(key)
                            methods.append({
                                "name": method_name,
                                "params": bparams,
                                "ret": bret,
                                "static": bsig["static"],
                                "varargs": bsig["varargs"],
                                "tparams": list(bsig.get("tparams", [])),
                                "throws": bthrows,
                                "owner": cur_simple,
                                "owner_key": cur_simple,
                                "owner_kind": "interface" if cur_simple in self.BUILTIN_INTERFACE_TYPES else "class",
                                "access": bsig.get("access", "public"),
                                "is_final": bool(bsig.get("is_final", False)),
                                "is_default": bool(bsig.get("is_default", False)),
                            })
                elif cur_ext is None and cur_simple not in self.BUILTIN_TYPE_SUPERTYPES and cur_simple not in self.KNOWN_EXCEPTION_PARENTS:
                    fully_known = False

            supers, is_ext = self._direct_supertypes(cur)
            if is_ext:
                fully_known = False
            for s in supers:
                sub_s = self._substitute_type_vars(s, tvar_map) or s
                queue.append(sub_s)

        return methods, fully_known, is_declared

    def _collect_type_constructors(self, type_str: str) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
        """Coleta assinaturas de construtor de uma classe/record ou tipo embutido."""
        base = self._strip_generics(type_str) or type_str
        simple = self._simple_base_name(type_str) or ""
        resolved_key = self._inheritance_analyzer.resolve_type_key(base) or simple
        tvar_map = self._type_var_mapping_for_type(type_str)
        ctors: List[Dict[str, Any]] = []
        tdecl = self._lookup_type_decl(resolved_key)
        if tdecl is not None:
            tkind, tnode = tdecl
            if tkind == "enum":
                return [], True, "enum"
            declared_ctors = [
                m for m in getattr(tnode, "members", [])
                if isinstance(m, (ConstructorDeclaration, CompactConstructorDeclaration, NormalCanonicalConstructor))
            ]
            if declared_ctors:
                for cm in declared_ctors:
                    c_acc = self._inheritance_analyzer.effective_access(
                        getattr(cm, "modifiers", []),
                        owner_kind=tkind,
                        member_kind="construtor",
                    )
                    if isinstance(cm, CompactConstructorDeclaration):
                        cparams = [
                            self._substitute_type_vars(c.effective_type.replace("...", "[]"), tvar_map) or c.effective_type
                            for c in getattr(tnode, "components", [])
                        ]
                        ctors.append({
                            "params": cparams,
                            "ret": type_str,
                            "static": False,
                            "varargs": False,
                            "tparams": [],
                            "throws": [],
                            "owner": simple,
                            "owner_key": resolved_key,
                            "access": c_acc,
                        })
                    else:
                        sig = self._extract_method_sig(cm, simple, tvar_map, owner_kind=tkind)
                        sig["ret"] = type_str
                        sig["owner_key"] = resolved_key
                        sig["access"] = c_acc
                        ctors.append(sig)
            has_explicit_canonical = any(
                isinstance(cm, (CompactConstructorDeclaration, NormalCanonicalConstructor))
                for cm in declared_ctors
            )
            if tkind == "record" and not has_explicit_canonical:
                cparams = [
                    self._substitute_type_vars(c.effective_type.replace("...", "[]"), tvar_map) or c.effective_type
                    for c in getattr(tnode, "components", [])
                ]
                rec_def_acc = self._inheritance_analyzer.effective_access(
                    getattr(tnode, "modifiers", []),
                    owner_kind="class",
                    member_kind="construtor",
                )
                ctors.append({
                    "params": cparams,
                    "ret": type_str,
                    "static": False,
                    "varargs": False,
                    "tparams": [],
                    "throws": [],
                    "owner": simple,
                    "owner_key": resolved_key,
                    "access": rec_def_acc,
                })
            elif not declared_ctors:
                if tkind == "interface":
                    return [], True, "interface"
                elif tkind != "record":
                    # Classe sem construtores explícitos possui construtor padrão com mesma visibilidade da classe (JLS §8.8.9)
                    cls_def_acc = self._inheritance_analyzer.effective_access(
                        getattr(tnode, "modifiers", []),
                        owner_kind="class",
                        member_kind="construtor",
                    )
                    ctors.append({
                        "params": [],
                        "ret": type_str,
                        "static": False,
                        "varargs": False,
                        "tparams": [],
                        "throws": [],
                        "owner": simple,
                        "owner_key": resolved_key,
                        "access": cls_def_acc,
                    })
            return ctors, True, tkind

        ext = self._resolve_external_type(base)
        if ext is not None:
            if ext.kind == "enum":
                return [], True, "enum"
            if ext.kind in ("interface", "annotation_interface"):
                return [], True, ext.kind
            seen_ctors: Set[Tuple[Tuple[str, ...], bool]] = set()
            for mc in ext.constructors:
                csig = self._ext_method_to_sig(mc, ext, tvar_map)
                csig["ret"] = type_str
                ckey = (tuple(csig["params"]), csig["varargs"])
                if ckey not in seen_ctors:
                    seen_ctors.add(ckey)
                    ctors.append(csig)
            if self._is_partial_external_stdlib(ext) and simple in self.BUILTIN_CONSTRUCTORS:
                for entry in self.BUILTIN_CONSTRUCTORS[simple]:
                    if isinstance(entry, dict):
                        plist = list(entry.get("params", []))
                        tlist = list(entry.get("throws", []))
                        is_va = bool(entry.get("varargs", False))
                        c_acc = entry.get("access", "public")
                    else:
                        plist = list(entry)
                        tlist = []
                        is_va = False
                        c_acc = "public"
                    ckey = (tuple(plist), is_va)
                    if ckey not in seen_ctors:
                        seen_ctors.add(ckey)
                        ctors.append({
                            "params": plist,
                            "ret": type_str,
                            "static": False,
                            "varargs": is_va,
                            "tparams": [],
                            "throws": tlist,
                            "owner": ext.simple_name,
                            "owner_key": ext.fqn,
                            "access": c_acc,
                        })
            return ctors, True, ext.kind

        if simple in self.BUILTIN_CONSTRUCTORS:
            for entry in self.BUILTIN_CONSTRUCTORS[simple]:
                if isinstance(entry, dict):
                    plist = list(entry.get("params", []))
                    tlist = list(entry.get("throws", []))
                    is_va = bool(entry.get("varargs", False))
                    c_acc = entry.get("access", "public")
                else:
                    plist = list(entry)
                    tlist = []
                    is_va = False
                    c_acc = "public"
                ctors.append({
                    "params": plist,
                    "ret": type_str,
                    "static": False,
                    "varargs": is_va,
                    "tparams": [],
                    "throws": tlist,
                    "owner": simple,
                    "owner_key": simple,
                    "access": c_acc,
                })
            return ctors, True, "class"
        if simple in self.BUILTIN_INTERFACE_TYPES:
            return [], True, "interface"
        if simple in self.KNOWN_EXCEPTION_PARENTS or simple in self.BUILTIN_CLASS_TYPES:
            ctors.append({"params": [], "ret": type_str, "static": False, "varargs": False, "tparams": [], "throws": [], "owner": simple})
            ctors.append({"params": ["String"], "ret": type_str, "static": False, "varargs": False, "tparams": [], "throws": [], "owner": simple})
            return ctors, True, "class"
        return [], False, None

    def _check_functional_interface_annotation(self, type_node: ASTNode, is_interface: bool = False) -> None:
        """Valida uso de @FunctionalInterface segundo JLS §9.6.4.9."""
        annos = getattr(type_node, "annotations", []) or []
        has_fi = any(
            isinstance(a, Annotation) and a.name.split(".")[-1] == "FunctionalInterface"
            for a in annos
        )
        if not has_fi:
            return
        name = getattr(type_node, "name", "<tipo>")
        line = getattr(type_node, "line", 1)
        if not is_interface:
            self.errors.append(
                SemanticError(
                    f"'{name}' não é uma interface; @FunctionalInterface só pode anotar interfaces funcionais (JLS §9.6.4.9).",
                    line,
                )
            )
            return
        sam, _ = self._resolve_functional_interface(name)
        if sam is None:
            self.errors.append(
                SemanticError(
                    f"Interface '{name}' anotada com @FunctionalInterface não é uma interface funcional válida (JLS §9.6.4.9).",
                    line,
                )
            )

    def _is_object_public_method_sig(self, name: str, sig: Dict[str, Any]) -> bool:
        """Verifica se a assinatura corresponde a método público de java.lang.Object (JLS §9.8)."""
        params = sig.get("params", [])
        ret = sig.get("ret", "")
        ret_simple = self._simple_base_name(ret) or ret
        if name == "toString" and len(params) == 0 and ret_simple == "String":
            return True
        if name == "hashCode" and len(params) == 0 and ret_simple == "int":
            return True
        if name == "equals" and len(params) == 1 and ret_simple == "boolean":
            p0 = self._simple_base_name(params[0]) or params[0]
            if p0 == "Object":
                return True
        return False

    def _resolve_functional_interface_full(self, target_type: Optional[str]) -> Tuple[Optional[Tuple[List[str], str, List[str]]], bool]:
        """Resolve a assinatura completa (parâmetros, retorno, throws) do SAM de uma interface funcional."""
        if not target_type:
            return None, False
        clean = self._strip_leading_type_annotations(target_type)
        clean = self._capture_convert(clean) or clean
        simple = self._simple_base_name(clean)
        if not simple or simple.endswith("[]") or simple in self.PRIMITIVE_TYPES:
            return None, False

        tvar_map = self._type_var_mapping_for_type(clean)
        if simple in self.BUILTIN_FUNCTIONAL_INTERFACES:
            raw_params, raw_ret, tparams = self.BUILTIN_FUNCTIONAL_INTERFACES[simple]
            # Se target foi raw type (ex: Function sem <T,R>), substitui type vars por Object
            eff_map = dict(tvar_map)
            for tp in tparams:
                eff_map.setdefault(tp, "Object")
            resolved_params = [self._substitute_type_vars(p, eff_map) or p for p in raw_params]
            resolved_ret = self._substitute_type_vars(raw_ret, eff_map) or raw_ret
            builtin_throws = ["Exception"] if simple == "Callable" else []
            return (resolved_params, resolved_ret, builtin_throws), True

        tdecl = self._lookup_type_decl(simple)
        if tdecl is not None:
            tkind, tnode = tdecl
            if tkind != "interface":
                return None, True
            eff_map = dict(tvar_map)
            for tp in (getattr(tnode, "type_parameters", []) or []):
                tp_name = getattr(tp, "name", None)
                if tp_name:
                    eff_map.setdefault(tp_name, "Object")
            abstract_methods: List[Dict[str, Any]] = []
            concrete_default_keys: Set[Tuple[str, Tuple[str, ...]]] = set()
            seen_abstract_sigs: Set[Tuple[str, Tuple[str, ...], str]] = set()
            # Verifica métodos abstratos declarados na interface e herdadas
            visited: Set[str] = set()
            queue: List[str] = [clean]
            while queue:
                cur = queue.pop(0)
                cs = self._simple_base_name(cur) or ""
                if not cs or cs in visited:
                    continue
                visited.add(cs)
                cdecl = self._lookup_type_decl(cs)
                cmap = self._type_var_mapping_for_type(cur)
                if cdecl is not None and cdecl[0] == "interface":
                    for tp in (getattr(cdecl[1], "type_parameters", []) or []):
                        tp_name = getattr(tp, "name", None)
                        if tp_name:
                            cmap.setdefault(tp_name, eff_map.get(tp_name, "Object"))
                    for member in getattr(cdecl[1], "members", []):
                        if isinstance(member, MethodDeclaration):
                            mods = getattr(member, "modifiers", [])
                            if "static" in mods or "private" in mods:
                                continue
                            sig = self._extract_method_sig(member, cs, cmap)
                            if "default" in mods:
                                concrete_default_keys.add((member.name, tuple(sig["params"])))
                                continue
                            # Métodos públicos de Object não contam como SAM (JLS §9.8)
                            if self._is_object_public_method_sig(member.name, sig):
                                continue
                            if member.body is None or "abstract" in mods:
                                key = (member.name, tuple(sig["params"]))
                                if key in concrete_default_keys:
                                    continue
                                full_key = (member.name, tuple(sig["params"]), sig["ret"])
                                if full_key not in seen_abstract_sigs:
                                    seen_abstract_sigs.add(full_key)
                                    abstract_methods.append(sig)
                    for ext in getattr(cdecl[1], "extends_types", []):
                        queue.append(self._substitute_type_vars(self._normalize_type_str(ext), cmap) or "")
            if len(abstract_methods) == 1:
                sam = abstract_methods[0]
                return (sam["params"], sam["ret"], list(sam.get("throws", []))), True
            return None, True

        ext = self._resolve_external_type(clean)
        if ext is not None:
            if ext.kind != "interface":
                return None, True
            eff_map = dict(tvar_map)
            for tp_name, _ in ext.type_parameters:
                eff_map.setdefault(tp_name, "Object")
            abstract_methods: List[Dict[str, Any]] = []
            concrete_default_keys: Set[Tuple[str, Tuple[str, ...]]] = set()
            seen_abstract_sigs: Set[Tuple[str, Tuple[str, ...], str]] = set()
            visited_ext: Set[str] = set()
            queue_ext: List[str] = [clean]
            while queue_ext:
                cur_q = queue_ext.pop(0)
                cur_b = self._strip_generics(cur_q) or cur_q
                cext = self._resolve_external_type(cur_b)
                if cext is None or cext.kind != "interface":
                    continue
                if cext.fqn in visited_ext:
                    continue
                visited_ext.add(cext.fqn)
                cmap = self._type_var_mapping_for_type(cur_q)
                for tp_name, _ in cext.type_parameters:
                    cmap.setdefault(tp_name, eff_map.get(tp_name, "Object"))
                for mname, mlist in cext.methods.items():
                    for minfo in mlist:
                        if minfo.static or minfo.access == "private":
                            continue
                        sig = self._ext_method_to_sig(minfo, cext, cmap)
                        if minfo.is_default:
                            concrete_default_keys.add((mname, tuple(sig["params"])))
                            continue
                        if self._is_object_public_method_sig(mname, sig):
                            continue
                        if minfo.is_abstract:
                            key = (mname, tuple(sig["params"]))
                            if key in concrete_default_keys:
                                continue
                            full_key = (mname, tuple(sig["params"]), sig["ret"])
                            if full_key not in seen_abstract_sigs:
                                seen_abstract_sigs.add(full_key)
                                abstract_methods.append(sig)
                for ifc in cext.interfaces:
                    fmt_i = self._format_ext_type(ifc) or ifc
                    queue_ext.append(self._substitute_type_vars(fmt_i, cmap) or fmt_i)
            if len(abstract_methods) == 1:
                sam = abstract_methods[0]
                return (sam["params"], sam["ret"], list(sam.get("throws", []))), True
            return None, True

        return None, False

    def _resolve_functional_interface(self, target_type: Optional[str]) -> Tuple[Optional[Tuple[List[str], str]], bool]:
        """Resolve a assinatura do método abstrato único (SAM) de uma interface funcional."""
        sam_full, is_known = self._resolve_functional_interface_full(target_type)
        if sam_full is None:
            return None, is_known
        return (sam_full[0], sam_full[1]), is_known

    def _is_poly_compatible_with_param(self, expr: ASTNode, param_type: str) -> bool:
        """Verifica rapidamente compatibilidade estrutural de poly expression com interface funcional."""
        sam, is_known = self._resolve_functional_interface(param_type)
        if sam is None:
            return not is_known and self._simple_base_name(param_type) not in self.PRIMITIVE_TYPES
        sam_params, _ = sam
        if isinstance(expr, LambdaExpression):
            return len(expr.parameters) == len(sam_params)
        if isinstance(expr, MethodReference):
            return True
        if isinstance(expr, ConditionalExpression):
            return self._is_poly_compatible_with_param(expr.then_expr, param_type) and self._is_poly_compatible_with_param(expr.else_expr, param_type)
        return True

    def _is_definitely_incompatible(self, param_type: str, arg_node: Optional[ASTNode], arg_type: Optional[str]) -> bool:
        """Verifica se um argumento é comprovadamente incompatível com um tipo de parâmetro formal."""
        if not param_type or param_type in ("var", "desconhecido"):
            return False
        p_clean = self._strip_leading_type_annotations(param_type) or param_type
        p_base, p_dims = self._strip_type_dims_full(p_clean)
        p_is_prim = (p_dims == 0) and (p_base in self.PRIMITIVE_TYPES)

        if p_is_prim:
            if isinstance(arg_node, (ObjectCreationExpression, ArrayCreationExpression, ArrayInitializer, LambdaExpression)):
                return True
            if arg_type:
                a_clean = self._strip_leading_type_annotations(arg_type) or arg_type
                a_base, a_dims = self._strip_type_dims_full(a_clean)
                if a_dims > 0:
                    return True
                if a_base not in self.PRIMITIVE_TYPES and a_base not in self.WRAPPER_TO_PRIMITIVE:
                    return True
            return False

        if p_dims > 0:
            if isinstance(arg_node, Literal):
                kind = getattr(arg_node, "kind", "")
                if kind in ("NUM", "INT", "LONG", "DOUBLE", "FLOAT", "CHAR", "BOOLEAN", "STRING"):
                    if kind != "STRING" or p_dims > 1 or p_base != "String":
                        return True
            if arg_type:
                a_clean = self._strip_leading_type_annotations(arg_type) or arg_type
                a_base, a_dims = self._strip_type_dims_full(a_clean)
                if a_dims == 0 and a_clean != "null":
                    return True
                if a_dims > 0:
                    p_prim = p_base in self.PRIMITIVE_TYPES
                    a_prim = a_base in self.PRIMITIVE_TYPES
                    if p_prim != a_prim:
                        return True
                    if p_prim and a_prim and p_base != a_base:
                        return True
            return False

        if arg_type:
            a_clean = self._strip_leading_type_annotations(arg_type) or arg_type
            a_base, a_dims = self._strip_type_dims_full(a_clean)
            if a_dims > 0:
                if p_base not in ("Object", "Cloneable", "Serializable") and not self._is_type_variable(p_base):
                    return True
        return False

    def _is_deferred_poly_call_arg(self, node: Optional[ASTNode]) -> bool:
        """Indica se um argumento de chamada depende do tipo de parâmetro alvo (poly expression)."""
        if isinstance(node, (LambdaExpression, MethodReference)):
            return True
        if isinstance(node, ObjectCreationExpression) and getattr(node, "is_diamond", False):
            return True
        if isinstance(node, ConditionalExpression):
            return (
                self._is_poly_expression(node)
                or self._is_deferred_poly_call_arg(node.then_expr)
                or self._is_deferred_poly_call_arg(node.else_expr)
            )
        if isinstance(node, MethodCall) and not getattr(node, "type_arguments", None):
            recv_type = None
            if node.target is None:
                recv_type = self._current_enclosing_type()
            elif isinstance(node.target, Identifier):
                sym = self._lookup_var_symbol(node.target.name)
                if sym is not None and sym.get("category") not in self.TYPE_SYMBOL_CATEGORIES and sym.get("category") is not None:
                    recv_type = sym.get("type")
                elif self._is_known_type(node.target.name) or (node.target.name and node.target.name[0].isupper()):
                    recv_type = node.target.name
            elif isinstance(node.target, MemberAccess):
                recv_type = self._infer_member_access_receiver_type(node)
            if recv_type:
                methods, _, _ = self._collect_type_methods(recv_type, node.method_name)
                nargs = len(node.arguments)
                for ms in methods:
                    ok_arity = (
                        (len(ms["params"]) == nargs and not ms.get("varargs"))
                        or (ms.get("varargs") and nargs >= len(ms["params"]) - 1)
                    )
                    if ok_arity and ms.get("tparams"):
                        return True
        return False

    def _score_deferred_poly_arg(
        self,
        param_type: str,
        arg_expr: ASTNode,
        phase: int,
    ) -> Optional[int]:
        """Avalia especulativamente argumento poly adiado contra param_type sem efeitos colaterais."""
        if not param_type or param_type in ("var", "desconhecido"):
            return 2
        snap_flow = self._flow_snapshot()
        snap_sup = self._flow_suppress_errors
        snap_flags = self._snapshot_local_var_flags()
        snap_errs = len(self.errors)
        snap_caps = len(self._pending_lambda_captures)
        snap_unres = len(self.unresolved_checks)
        had_cache = id(arg_expr) in self._inferred_types
        prev_cache = self._inferred_types.get(id(arg_expr))
        self._flow_suppress_errors = True
        try:
            self._check_expression_with_target(arg_expr, param_type)
            if len(self.errors) > snap_errs:
                return None
            spec_t = self._inferred_types.get(id(arg_expr))
            if not spec_t:
                return 1
            return self._score_param_match(param_type, None, spec_t, phase)
        finally:
            if had_cache and prev_cache is not None:
                self._inferred_types[id(arg_expr)] = prev_cache
            else:
                self._inferred_types.pop(id(arg_expr), None)
            del self.errors[snap_errs:]
            del self._pending_lambda_captures[snap_caps:]
            del self.unresolved_checks[snap_unres:]
            self._flow_suppress_errors = snap_sup
            self._flow_restore(snap_flow)
            self._restore_local_var_flags(snap_flags)

    def _score_param_match(
        self,
        param_type: str,
        arg_expr: Optional[ASTNode],
        arg_type: Optional[str],
        phase: int,
    ) -> Optional[int]:
        """Pontua compatibilidade entre argumento e parâmetro formal na fase JLS §15.12.2 dada."""
        if isinstance(arg_expr, (LambdaExpression, MethodReference)):
            return 1 if self._is_poly_compatible_with_param(arg_expr, param_type) else None
        if arg_type is None and isinstance(arg_expr, (MethodCall, ObjectCreationExpression, ConditionalExpression)):
            return self._score_deferred_poly_arg(param_type, arg_expr, phase)

        p_clean = self._strip_leading_type_annotations(param_type) or param_type
        a_clean = (self._strip_leading_type_annotations(arg_type) or arg_type) if arg_type else None
        p_base, p_dims = self._strip_type_dims_full(p_clean)
        p_is_prim = (p_dims == 0) and (p_base in self.PRIMITIVE_TYPES)

        # Se o parâmetro é primitivo escalar, expressões de referência nunca casam
        if p_is_prim:
            if isinstance(arg_expr, (ObjectCreationExpression, ArrayCreationExpression, ArrayInitializer)):
                return None
            if arg_type:
                a_base, a_dims = self._strip_type_dims_full(a_clean)
                if a_dims > 0:
                    return None
                if a_base not in self.PRIMITIVE_TYPES and a_base not in self.WRAPPER_TO_PRIMITIVE:
                    return None

        if arg_type is None or param_type in ("var", "desconhecido") or arg_type in ("var", "desconhecido"):
            return 2

        a_base, a_dims = self._strip_type_dims_full(a_clean)
        a_is_prim = (a_dims == 0) and (a_base in self.PRIMITIVE_TYPES)

        # Verificações de compatibilidade de array (JLS §4.10.3 / §10.7)
        if p_dims > 0 or a_dims > 0:
            if a_clean == "null":
                return 1 if p_dims > 0 else None
            if p_dims > 0 and a_dims == 0:
                return None
            if p_dims == 0 and a_dims > 0:
                if p_clean in ("Object", "Cloneable", "Serializable") or self._is_type_variable(p_base):
                    return 1
                return None
            # Ambos são arrays (p_dims > 0 and a_dims > 0)
            if p_dims != a_dims:
                if p_dims < a_dims and p_base in ("Object", "Cloneable", "Serializable"):
                    return 1
                return None
            # Mesma dimensão de array
            p_prim_arr = p_base in self.PRIMITIVE_TYPES
            a_prim_arr = a_base in self.PRIMITIVE_TYPES
            if p_prim_arr != a_prim_arr:
                return None
            if p_prim_arr and a_prim_arr:
                return 0 if p_base == a_base else None
            # Ambos são arrays de tipos de referência
            if p_base == a_base:
                if p_clean == a_clean:
                    return 0
                compat = self._generic_args_compatible(a_clean, p_clean)
                return 0 if compat is not False else None
            if p_base == "Object":
                return 1
            if self._is_type_variable(p_base) or self._is_type_variable(a_base):
                return 1
            sub = self._is_subtype(a_clean, p_clean)
            if sub is True:
                return 1
            if sub is None and not self._is_known_type(p_base) and not self._is_known_type(a_base):
                return 2
            return None

        # Escalares (p_dims == 0 and a_dims == 0)
        p_simple = self._simple_base_name(p_clean) or p_clean
        a_simple = self._simple_base_name(a_clean) or a_clean

        if p_simple == a_simple:
            if p_clean == a_clean:
                return 0
            compat = self._generic_args_compatible(a_clean, p_clean)
            return 0 if compat is not False else None

        if self._is_type_variable(p_simple) or self._is_type_variable(a_simple):
            return 1

        if a_simple == "null":
            return 1 if not p_is_prim else None

        if phase == 1:
            # Fase 1 (Strict Invocation): apenas identidade, primitive widening ou subtipagem de referência
            if p_is_prim and a_is_prim:
                if p_simple in self.WIDENING_PRIMITIVE_TARGETS.get(a_simple, set()):
                    return 1
                return None
            if (not p_is_prim) and (not a_is_prim):
                sub = self._is_subtype(a_clean, p_clean)
                if sub is True:
                    return 1
                if sub is None and not self._is_known_type(p_clean) and not self._is_known_type(a_clean):
                    return 2
                return None
            return None

        # Fase 2 / 3 (Loose / Varargs): permite boxing, unboxing e boxing + widening
        if p_is_prim and a_is_prim:
            if p_simple in self.WIDENING_PRIMITIVE_TARGETS.get(a_simple, set()):
                return 1
            return None
        if p_is_prim and not a_is_prim:
            a_unboxed = self.WRAPPER_TO_PRIMITIVE.get(a_simple)
            if a_unboxed == p_simple:
                return 2
            if a_unboxed and p_simple in self.WIDENING_PRIMITIVE_TARGETS.get(a_unboxed, set()):
                return 2
            return None
        if not p_is_prim and a_is_prim:
            boxed = self.PRIMITIVE_TO_WRAPPER.get(a_simple)
            if boxed:
                if boxed == p_simple or p_simple == "Object" or self._is_subtype(boxed, p_clean) is True:
                    return 2
            return None

        sub = self._is_subtype(a_clean, p_clean)
        if sub is True:
            return 1
        if sub is None and (not self._is_known_type(p_clean) or not self._is_known_type(a_clean)):
            return 2
        return None

    def _lift_to_base_type(self, concrete: Optional[str], target_base: str) -> Optional[str]:
        """Encontra o supertipo parametrizado de concrete cuja base simples corresponde a target_base."""
        if not concrete or not target_base:
            return None
        target_simple = self._simple_base_name(target_base) or target_base
        queue: List[str] = [self._strip_leading_type_annotations(concrete)]
        visited: Set[str] = set()
        while queue:
            cur = queue.pop(0)
            cur_simple = self._simple_base_name(cur) or ""
            if not cur_simple or cur_simple in visited:
                continue
            visited.add(cur_simple)
            if cur_simple == target_simple:
                return cur
            tvar_map = self._type_var_mapping_for_type(cur)
            supers, _ = self._direct_supertypes(cur_simple)
            for sup in supers:
                sup_sub = self._substitute_type_vars(sup, tvar_map) if tvar_map else sup
                if sup_sub:
                    queue.append(sup_sub)
        return None

    def _infer_method_type_vars_full(
        self,
        sig: Dict[str, Any],
        arg_types: List[Optional[str]],
        args: Optional[List[ASTNode]] = None,
        expected_return: Optional[str] = None,
        explicit_targs: Optional[List[str]] = None,
        phase: int = 2,
    ) -> Tuple[Dict[str, str], List[str]]:
        """Infere argumentos de tipo usando o solucionador formal de restrições JLS §18."""
        tparams = list(sig.get("tparams", []) or [])
        if not tparams:
            return {}, []
        arg_nodes = list(args) if args is not None else [None] * len(arg_types)
        res = self._type_inference.solve_invocation(
            sig,
            arg_nodes,
            arg_types,
            expected_return=expected_return,
            explicit_targs=explicit_targs,
            phase=phase,
        )
        return res.mapping, res.errors

    def _infer_method_type_vars(
        self,
        sig: Dict[str, Any],
        arg_types: List[Optional[str]],
        expected_return: Optional[str] = None,
        explicit_targs: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Infere mapa de argumentos de tipo para métodos genéricos e diamond operator."""
        mapping, _ = self._infer_method_type_vars_full(
            sig,
            arg_types,
            expected_return=expected_return,
            explicit_targs=explicit_targs,
            phase=2,
        )
        return mapping

    def _is_sig_more_specific(self, s1: Dict[str, Any], s2: Dict[str, Any]) -> bool:
        """Determina se assinatura s1 é estritamente mais específica que s2 (JLS §15.12.2.5)."""
        p1 = s1["params"]
        p2 = s2["params"]
        if len(p1) != len(p2):
            return False
        better_in_at_least_one = False
        for t1, t2 in zip(p1, p2):
            if t1 == t2:
                continue
            if t1 in self.PRIMITIVE_TYPES and t2 in self.PRIMITIVE_TYPES:
                if t2 in self.WIDENING_PRIMITIVE_TARGETS.get(t1, set()):
                    better_in_at_least_one = True
                    continue
                return False
            if t1 not in self.PRIMITIVE_TYPES and t2 not in self.PRIMITIVE_TYPES:
                if self._is_subtype(t1, t2) is True:
                    better_in_at_least_one = True
                    continue
                if s2.get("tparams"):
                    # JLS §18.5.4: trata tparams de s1 como tipos rígidos e verifica se t1 <: t2[s2.tparams]
                    if any(tp in t2 for tp in s2["tparams"]):
                        s2_probe = {"params": [t2], "ret": "void", "tparams": list(s2["tparams"]), "tparam_bounds": dict(s2.get("tparam_bounds", {}) or {}), "varargs": False}
                        res_spec = self._type_inference.solve_invocation(s2_probe, [None], [t1], phase=2)
                        if res_spec.success:
                            t2_sub = self._substitute_type_vars(t2, res_spec.mapping) or t2
                            if self._is_subtype(t1, t2_sub) is True:
                                better_in_at_least_one = True
                                continue
                if t2 == "Object" and t1 != "Object":
                    better_in_at_least_one = True
                    continue
                if not self._is_type_variable(t1) and self._is_type_variable(t2):
                    better_in_at_least_one = True
                    continue
                return False
            return False
        return better_in_at_least_one

    def _resolve_overload(
        self,
        candidates: List[Dict[str, Any]],
        args: List[ASTNode],
        line: int,
        call_desc: str,
        expected_return: Optional[str] = None,
        explicit_targs: Optional[List[str]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, str]]]:
        """Executa resolução de sobrecarga em 3 fases (JLS §15.12.2): estrita, boxing e varargs."""
        if not candidates:
            return None, None, None

        # Pré-infere tipos de argumentos não-poly para pontuação inicial
        arg_types: List[Optional[str]] = []
        for a in args:
            if self._is_deferred_poly_call_arg(a):
                arg_types.append(None)
            else:
                arg_types.append(self.infer_type(a))

        nargs = len(args)
        inference_failures: List[str] = []

        def match_candidate(sig: Dict[str, Any], phase: int) -> Optional[Tuple[int, Dict[str, str]]]:
            is_va = sig.get("varargs", False)
            raw_params = sig["params"]
            if phase < 3:
                if len(raw_params) != nargs:
                    return None
            else:
                if not is_va or nargs < len(raw_params) - 1:
                    return None
            if sig.get("tparams") or explicit_targs:
                tmap, inf_errs = self._infer_method_type_vars_full(
                    sig,
                    arg_types,
                    args=args,
                    expected_return=expected_return,
                    explicit_targs=explicit_targs,
                    phase=phase,
                )
                if inf_errs:
                    for err_m in inf_errs:
                        if phase == 1 and ("Fase 1" in err_m):
                            continue
                        if err_m not in inference_failures:
                            inference_failures.append(err_m)
                    return None
            else:
                tmap = {}
            eff_params = [self._substitute_type_vars(p, tmap) or p for p in raw_params]
            if phase < 3:
                total = 0
                for idx, (pt, a_node, a_t) in enumerate(zip(eff_params, args, arg_types)):
                    if is_va and idx == len(eff_params) - 1:
                        # Na fase 1/2, parâmetro varargs também pode casar como array direto
                        sc_arr = self._score_param_match(f"{pt}[]", a_node, a_t, phase)
                        sc_el = self._score_param_match(pt, a_node, a_t, phase)
                        sc = sc_arr if sc_arr is not None else sc_el
                    else:
                        sc = self._score_param_match(pt, a_node, a_t, phase)
                    if sc is None:
                        return None
                    total += sc
                return total, tmap
            else:
                if not is_va or nargs < len(eff_params) - 1:
                    return None
                fixed = eff_params[:-1]
                va_elem = eff_params[-1]
                total = 0
                for pt, a_node, a_t in zip(fixed, args[:len(fixed)], arg_types[:len(fixed)]):
                    sc = self._score_param_match(pt, a_node, a_t, 2)
                    if sc is None:
                        return None
                    total += sc
                tail = list(zip(args[len(fixed):], arg_types[len(fixed):]))
                if len(tail) == 1:
                    a_node, a_t = tail[0]
                    sc_arr = self._score_param_match(f"{va_elem}[]", a_node, a_t, 2)
                    if sc_arr is not None:
                        return total + sc_arr + 3, tmap
                for a_node, a_t in tail:
                    sc = self._score_param_match(va_elem, a_node, a_t, 2)
                    if sc is None:
                        return None
                    total += sc + 3
                return total, tmap

        def finalize_win(win_sig: Dict[str, Any], win_map: Dict[str, str]):
            eff_ret = self._substitute_type_vars(win_sig["ret"], win_map) or win_sig["ret"]
            bound = {k: self._substitute_type_vars(p, win_map) or p for k, p in enumerate(win_sig["params"])}
            resolved_sig = dict(win_sig)
            resolved_sig["throws"] = [self._substitute_type_vars(t, win_map) or t for t in win_sig.get("throws", [])]
            return resolved_sig, eff_ret, bound

        for phase in (1, 2, 3):
            applicable: List[Tuple[Dict[str, Any], int, Dict[str, str]]] = []
            for sig in candidates:
                m = match_candidate(sig, phase)
                if m is not None:
                    applicable.append((sig, m[0], m[1]))
            if not applicable:
                continue

            if len(applicable) == 1:
                win_sig, _, win_map = applicable[0]
                return finalize_win(win_sig, win_map)

            # Escolha da sobrecarga maximalmente específica (JLS §15.12.2.5)
            best_candidates: List[Tuple[Dict[str, Any], int, Dict[str, str]]] = []
            for cand in applicable:
                dominated = False
                for other in applicable:
                    if other[0] is cand[0]:
                        continue
                    if self._is_sig_more_specific(other[0], cand[0]):
                        dominated = True
                        break
                    # Se parâmetros são idênticos, método sobrescrito em subtipo domina método de supertipo
                    if other[0]["params"] == cand[0]["params"]:
                        o_owner = other[0].get("owner")
                        c_owner = cand[0].get("owner")
                        if o_owner and c_owner and o_owner != c_owner and self._is_subtype(o_owner, c_owner) is True:
                            dominated = True
                            break
                if not dominated:
                    best_candidates.append(cand)
            if not best_candidates:
                best_candidates = list(applicable)

            if len(best_candidates) > 1:
                min_score = min(c[1] for c in best_candidates)
                best_scored = [c for c in best_candidates if c[1] == min_score]
                if len(best_scored) > 1:
                    # Filtra candidatos cujos parâmetros são comprovadamente incompatíveis com os argumentos passados
                    filtered = []
                    for cand_item in best_scored:
                        sig, _, tmap = cand_item
                        eff_p = [self._substitute_type_vars(p, tmap) or p for p in sig["params"]]
                        incompatible = False
                        for p, a_node, a_t in zip(eff_p, args, arg_types):
                            if self._is_definitely_incompatible(p, a_node, a_t):
                                incompatible = True
                                break
                        if not incompatible:
                            filtered.append(cand_item)
                    if filtered:
                        best_scored = filtered

                    if len(best_scored) > 1:
                        # Preferência por tipos concretos sobre variáveis de tipo
                        def count_type_vars(cand_item):
                            sig, _, _ = cand_item
                            return sum(1 for p in sig["params"] if self._is_type_variable(p))
                        min_tvars = min(count_type_vars(c) for c in best_scored)
                        concrete_cands = [c for c in best_scored if count_type_vars(c) == min_tvars]
                        if len(concrete_cands) < len(best_scored):
                            best_scored = concrete_cands

                    if len(best_scored) > 1:
                        # Preferência por declaração em subtipo quando supertipo também é herdado
                        owners = {c[0].get("owner") for c in best_scored if c[0].get("owner")}
                        if len(owners) > 1:
                            kept = []
                            for c in best_scored:
                                c_owner = c[0].get("owner")
                                if c_owner:
                                    is_super = any(self._is_subtype(other_owner, c_owner) is True for other_owner in owners if other_owner != c_owner)
                                    if not is_super:
                                        kept.append(c)
                                else:
                                    kept.append(c)
                            if kept:
                                best_scored = kept

                    if len(best_scored) > 1:
                        self.errors.append(
                            SemanticError(
                                f"Invocação ambígua em '{call_desc}': múltiplos métodos sobrecarregados são igualmente aplicáveis (JLS §15.12.2.5).",
                                line,
                            )
                        )
                    win_sig, _, win_map = best_scored[0]
                    return finalize_win(win_sig, win_map)
                best_candidates = best_scored

            win_sig, _, win_map = best_candidates[0]
            return finalize_win(win_sig, win_map)

        # Nenhuma sobrecarga compatível encontrada
        if candidates and not any(self._is_type_variable(a) for a in arg_types if a):
            if inference_failures:
                self.errors.append(
                    SemanticError(
                        f"Falha na inferência de tipos em '{call_desc}': {inference_failures[0]} (JLS §18).",
                        line,
                    )
                )
            else:
                self.errors.append(
                    SemanticError(
                        f"Nenhuma sobrecarga aplicável encontrada para '{call_desc}' com {nargs} argumento(s) (JLS §15.12.2).",
                        line,
                    )
                )
        return None, None, None

    def _record_lambda_capture(self, name: str, line: int) -> None:
        """Registra acesso ou tentativa de modificação de variável local/parâmetro por expressão lambda (JLS §15.27.2)."""
        if self._lambda_scope_floor_stack:
            floor = self._lambda_scope_floor_stack[-1]
            shadowed = any(name in sc for sc in self._local_var_scopes[floor:])
            if not shadowed:
                for sc in reversed(self._local_var_scopes[:floor]):
                    if name in sc:
                        self._pending_lambda_captures.append((name, sc[name], line))
                        break

    def _is_modifiable_lvalue(
        self,
        target_node: Optional[ASTNode],
        target_name: Optional[str],
        line: int,
        op_desc: str,
        defer_flow_write: bool = False,
        defer_member_read: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """Verifica se operando/alvo de atribuição ou incremento é uma variável modificável (JLS §15.14 / §15.26)."""
        if target_node is not None and not isinstance(target_node, Identifier):
            if isinstance(target_node, MemberAccess):
                is_simple_this_field = (
                    defer_member_read
                    and isinstance(target_node.target, Identifier)
                    and target_node.target.name == "this"
                )
                if is_simple_this_field:
                    self._check_early_target_ref(
                        "this",
                        line,
                        f"Acesso inválido a membro via 'this' ('this.{target_node.member_name}')",
                    )
                    if self._in_static_context:
                        self.errors.append(
                            SemanticError("Não é possível usar 'this' em contexto estático.", line)
                        )
                else:
                    self._check_expression_flow(target_node)
                t_type = self._infer_member_access_receiver_type(target_node)
                if t_type and t_type.endswith("[]") and target_node.member_name == "length":
                    self.errors.append(
                        SemanticError(f"Não é possível modificar o campo 'final' 'length' de um array em {op_desc} (JLS §10.7).", line)
                    )
                    return False, "int"
                if t_type:
                    fields, is_known = self._collect_type_fields(t_type)
                    finfo = fields.get(target_node.member_name)
                    if finfo is not None:
                        if is_simple_this_field:
                            self._inheritance_analyzer.check_member_access(
                                finfo.get("owner_key") or t_type,
                                finfo.get("access", "public"),
                                bool(finfo.get("is_static", False)),
                                finfo.get("category", "campo"),
                                target_node.member_name,
                                line,
                                receiver_type=t_type,
                                via_super=False,
                            )
                        is_ctor_this_init = (
                            isinstance(target_node.target, Identifier)
                            and target_node.target.name == "this"
                            and self._callable_kind in ("constructor", "initializer")
                            and finfo.get("category") in ("campo", "componente_record")
                        )
                        if (finfo.get("is_final") or finfo.get("category") in ("constante_interface", "constante_enum", "componente_record")) and not is_ctor_this_init:
                            self.errors.append(
                                SemanticError(f"Não é possível modificar membro 'final' '{target_node.member_name}' em {op_desc}.", line)
                            )
                            return False, finfo.get("type")
                        return True, finfo.get("type")
                    if is_known:
                        self.errors.append(
                            SemanticError(f"Campo '{target_node.member_name}' não existe no tipo '{t_type}'.", line)
                        )
                        return False, None
                return True, self.infer_type(target_node)
            if isinstance(target_node, ArrayAccess):
                self._check_expression_flow(target_node)
                return True, self.infer_type(target_node)
            self._check_expression_flow(target_node)
            self.errors.append(
                SemanticError(f"O alvo de {op_desc} deve ser uma variável modificável (JLS §15.26).", line)
            )
            return False, None

        name = target_node.name if isinstance(target_node, Identifier) else target_name
        if not name:
            self.errors.append(SemanticError(f"O alvo de {op_desc} deve ser uma variável modificável.", line))
            return False, None
        if name in ("this", "super") or name.startswith(("this.", "super.")):
            self._check_early_target_ref(name, line)
            return True, None
        if "." in name:
            return True, None

        symbol = self._lookup_var_symbol(name)
        if symbol is not None and symbol.get("owner_key") and not defer_flow_write:
            self._inheritance_analyzer.check_member_access(
                symbol["owner_key"],
                symbol.get("access", "public"),
                bool(symbol.get("is_static", False)),
                symbol.get("category", "campo"),
                name,
                line,
            )
        if self._in_early_construction_context and symbol is not None and symbol.get("category") == "campo" and not symbol.get("is_static", False):
            self.errors.append(
                SemanticError(f"Acesso inválido ao campo de instância '{name}' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513).", line)
            )
        if symbol is not None and symbol.get("category") in ("constante_interface", "constante_enum", "componente_record"):
            self.errors.append(
                SemanticError(f"Não é possível modificar '{name}' ({symbol.get('category')} é implicitamente final).", line)
            )
            return False, symbol.get("type")
        if symbol is None or symbol.get("category") not in ("variavel", "parametro", "campo"):
            self.errors.append(SemanticError(f"Variável '{name}' não foi declarada.", line))
            return False, None
        local_info = self._find_local_var_info(name)
        if local_info is not None:
            if not defer_flow_write:
                if local_info.get("is_final", False) and local_info.get("has_initializer", True):
                    self.errors.append(SemanticError(f"Não é possível modificar a variável 'final' '{name}'.", line))
                    return False, symbol.get("type")
                self._record_lambda_capture(name, line)
                self._mark_local_var_reassigned(name)
        elif symbol.get("is_final", False) and symbol.get("category") == "campo":
            # Permite atribuição a campo final apenas dentro de construtores ou inicializadores de instância/estático
            if self._callable_kind not in ("constructor", "initializer"):
                self.errors.append(SemanticError(f"Não é possível atribuir valor ao campo 'final' '{name}'.", line))
                return False, symbol.get("type")
        return True, symbol.get("type")

    def _check_cast(self, node: CastExpression):
        """Valida expressão de cast simples ou interseção de tipos segundo JLS §5.5."""
        line = getattr(node, "line", 1)
        tref = getattr(node, "target_type", None)
        self._check_type_ref_annotations(tref)
        bounds = list(getattr(node, "additional_bounds", []) or [])
        for b in bounds:
            self._check_type_ref_annotations(b)

        target_str = self._normalize_type_str(tref) or ""
        if target_str == "void":
            self.errors.append(SemanticError("Tipo 'void' não é permitido em expressão de cast (JLS §15.16).", line))
            self._check_expression_flow(node.expression)
            return

        if bounds:
            first_base = self._simple_base_name(target_str) or ""
            if first_base in self.PRIMITIVE_TYPES:
                self.errors.append(
                    SemanticError("Cast de interseção '(T & ...)' não pode incluir tipos primitivos (JLS §4.4 / §15.16).", line)
                )
            for b in bounds:
                b_str = self._normalize_type_str(b) or ""
                b_kind = self._is_class_kind(b_str)
                if b_kind is True:
                    self.errors.append(
                        SemanticError(f"Limite adicional '{b_str}' em cast de interseção deve ser uma interface (JLS §4.4 / §15.16).", line)
                    )

        # Propaga target typing do cast quando expressão interna é lambda/method reference
        if isinstance(node.expression, (LambdaExpression, MethodReference, SwitchExpression, ConditionalExpression)) and target_str:
            self._check_expression_with_target(node.expression, target_str)
            return

        self._check_expression_flow(node.expression)
        src_str = self.infer_type(node.expression)
        if not target_str or not src_str or src_str == "desconhecido":
            return

        types_to_check = [target_str] + [self._normalize_type_str(b) or "" for b in bounds if self._normalize_type_str(b)]
        for t in types_to_check:
            ok, err_msg = self._is_single_cast_valid(t, src_str)
            if not ok:
                self.errors.append(SemanticError(err_msg or f"Cast inválido de '{src_str}' para '{t}' (JLS §5.5).", line))
                break

    def _are_generic_cast_args_compatible(self, src_str: str, target_str: str) -> bool:
        """Verifica se dois tipos parametrizados da mesma base são compatíveis para cast (JLS §5.5.1)."""
        _, s_args, s_dims = self._extract_generic_args(src_str)
        _, t_args, t_dims = self._extract_generic_args(target_str)
        if s_dims != t_dims:
            return False
        if not s_args or not t_args:
            return True
        if len(s_args) != len(t_args):
            return False
        for sa, ta in zip(s_args, t_args):
            sa_s = sa.strip()
            ta_s = ta.strip()
            if sa_s == ta_s or sa_s == "?" or ta_s == "?":
                continue
            sa_simple = self._simple_base_name(sa_s) or sa_s
            ta_simple = self._simple_base_name(ta_s) or ta_s
            if self._is_type_variable(sa_simple) or self._is_type_variable(ta_simple):
                continue
            if self._is_capture_var(sa_s) or self._is_capture_var(ta_s):
                if self._is_capture_var(sa_s):
                    cap_u = (self._capture_vars.get(sa_s, {}).get("upper_bounds") or ["Object"])[0]
                    t_eff = ta_s.split(" ", 2)[-1].strip() if ta_s.startswith("? ") else ta_s
                    if not self._is_capture_var(t_eff) and t_eff != "?":
                        if self._is_subtype(t_eff, cap_u) is False and self._are_types_disjoint(t_eff, cap_u) is True:
                            return False
                if self._is_capture_var(ta_s):
                    cap_u = (self._capture_vars.get(ta_s, {}).get("upper_bounds") or ["Object"])[0]
                    s_eff = sa_s.split(" ", 2)[-1].strip() if sa_s.startswith("? ") else sa_s
                    if not self._is_capture_var(s_eff) and s_eff != "?":
                        if self._is_subtype(s_eff, cap_u) is False and self._are_types_disjoint(s_eff, cap_u) is True:
                            return False
                continue
            if sa_s.startswith(("? extends ", "? super ")) or ta_s.startswith(("? extends ", "? super ")):
                s_bound = sa_s.split(" ", 2)[-1].strip() if sa_s.startswith("? ") else sa_s
                t_bound = ta_s.split(" ", 2)[-1].strip() if ta_s.startswith("? ") else ta_s
                if sa_s.startswith("? extends ") and not ta_s.startswith("? "):
                    if self._is_subtype(t_bound, s_bound) is False and self._are_types_disjoint(t_bound, s_bound) is True:
                        return False
                elif ta_s.startswith("? extends ") and not sa_s.startswith("? "):
                    if self._is_subtype(s_bound, t_bound) is False and self._are_types_disjoint(s_bound, t_bound) is True:
                        return False
                continue
            if sa_simple != ta_simple:
                return False
            if not self._are_generic_cast_args_compatible(sa_s, ta_s):
                return False
        return True

    def _is_single_cast_valid(self, target_str: str, src_str: str) -> Tuple[bool, Optional[str]]:
        """Verifica validade de conversão por cast entre um par (source -> target) conforme JLS §5.5."""
        t_clean = self._strip_leading_type_annotations(target_str) or target_str
        s_clean = self._strip_leading_type_annotations(src_str) or src_str
        t_simple = self._simple_base_name(t_clean) or t_clean
        s_simple = self._simple_base_name(s_clean) or s_clean

        if self._is_type_variable(t_simple) or self._is_type_variable(s_simple):
            return True, None
        if t_simple == s_simple:
            if not self._are_generic_cast_args_compatible(s_clean, t_clean):
                return False, f"Tipos incompatíveis em cast: '{s_clean}' não pode ser convertido para '{t_clean}' (JLS §5.5.1)."
            return True, None

        t_prim = t_simple in self.PRIMITIVE_TYPES
        s_prim = s_simple in self.PRIMITIVE_TYPES

        if t_prim and s_prim:
            if t_simple == "boolean" or s_simple == "boolean":
                return False, f"Conversão de cast inválida: não é possível converter '{s_clean}' para '{t_clean}' (JLS §5.5)."
            return True, None

        if s_prim and not t_prim:
            # Primitivo -> Referência: apenas boxing seguido de widening para supertipo do wrapper (ex: int -> Integer/Number/Object)
            boxed = self.PRIMITIVE_TO_WRAPPER.get(s_simple)
            if not boxed:
                return False, f"Conversão de cast inválida de '{s_clean}' para '{t_clean}' (JLS §5.5)."
            if t_simple == boxed or self._is_subtype(boxed, t_clean) is True:
                return True, None
            return False, f"Conversão de cast inválida de '{s_clean}' para '{t_clean}': primitivo não pode ser convertido para esse tipo de referência (JLS §5.5)."

        if not s_prim and t_prim:
            # Referência -> Primitivo: Object ou supertipo compatível (ex: Number/Integer -> int, Object -> boolean), mas String -> int é proibido
            if s_simple == "null":
                return False, f"Não é possível converter literal 'null' para o tipo primitivo '{t_clean}' (JLS §5.5)."
            unboxed = self.WRAPPER_TO_PRIMITIVE.get(s_simple)
            if unboxed is not None:
                if unboxed == t_simple:
                    return True, None
                if t_simple != "boolean" and unboxed != "boolean":
                    # Java não permite cast direto de Double para int se Double é final e não unboxing+widening para outro wrapper sem primitivo?
                    # JLS §5.5 permite referência -> primitivo via unboxing + widening opcional (ex: Integer -> long OK, mas Double -> int NÃO pois narrowing primitivo não segue unboxing!)
                    if t_simple in self.WIDENING_PRIMITIVE_TARGETS.get(unboxed, set()):
                        return True, None
                return False, f"Conversão de cast inválida de '{s_clean}' para '{t_clean}' (JLS §5.5)."
            boxed_target = self.PRIMITIVE_TO_WRAPPER.get(t_simple)
            if boxed_target and (self._is_subtype(boxed_target, s_clean) is True or self._is_subtype(s_clean, boxed_target) is True):
                return True, None
            if not self._is_known_type(s_clean):
                return True, None
            return False, f"Tipos incompatíveis em cast: '{s_clean}' não pode ser convertido para '{t_clean}' (JLS §5.5)."

        # Referência -> Referência
        if s_simple == "null":
            return True, None
        if self._are_types_disjoint(s_clean, t_clean) is True:
            return False, f"Tipos incompatíveis em cast: '{s_clean}' não pode ser convertido para '{t_clean}' (JLS §5.5)."
        return True, None

    def _infer_member_access_receiver_type(self, node: MemberAccess) -> Optional[str]:
        """Resolve o tipo do alvo de um MemberAccess (incluindo identificador de classe estático)."""
        if isinstance(node.target, Identifier):
            sym = self._lookup_var_symbol(node.target.name)
            if sym is not None and "type" in sym:
                return sym["type"]
            if self._is_known_type(node.target.name):
                return node.target.name
            if node.target.name == "this":
                return self._current_enclosing_type()
            if node.target.name == "super":
                cur = self._current_enclosing_type()
                if cur:
                    supers, _ = self._direct_supertypes(cur)
                    return supers[0] if supers else "Object"
        qtarget = self._extract_qualified_name(node.target)
        if qtarget and (
            self._is_known_type(qtarget)
            or (qtarget.split(".")[-1][0].isupper() and self._lookup_var_symbol(qtarget.split(".")[0]) is None)
        ):
            return qtarget
        return self.infer_type(node.target)

    def _check_lambda_with_target(self, node: LambdaExpression, target_type: Optional[str]) -> Optional[str]:
        """Valida expressão lambda contra target_type (ou sem alvo em 'var'), checando parâmetros, retorno e captura efetivamente final."""
        line = getattr(node, "line", 1)
        sam_full, is_known = self._resolve_functional_interface_full(target_type)
        sam_params: Optional[List[str]] = None
        sam_ret: Optional[str] = None
        sam_throws: List[str] = []

        if target_type and target_type not in ("var", "desconhecido"):
            if sam_full is None and is_known:
                self.errors.append(
                    SemanticError(
                        f"Tipo alvo '{target_type}' em expressão lambda não é uma interface funcional válida (JLS §15.27).",
                        line,
                    )
                )
            elif sam_full is not None:
                sam_params, sam_ret, sam_throws = sam_full
                if len(node.parameters) != len(sam_params):
                    self.errors.append(
                        SemanticError(
                            f"Número de parâmetros incompatível na expressão lambda: esperado {len(sam_params)} para '{target_type}', encontrado {len(node.parameters)} (JLS §15.27.3).",
                            line,
                        )
                    )

        typed_params = list(getattr(node, "typed_parameters", []) or [])
        param_mode = getattr(node, "parameter_mode", "inferred")
        param_types_for_scope: List[str] = []

        for idx, pname in enumerate(node.parameters):
            lp = typed_params[idx] if idx < len(typed_params) else None
            if param_mode == "explicit" and lp is not None and getattr(lp, "type_ref", None) is not None:
                self._analyze_annotations(getattr(lp, "annotations", []), valid_targets={"PARAMETER"}, adjacent_type_ref=lp.type_ref)
                self._check_type_ref_annotations(lp.type_ref)
                pt_str = self._normalize_type_str(lp.type_ref) or "Object"
                if getattr(lp, "is_varargs", False) and not pt_str.endswith("[]"):
                    pt_str += "[]"
                if sam_params is not None and idx < len(sam_params):
                    sp = sam_params[idx]
                    incompatible_explicit = False
                    if not self._is_type_variable(sp):
                        if self._simple_base_name(pt_str) != self._simple_base_name(sp):
                            if not (pt_str == "Object" and sp == "Object"):
                                incompatible_explicit = True
                        elif "<" in sp and "<" in pt_str and self._generic_args_compatible(pt_str, sp) is False:
                            incompatible_explicit = True
                    if incompatible_explicit:
                        self.errors.append(
                            SemanticError(
                                f"Tipo de parâmetro '{pt_str}' incompatível com '{sp}' da interface funcional '{target_type}' (JLS §15.27.3).",
                                getattr(lp, "line", line),
                            )
                        )
                param_types_for_scope.append(pt_str)
            elif sam_params is not None and idx < len(sam_params):
                if param_mode == "var" and lp is not None:
                    self._analyze_annotations(getattr(lp, "annotations", []), valid_targets={"PARAMETER"})
                param_types_for_scope.append(sam_params[idx])
            else:
                if param_mode == "var" and lp is not None:
                    self._analyze_annotations(getattr(lp, "annotations", []), valid_targets={"PARAMETER"})
                param_types_for_scope.append("Object")

        self.symbols.enter_scope()
        floor_idx = len(self._local_var_scopes)
        self._lambda_scope_floor_stack.append(floor_idx)
        self._local_var_scopes.append({})
        self._active_pattern_scopes.append({})
        self._local_type_scopes.append({})
        self._local_declared_type_scopes.append({})
        self._lambda_return_exprs_stack.append([])
        saved_ctx = self._enter_exec_context("lambda", return_type=sam_ret, share_locals=True)
        self._exception_analyzer.push_callable_frame(
            "lambda",
            f"expressão lambda de '{target_type or 'SAM'}'",
            sam_throws,
            enforce_unreported=(sam_params is not None and not self._flow_suppress_errors),
        )
        inferred_ret: Optional[str] = sam_ret
        try:
            for idx, p in enumerate(node.parameters):
                if p != "_":
                    lp = typed_params[idx] if idx < len(typed_params) else None
                    is_fin = ("final" in getattr(lp, "modifiers", [])) if lp is not None else False
                    self._register_local_var(
                        p,
                        param_types_for_scope[idx] if idx < len(param_types_for_scope) else "Object",
                        getattr(lp, "line", line) if lp is not None else line,
                        is_final=is_fin,
                        has_initializer=True,
                        category="parametro",
                    )

            if node.is_block_body and isinstance(node.body, Block):
                self.analyze_block(node.body)
                ret_exprs = self._lambda_return_exprs_stack[-1] if self._lambda_return_exprs_stack else []
                if sam_ret == "void":
                    for re in ret_exprs:
                        if re is not None:
                            self.errors.append(
                                SemanticError("Expressão lambda com retorno 'void' não pode retornar valor em 'return' (JLS §15.27.3).", getattr(re, "line", line))
                            )
                elif sam_ret is not None:
                    if self._stmt_completes_normally(node.body):
                        self.errors.append(
                            SemanticError(
                                f"Bloco de lambda deve retornar valor compatível com '{sam_ret}' em todos os caminhos de execução (JLS §15.27.3).",
                                line,
                            )
                        )
                    for re in ret_exprs:
                        if re is None:
                            self.errors.append(
                                SemanticError(f"Instrução 'return;' sem valor não é permitida em lambda com retorno '{sam_ret}' (JLS §15.27.3).", line)
                            )
                else:
                    # Verifica consistência interna quando não há alvo SAM fechado
                    has_val = any(r is not None for r in ret_exprs)
                    has_void = any(r is None for r in ret_exprs)
                    if has_val and has_void:
                        self.errors.append(
                            SemanticError("Bloco de expressão lambda mistura retornos com valor e sem valor (JLS §15.27.3).", line)
                        )
            elif node.body is not None:
                if sam_ret == "void":
                    if not self._is_statement_expression(node.body):
                        self.errors.append(
                            SemanticError(
                                "Corpo de expressão lambda para método abstrato 'void' deve ser uma statement expression (JLS §15.27.3).",
                                getattr(node.body, "line", line),
                            )
                        )
                    self._check_expression_flow(node.body)
                elif sam_ret is not None:
                    self._check_expression_with_target(node.body, sam_ret)
                    if not self._is_type_variable(sam_ret) and sam_ret not in ("Object", "var", "desconhecido"):
                        body_t = self.infer_type(node.body)
                        if body_t == "void":
                            self.errors.append(
                                SemanticError(
                                    f"Corpo de lambda 'void' é incompatível com o tipo de retorno esperado '{sam_ret}' (JLS §15.27.3).",
                                    getattr(node.body, "line", line),
                                )
                            )
                        elif not self._is_assignable_expr(sam_ret, node.body):
                            self.errors.append(
                                SemanticError(
                                    f"Tipo de retorno da expressão lambda ('{body_t}') é incompatível com '{sam_ret}' (JLS §15.27.3).",
                                    getattr(node.body, "line", line),
                                )
                            )
                else:
                    self._check_expression_flow(node.body)
                    inferred_ret = self.infer_type(node.body)
        finally:
            self._exception_analyzer.pop_callable_frame()
            self._restore_exec_context(saved_ctx)
            self._lambda_return_exprs_stack.pop()
            self._lambda_scope_floor_stack.pop()
            self._local_declared_type_scopes.pop()
            self._local_type_scopes.pop()
            self._pop_pattern_scope()
            self._local_var_scopes.pop()
            self.symbols.exit_scope()

        if target_type and sam_full is not None:
            self._inferred_types[id(node)] = target_type
            return target_type
        return None

    def _check_method_ref_with_target(self, node: MethodReference, target_type: Optional[str]) -> Optional[str]:
        """Valida todas as 5 formas de method reference contra target_type (JLS §15.13)."""
        line = getattr(node, "line", 1)
        if isinstance(node.target, Identifier) and node.target.name in ("this", "super"):
            self._check_early_target_ref(
                node.target.name,
                line,
                f"Referência inválida a método via '{node.target.name}' ('{node.target.name}::{node.method_name}')",
            )
        elif getattr(node, "is_array_creation", False):
            arr_tref = getattr(node, "array_type", None) or (
                node.target if isinstance(node.target, TypeReference) else None
            )
            if isinstance(arr_tref, TypeReference):
                self._check_type_ref_annotations(arr_tref)
                self._check_array_component_reifiable(arr_tref, line, "referência de criação de array '::new'")
        elif not getattr(node, "is_array_creation", False):
            if isinstance(node.target, Identifier) and (node.target.name in ("this", "super") or (node.target.name and node.target.name[0].isupper())):
                pass
            elif isinstance(node.target, TypeReference):
                self._check_type_ref_annotations(node.target)
            elif node.target is not None:
                self._check_expression_flow(node.target)
        for targ_node in getattr(node, "type_arguments", []) or []:
            self._check_type_ref_annotations(targ_node)

        sam_full, is_known_sam = self._resolve_functional_interface_full(target_type)
        if target_type and target_type not in ("var", "desconhecido"):
            if sam_full is None and is_known_sam:
                self.errors.append(
                    SemanticError(
                        f"Tipo alvo '{target_type}' em method reference não é uma interface funcional válida (JLS §15.13).",
                        line,
                    )
                )
                return None

        if sam_full is None:
            return None

        sam_params, sam_ret, sam_throws = sam_full

        def check_ref_throws(msig: Optional[Dict[str, Any]]) -> None:
            if msig is None or self._flow_suppress_errors:
                return
            for ex in msig.get("throws", []):
                if self._exception_analyzer.is_checked_exception(ex) is True:
                    if self._exception_analyzer.is_covered_by(ex, sam_throws) is False:
                        self.errors.append(
                            SemanticError(
                                f"Referência a método/construtor pode lançar exceção verificada '{ex}' incompatível com a cláusula 'throws' de '{target_type}' (JLS §15.13.2).",
                                line,
                            )
                        )
        if getattr(node, "is_array_creation", False):
            # Forma 5: Type[]::new -> espera 1 parâmetro int/integral e retorno compatível com array
            if len(sam_params) != 1 or (not self._is_integral_type(sam_params[0]) and not self._is_type_variable(sam_params[0])):
                self.errors.append(
                    SemanticError(
                        f"Referência a criação de array '::new' exige interface funcional com 1 parâmetro inteiro (encontrado '{sam_params}' em '{target_type}' — JLS §15.13.1).",
                        line,
                    )
                )
            arr_t = self._normalize_type_str(getattr(node, "array_type", None)) or self._normalize_type_str(node.target)
            if arr_t and sam_ret != "void" and not self._is_type_variable(sam_ret):
                if not self.is_assignable(sam_ret, arr_t):
                    self.errors.append(
                        SemanticError(
                            f"Tipo retornado pela referência de array ('{arr_t}') é incompatível com '{sam_ret}' (JLS §15.13.2).",
                            line,
                        )
                    )
            self._inferred_types[id(node)] = target_type
            return target_type

        if node.method_name == "new":
            # Forma 4: ClassName::new
            if isinstance(node.target, TypeReference):
                tname = self._normalize_type_str(node.target) or ""
            elif isinstance(node.target, Identifier):
                tname = node.target.name
            elif isinstance(node.target, MemberAccess):
                tname = self._extract_qualified_name(node.target) or ""
            else:
                tname = self._normalize_type_str(node.target) or ""
            ctors, is_known_c, tkind = self._collect_type_constructors(tname)
            tdecl = self._lookup_type_decl(self._simple_base_name(tname) or tname)
            is_abstract_cls = (
                tdecl is not None
                and tdecl[0] == "class"
                and "abstract" in (getattr(tdecl[1], "modifiers", []) or [])
            )
            req_enclosing = self._requires_enclosing_instance(tname)
            has_enclosing = False
            if req_enclosing is not None:
                avail_enclosing = self._available_enclosing_instance_types()
                has_enclosing = any(
                    enc_t == req_enclosing or self._is_subtype(enc_t, req_enclosing) is True
                    for enc_t in avail_enclosing
                )
            if tkind in ("interface", "enum"):
                self.errors.append(
                    SemanticError(f"Não é possível referenciar construtor de {tkind} '{tname}::new' (JLS §15.13).", line)
                )
            elif is_abstract_cls:
                self.errors.append(
                    SemanticError(f"Não é possível referenciar construtor de classe abstrata '{tname}::new' (JLS §15.13.1).", line)
                )
            elif req_enclosing is not None and not has_enclosing:
                self.errors.append(
                    SemanticError(
                        f"Não há instância envolvente válida do tipo '{req_enclosing}' no escopo para referenciar construtor de inner class '{tname}::new' (JLS §15.13.1 / §8.1.3).",
                        line,
                    )
                )
            elif ctors:
                matched_ctor_sig = None
                for csig in ctors:
                    if len(csig["params"]) == len(sam_params):
                        if all(self._score_param_match(cp, None, sp, 2) is not None for cp, sp in zip(csig["params"], sam_params)):
                            matched_ctor_sig = csig
                            break
                if matched_ctor_sig is None and not any(self._is_type_variable(sp) for sp in sam_params):
                    self.errors.append(
                        SemanticError(
                            f"Nenhum construtor compatível encontrado para '{tname}::new' com assinatura '{target_type}' (JLS §15.13.1).",
                            line,
                        )
                    )
                elif matched_ctor_sig is not None and sam_ret != "void" and not self._is_type_variable(sam_ret):
                    if not self.is_assignable(sam_ret, tname):
                        self.errors.append(
                            SemanticError(
                                f"Tipo criado por '{tname}::new' ('{tname}') é incompatível com o retorno esperado '{sam_ret}' (JLS §15.13.2).",
                                line,
                            )
                        )
                if matched_ctor_sig is not None:
                    self._inheritance_analyzer.check_member_access(
                        matched_ctor_sig.get("owner_key") or matched_ctor_sig.get("owner") or tname,
                        matched_ctor_sig.get("access", "public"),
                        False,
                        "construtor",
                        self._simple_base_name(tname) or tname,
                        line,
                    )
                check_ref_throws(matched_ctor_sig)
            self._inferred_types[id(node)] = target_type
            return target_type

        # Formas 1, 2 e 3: Class::staticMethod, expr::instanceMethod, ReferenceType::instanceMethod
        recv_is_type = False
        recv_type: Optional[str] = None
        if isinstance(node.target, TypeReference):
            recv_is_type = True
            recv_type = self._normalize_type_str(node.target)
        elif isinstance(node.target, Identifier):
            sym = self._lookup_var_symbol(node.target.name)
            if sym is not None and "type" in sym and sym.get("category") not in self.TYPE_SYMBOL_CATEGORIES:
                recv_type = sym["type"]
            elif self._is_known_type(node.target.name):
                recv_is_type = True
                recv_type = node.target.name
            elif node.target.name == "this":
                recv_type = self._current_enclosing_type()
            elif node.target.name == "super":
                cur = self._current_enclosing_type()
                if cur:
                    supers, _ = self._direct_supertypes(cur)
                    recv_type = supers[0] if supers else "Object"
        else:
            recv_type = self.infer_type(node.target)

        if not recv_type:
            self._record_unresolved(f"Method reference '{node.method_name}' com receptor externo não resolvido.")
            self._inferred_types[id(node)] = target_type
            return target_type

        methods, is_known_m, _ = self._collect_type_methods(recv_type, node.method_name)
        if not methods:
            if is_known_m:
                self.errors.append(
                    SemanticError(
                        f"Método '{node.method_name}' não encontrado no tipo '{recv_type}' para method reference (JLS §15.13.1).",
                        line,
                    )
                )
            else:
                self._record_unresolved(f"Method reference '{recv_type}::{node.method_name}' não pôde ser resolvida sem classpath completo.")
            self._inferred_types[id(node)] = target_type
            return target_type

        explicit_targ_nodes = getattr(node, "type_arguments", None) or []
        explicit_targs = [self._normalize_type_str(t) or "Object" for t in explicit_targ_nodes] if explicit_targ_nodes else []
        recv_tvar_map = self._type_var_mapping_for_type(recv_type) if (explicit_targs and recv_type) else {}

        matched_method_sig = None
        best_bound_errors: List[SemanticError] = []
        fallback_bound_errors: List[SemanticError] = []
        saw_targ_arity_mismatch = False
        for msig in methods:
            mparams = msig["params"]
            if msig["static"]:
                if not recv_is_type or len(mparams) != len(sam_params):
                    continue
                sam_arg_slice = sam_params
            elif not recv_is_type:
                # Se receptor é uma instância, aridade é igual; se receptor é tipo, primeiro arg do SAM vira receptor (len(mparams) + 1 == len(sam_params))
                if len(mparams) != len(sam_params):
                    continue
                sam_arg_slice = sam_params
            else:
                if len(sam_params) != len(mparams) + 1:
                    continue
                recv_arg = sam_params[0]
                if not (self._is_type_variable(recv_arg) or self.is_assignable(recv_type, recv_arg) or self._is_subtype(recv_arg, recv_type) is True):
                    continue
                sam_arg_slice = sam_params[1:]

            eff_mparams = mparams
            eff_ret = msig["ret"]
            cand_bound_errors: List[SemanticError] = []
            if explicit_targs:
                tparams = msig.get("tparams") or []
                if tparams:
                    if len(explicit_targs) != len(tparams):
                        saw_targ_arity_mismatch = True
                        continue
                    method_decls = [
                        (tp, list((msig.get("tparam_bounds") or {}).get(tp, ["Object"])))
                        for tp in tparams
                    ]
                    explicit_map = self._validate_type_args_against_bounds(
                        f"{recv_type}::{node.method_name}",
                        explicit_targs,
                        line,
                        outer_subst=None if msig["static"] else recv_tvar_map,
                        decls_override=method_decls,
                        error_sink=cand_bound_errors,
                    )
                    eff_mparams = [self._substitute_type_vars(mp, explicit_map) or mp for mp in mparams]
                    eff_ret = self._substitute_type_vars(eff_ret, explicit_map) or eff_ret

            if cand_bound_errors and not fallback_bound_errors:
                fallback_bound_errors = cand_bound_errors

            if all(self._score_param_match(mp, None, sp, 2) is not None for mp, sp in zip(eff_mparams, sam_arg_slice)):
                if sam_ret == "void" or self._is_type_variable(sam_ret) or self._is_type_variable(eff_ret) or self.is_assignable(sam_ret, eff_ret):
                    if cand_bound_errors:
                        if not best_bound_errors:
                            best_bound_errors = cand_bound_errors
                        continue
                    matched_method_sig = msig
                    break

        if matched_method_sig is None:
            if best_bound_errors:
                self.errors.extend(best_bound_errors)
            elif fallback_bound_errors:
                self.errors.extend(fallback_bound_errors)
            elif saw_targ_arity_mismatch or not any(self._is_type_variable(sp) for sp in sam_params):
                self.errors.append(
                    SemanticError(
                        f"Referência a método '{recv_type}::{node.method_name}' incompatível com o tipo alvo '{target_type}' (JLS §15.13.1).",
                        line,
                    )
                )
        elif matched_method_sig is not None:
            mref_via_super = isinstance(node.target, Identifier) and node.target.name == "super"
            self._inheritance_analyzer.check_member_access(
                matched_method_sig.get("owner_key") or matched_method_sig.get("owner") or recv_type,
                matched_method_sig.get("access", "public"),
                bool(matched_method_sig.get("static", False)),
                "método",
                node.method_name,
                line,
                receiver_type=None if (recv_is_type or mref_via_super) else recv_type,
                via_super=mref_via_super,
            )
        check_ref_throws(matched_method_sig)
        self._inferred_types[id(node)] = target_type
        return target_type

    @staticmethod
    def _parse_java_int_literal(val_s: str) -> Optional[Tuple[int, bool, int]]:
        """Interpreta um literal inteiro Java (decimal, hex, binário ou octal) retornando (valor, is_long, base)."""
        s = val_s.strip()
        is_long = s.endswith(("l", "L"))
        body = (s[:-1] if is_long else s).replace("_", "")
        if not body:
            return None
        try:
            if body.startswith(("0x", "0X")):
                return int(body[2:], 16), is_long, 16
            if body.startswith(("0b", "0B")):
                return int(body[2:], 2), is_long, 2
            if len(body) > 1 and body.startswith("0") and not (
                "." in body or "e" in body.lower() or body.endswith(("f", "F", "d", "D"))
            ):
                return int(body[1:], 8), is_long, 8
            if body.isdigit():
                return int(body, 10), is_long, 10
        except ValueError:
            return None
        return None

    def _validate_numeric_literal(self, node: Literal, negated: bool = False) -> None:
        """Valida faixa de literais inteiros (JLS §3.10.1) e ponto flutuante (JLS §3.10.2)."""
        nid = id(node)
        if nid in self._validated_literal_ids:
            return
        self._validated_literal_ids.add(nid)

        kind = getattr(node, "kind", "")
        if kind not in ("NUM", "INT", "LONG", "FLOAT", "DOUBLE"):
            return

        val_s = str(getattr(node, "value", "")).strip()
        line = getattr(node, "line", 1)

        is_fp_text = (
            kind in ("FLOAT", "DOUBLE")
            or "." in val_s
            or ("e" in val_s.lower() and not val_s.startswith(("0x", "0X")))
            or ("p" in val_s.lower() and val_s.startswith(("0x", "0X")))
            or (val_s.endswith(("f", "F", "d", "D")) and not val_s.startswith(("0x", "0X")))
        )

        if kind in ("NUM", "INT", "LONG") and not is_fp_text:
            parsed = self._parse_java_int_literal(val_s)
            if parsed is None:
                return
            num_val, is_long_lit, base = parsed
            is_long = (kind == "LONG") or is_long_lit
            if base == 10:
                if is_long:
                    max_val = (1 << 63) if negated else ((1 << 63) - 1)
                else:
                    max_val = (1 << 31) if negated else ((1 << 31) - 1)
            else:
                max_val = ((1 << 64) - 1) if is_long else ((1 << 32) - 1)
            if num_val > max_val:
                tname = "long" if is_long else "int"
                self.errors.append(
                    SemanticError(
                        f"Literal inteiro '{tname}' fora da faixa permitida: '{val_s}' (JLS §3.10.1).",
                        line,
                    )
                )
            return

        is_float = (kind == "FLOAT") or val_s.endswith(("f", "F"))
        raw = val_s[:-1] if val_s.endswith(("f", "F", "d", "D")) else val_s
        clean = raw.replace("_", "")
        tname = "float" if is_float else "double"

        if clean.startswith(("0x", "0X")):
            mant = clean[2:].split("p", 1)[0].split("P", 1)[0]
            has_nonzero = any(c in "123456789abcdefABCDEF" for c in mant)
            try:
                fval = float.fromhex(clean)
            except OverflowError:
                self.errors.append(
                    SemanticError(
                        f"Literal de ponto flutuante '{tname}' muito grande (overflow): '{val_s}' (JLS §3.10.2).",
                        line,
                    )
                )
                return
            except ValueError:
                return
        else:
            mant = clean.split("e", 1)[0].split("E", 1)[0]
            has_nonzero = any(c in "123456789" for c in mant)
            try:
                fval = float(clean)
            except ValueError:
                return

        if math.isinf(fval):
            self.errors.append(
                SemanticError(
                    f"Literal de ponto flutuante '{tname}' muito grande (overflow): '{val_s}' (JLS §3.10.2).",
                    line,
                )
            )
            return

        if is_float:
            try:
                packed = struct.pack(">f", fval)
            except OverflowError:
                self.errors.append(
                    SemanticError(
                        f"Literal de ponto flutuante 'float' muito grande (overflow): '{val_s}' (JLS §3.10.2).",
                        line,
                    )
                )
                return
            if has_nonzero and packed in (b"\x00\x00\x00\x00", b"\x80\x00\x00\x00"):
                self.errors.append(
                    SemanticError(
                        f"Literal de ponto flutuante 'float' muito pequeno (underflow): '{val_s}' (JLS §3.10.2).",
                        line,
                    )
                )
        elif has_nonzero and fval == 0.0:
            self.errors.append(
                SemanticError(
                    f"Literal de ponto flutuante 'double' muito pequeno (underflow): '{val_s}' (JLS §3.10.2).",
                    line,
                )
            )

    def _validate_unary_op(self, node: UnaryOp):
        """Valida tipo e modificabilidade dos operandos em operadores unários (JLS §15.14 / §15.15)."""
        line = getattr(node, "line", 1)
        if node.op in ("++", "--", "post++", "post--"):
            ok, op_type = self._is_modifiable_lvalue(
                node.operand,
                getattr(node.operand, "name", None),
                line,
                f"'{node.op}'",
                defer_flow_write=True,
                defer_member_read=False,
            )
            if isinstance(node.operand, Identifier) and "." not in node.operand.name:
                self._flow_apply_local_write(node.operand.name, line, is_compound=True)
            elif isinstance(node.operand, MemberAccess) and isinstance(node.operand.target, Identifier) and node.operand.target.name == "this":
                self._flow_apply_local_write(node.operand.member_name, line, is_compound=True, is_this_qualified=True)
            if ok and op_type and self._unboxed_numeric(op_type) is None and op_type not in ("Object", "var", "desconhecido") and not self._is_type_variable(op_type):
                self.errors.append(
                    SemanticError(
                        f"Operador '{node.op}' requer operando numérico (encontrado '{op_type}' — JLS §15.14 / §15.15).",
                        line,
                    )
                )
            return

        if node.op == "-" and isinstance(node.operand, Literal) and not getattr(node.operand, "parenthesized", False):
            self._validate_numeric_literal(node.operand, negated=True)
        else:
            self._check_expression_flow(node.operand)
        op_type = self.infer_type(node.operand)
        if not op_type or op_type in ("Object", "var", "desconhecido") or self._is_type_variable(op_type):
            return
        if node.op == "!":
            if not self._is_boolean_type(op_type):
                self.errors.append(
                    SemanticError(f"Operador lógico '!' requer operando 'boolean' (encontrado '{op_type}' — JLS §15.15.6).", line)
                )
        elif node.op == "~":
            if not self._is_integral_type(op_type):
                self.errors.append(
                    SemanticError(f"Operador bit-a-bit '~' requer tipo integral (encontrado '{op_type}' — JLS §15.15.5).", line)
                )
        elif node.op in ("+", "-"):
            if self._unboxed_numeric(op_type) is None:
                self.errors.append(
                    SemanticError(f"Operador unário '{node.op}' requer tipo numérico (encontrado '{op_type}' — JLS §15.15.3).", line)
                )

    def _validate_binary_op(self, node: BinaryOp):
        """Valida compatibilidade de tipos e promoções em operadores binários (JLS §15.17–§15.24)."""
        line = getattr(node, "line", 1)
        left_t = self.infer_type(node.left)
        right_t = self.infer_type(node.right)
        if not left_t or not right_t:
            return
        if any(t in ("Object", "var", "desconhecido") or self._is_type_variable(t) for t in (left_t, right_t)):
            # Se for operação numérica óbvia com String ou boolean contra desconhecido, ainda valida o lado conhecido
            if node.op in ("-", "*", "/", "%") and ("String" in (left_t, right_t) or "boolean" in (left_t, right_t)):
                pass
            elif node.op in ("<", "<=", ">", ">=", "<<", ">>", ">>>") and (self._is_boolean_type(left_t) or self._is_boolean_type(right_t) or "String" in (left_t, right_t)):
                pass
            else:
                return

        if node.op in ("+", "-", "*", "/", "%"):
            if node.op == "+" and (left_t == "String" or right_t == "String"):
                return
            if left_t == "String" or right_t == "String":
                self.errors.append(
                    SemanticError(
                        f"Operação aritmética '{node.op}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                        line,
                    )
                )
                return
            if self._unboxed_numeric(left_t) is None or self._unboxed_numeric(right_t) is None:
                self.errors.append(
                    SemanticError(
                        f"Operação aritmética '{node.op}' inválida entre tipos '{left_t}' e '{right_t}'.",
                        line,
                    )
                )
            return

        if node.op in ("<<", ">>", ">>>"):
            if not self._is_integral_type(left_t) or not self._is_integral_type(right_t):
                self.errors.append(
                    SemanticError(
                        f"Operador de deslocamento '{node.op}' exige operandos de tipos integrais (encontrado '{left_t}' e '{right_t}' — JLS §15.19).",
                        line,
                    )
                )
            return

        if node.op in ("<", "<=", ">", ">="):
            if self._unboxed_numeric(left_t) is None or self._unboxed_numeric(right_t) is None:
                self.errors.append(
                    SemanticError(
                        f"Operador relacional '{node.op}' requer operandos numéricos (encontrado '{left_t}' e '{right_t}' — JLS §15.20.1).",
                        line,
                    )
                )
            return

        if node.op in ("&", "|", "^"):
            both_int = self._is_integral_type(left_t) and self._is_integral_type(right_t)
            both_bool = self._is_boolean_type(left_t) and self._is_boolean_type(right_t)
            if not both_int and not both_bool:
                self.errors.append(
                    SemanticError(
                        f"Operador '{node.op}' exige ambos os operandos integrais ou ambos booleanos (encontrado '{left_t}' e '{right_t}' — JLS §15.22).",
                        line,
                    )
                )
            return

        if node.op in ("&&", "||"):
            if not self._is_boolean_type(left_t) or not self._is_boolean_type(right_t):
                self.errors.append(
                    SemanticError(
                        f"Operador lógico '{node.op}' requer operandos de tipo 'boolean' (encontrado '{left_t}' e '{right_t}' — JLS §15.23 / §15.24).",
                        line,
                    )
                )
            return

        if node.op in ("==", "!="):
            both_num = self._unboxed_numeric(left_t) is not None and self._unboxed_numeric(right_t) is not None
            both_bool = self._is_boolean_type(left_t) and self._is_boolean_type(right_t)
            if both_num or both_bool:
                return
            if "null" in (left_t, right_t):
                other = right_t if left_t == "null" else left_t
                if other in self.PRIMITIVE_TYPES:
                    self.errors.append(
                        SemanticError(f"Operação '{node.op}' inválida entre '{left_t}' e '{right_t}' (JLS §15.21).", line)
                    )
                return
            if (left_t in self.PRIMITIVE_TYPES) != (right_t in self.PRIMITIVE_TYPES):
                self.errors.append(
                    SemanticError(f"Operação '{node.op}' inválida entre tipos incomparáveis '{left_t}' e '{right_t}' (JLS §15.21).", line)
                )
                return
            if left_t in self.PRIMITIVE_TYPES and right_t in self.PRIMITIVE_TYPES:
                self.errors.append(
                    SemanticError(f"Operação '{node.op}' inválida entre '{left_t}' e '{right_t}' (JLS §15.21).", line)
                )
                return
            if self._are_types_disjoint(left_t, right_t) is True:
                self.errors.append(
                    SemanticError(f"Operandos incompatíveis em '{node.op}': '{left_t}' e '{right_t}' não são comparáveis (JLS §15.21.3).", line)
                )

    def _is_poly_expression(self, node: Optional[ASTNode]) -> bool:
        """Indica se a expressão é poly e depende de tipo alvo para inferência completa."""
        if node is None:
            return False
        if isinstance(node, (LambdaExpression, MethodReference)):
            return True
        if isinstance(node, ObjectCreationExpression) and getattr(node, "is_diamond", False):
            return False  # `var x = new ArrayList<>()` é permitido com <> (infere ArrayList<Object>)
        if isinstance(node, ConditionalExpression):
            return self._is_poly_expression(node.then_expr) or self._is_poly_expression(node.else_expr)
        return False

    def _unify_branch_types(self, expr_nodes: List[ASTNode], target_type: Optional[str] = None) -> Optional[str]:
        """Unifica os tipos resultantes de múltiplos ramos de switch expression ou array initializer."""
        if not expr_nodes:
            return target_type
        if target_type and target_type not in ("var", "desconhecido"):
            return target_type
        acc: Optional[str] = None
        for expr in expr_nodes:
            et = self.infer_type(expr)
            if et is None:
                continue
            if acc is None:
                acc = et
            else:
                acc = self._lub_type(acc, et)
        return acc

    def _check_array_initializer_compatible(self, elem_expected: str, init_node: ArrayInitializer, line: int):
        """Valida recursivamente inicializadores de array contra o tipo de elemento esperado."""
        for elem in init_node.elements:
            if isinstance(elem, ArrayInitializer):
                if elem_expected.endswith("[]"):
                    self._check_array_initializer_compatible(elem_expected[:-2], elem, getattr(elem, "line", line))
                else:
                    self.errors.append(
                        SemanticError(f"Inicializador de array aninhado incompatível com o tipo '{elem_expected}'.", getattr(elem, "line", line))
                    )
            else:
                self._check_expression_with_target(elem, elem_expected)
                if not self._is_assignable_expr(elem_expected, elem):
                    et = self.infer_type(elem)
                    self.errors.append(
                        SemanticError(
                            f"Elemento de tipo '{et}' incompatível em inicializador de array de '{elem_expected}' (JLS §10.6).",
                            getattr(elem, "line", line),
                        )
                    )

    def _check_expression_with_target(self, node: Optional[ASTNode], target_type: Optional[str] = None) -> "_FlowResult":
        """Analisa uma expressão propagando o tipo alvo (target typing) quando aplicável."""
        if node is None:
            return self._FlowResult()
        if isinstance(node, LambdaExpression):
            self._check_lambda_with_target(node, target_type)
            return self._FlowResult()
        if isinstance(node, MethodReference):
            self._check_method_ref_with_target(node, target_type)
            return self._FlowResult()
        if isinstance(node, ArrayInitializer):
            if target_type and target_type.endswith("[]"):
                self._check_array_initializer_compatible(target_type[:-2], node, getattr(node, "line", 1))
            else:
                for elem in node.elements:
                    self._check_expression_flow(elem)
            if target_type:
                self._inferred_types[id(node)] = target_type
            return self._FlowResult()
        if isinstance(node, ConditionalExpression):
            fc = self._check_expression_flow(node.condition)
            cond_t = self.infer_type(node.condition)
            if cond_t is not None and not self._is_boolean_type(cond_t) and cond_t not in ("Object", "var", "desconhecido") and not self._is_type_variable(cond_t):
                self.errors.append(
                    SemanticError(
                        f"Condição do operador ternário '?:' deve possuir tipo 'boolean' (encontrado '{cond_t}' — JLS §15.25).",
                        getattr(node, "line", 1),
                    )
                )
            cur_snap = self._flow_snapshot()
            ct = fc.true_state if fc.true_state is not None else cur_snap
            cf = fc.false_state if fc.false_state is not None else cur_snap
            c_val = self._eval_constant_boolean(node.condition)
            if c_val is True:
                cf = self._flow_unreachable()
            elif c_val is False:
                ct = self._flow_unreachable()

            self._flow_restore(ct)
            self._push_pattern_scope(fc.true_vars)
            try:
                ft = self._check_expression_with_target(node.then_expr, target_type)
                then_post = self._flow_snapshot()
            finally:
                self._pop_pattern_scope()

            self._flow_restore(cf)
            self._push_pattern_scope(fc.false_vars)
            try:
                fe = self._check_expression_with_target(node.else_expr, target_type)
                else_post = self._flow_snapshot()
            finally:
                self._pop_pattern_scope()

            ft_true = ft.true_state if ft.true_state is not None else then_post
            ft_false = ft.false_state if ft.false_state is not None else then_post
            fe_true = fe.true_state if fe.true_state is not None else else_post
            fe_false = fe.false_state if fe.false_state is not None else else_post
            out_true_st = self._flow_join_states(ft_true, fe_true)
            out_false_st = self._flow_join_states(ft_false, fe_false)
            self._flow_restore(self._flow_join_states(then_post, else_post))

            if target_type and target_type not in ("var", "desconhecido"):
                self._inferred_types[id(node)] = target_type
            left_true = {**fc.true_vars, **ft.true_vars}
            right_true = {**fc.false_vars, **fe.true_vars}
            out_true = {k: v for k, v in left_true.items() if k in right_true}
            left_false = {**fc.true_vars, **ft.false_vars}
            right_false = {**fc.false_vars, **fe.false_vars}
            out_false = {k: v for k, v in left_false.items() if k in right_false}
            return self._FlowResult(out_true, out_false, out_true_st, out_false_st)
        if isinstance(node, SwitchExpression):
            saved_ctx = self._enter_exec_context(
                "switch_expression",
                return_type=self._current_return_type,
                share_locals=True,
                switch_expr_depth=self._switch_expr_depth + 1,
            )
            self._switch_expected_type_stack.append(target_type)
            try:
                self._analyze_switch_block(node, is_expression=True, expected_type=target_type)
            finally:
                self._switch_expected_type_stack.pop()
                self._restore_exec_context(saved_ctx)
            return self._FlowResult()
        if isinstance(node, ObjectCreationExpression):
            return self._check_object_creation(node, target_type=target_type)
        if isinstance(node, MethodCall):
            return self._check_method_call(node, target_type=target_type)
        return self._check_expression_flow(node)

    def _check_array_component_reifiable(self, type_ref: Optional[ASTNode], line: int, context_desc: str) -> None:
        """Valida que o tipo componente de criação de array é reificável segundo JLS §4.7 / §15.10.1."""
        if not isinstance(type_ref, TypeReference):
            return
        tname = getattr(type_ref, "name", "") or ""
        if not tname or tname in self.PRIMITIVE_TYPES or tname == "void":
            return

        # 1. Variável de tipo em escopo não é reificável: new T[...], T[]::new
        if "." not in tname and self._lookup_type_param_bounds(tname) is not None:
            self.errors.append(
                SemanticError(
                    f"Criação de array genérico inválido em {context_desc}: variável de tipo '{tname}' não é reificável (JLS §4.7 / §15.10.1).",
                    line,
                )
            )
            return

        # 2. Tipo parametrizado só é reificável se todos os argumentos em todos os segmentos forem wildcards não limitados '?'
        seg_targs = getattr(type_ref, "segment_type_arguments", None) or []
        has_segment_args = any(sa is not None for sa in seg_targs)
        arg_lists = [sa for sa in seg_targs if sa] if has_segment_args else (
            [type_ref.type_arguments] if getattr(type_ref, "type_arguments", None) else []
        )
        for arg_list in arg_lists:
            for arg in arg_list:
                if isinstance(arg, WildcardType) and arg.bound_kind is None and arg.bound_type is None:
                    continue
                norm = self._normalize_type_str(type_ref) or tname
                self.errors.append(
                    SemanticError(
                        f"Criação de array genérico inválido com tipo não reificável '{norm}' em {context_desc} (JLS §4.7 / §15.10.1).",
                        line,
                    )
                )
                return

    def _resolve_inherited_member_type(self, owner_key: Optional[str], member_name: str) -> Optional[str]:
        """Resolve tipo membro declarado em supertipos de `owner_key` (para `expr.new Inner()` ou herança)."""
        if not owner_key or not member_name or "." in member_name:
            return None
        if getattr(self, "_in_member_type_lookup", False):
            return None
        self._in_member_type_lookup = True
        try:
            visited: Set[str] = set()
            queue: List[str] = [owner_key]
            while queue:
                cur = queue.pop(0)
                cur_base = self._strip_generics(cur) or cur
                cur_key = (
                    cur_base
                    if cur_base in self._inheritance_analyzer._type_meta
                    else (self._inheritance_analyzer.resolve_type_key(cur_base) or cur_base)
                )
                if not cur_key or cur_key in visited:
                    continue
                visited.add(cur_key)
                cand = f"{cur_key}.{member_name}"
                if cand in self._inheritance_analyzer._type_meta:
                    return cand
                if self._resolve_external_type(cand) is not None:
                    return cand
                supers, _ = self._direct_supertypes(cur_key)
                queue.extend(supers)
            return None
        finally:
            self._in_member_type_lookup = False

    def _requires_enclosing_instance(self, type_name_or_key: Optional[str]) -> Optional[str]:
        """Retorna a chave da classe envolvente exigida por inner class não-static, ou None (JLS §8.1.3 / §15.9.2)."""
        if not type_name_or_key:
            return None
        meta = self._inheritance_analyzer.get_type_meta(type_name_or_key)
        if meta is not None:
            if meta.get("is_local"):
                return None
            if not meta.get("is_nested") or meta.get("kind") != "class":
                return None
            if "static" in (meta.get("modifiers") or []):
                return None
            enc_key = meta.get("enclosing_key")
            if not enc_key:
                return None
            enc_meta = self._inheritance_analyzer.get_type_meta(enc_key)
            if enc_meta is not None and enc_meta.get("kind") in ("interface", "annotation_interface"):
                return None
            return enc_key
        ext = self._resolve_external_type(type_name_or_key)
        if ext is not None:
            if not ext.is_nested or ext.kind != "class":
                return None
            if "static" in (ext.modifiers or []) or not ext.enclosing_fqn:
                return None
            enc_ext = self._resolve_external_type(ext.enclosing_fqn)
            if enc_ext is not None and enc_ext.kind in ("interface", "annotation_interface"):
                return None
            return ext.enclosing_fqn
        return None

    def _available_enclosing_instance_types(self) -> List[str]:
        """Lista os tipos envolventes com instância ativa alcançável no escopo léxico atual (JLS §15.9.2)."""
        if self._in_static_context or self._in_early_construction_context or self._anon_enclosing_blocked:
            return []
        keys = list(self._inheritance_analyzer._enclosing_type_keys)
        avail: List[str] = []
        for idx in range(len(keys) - 1, -1, -1):
            k = keys[idx]
            avail.append(k)
            if k in self._static_context_local_keys:
                break
            meta = self._inheritance_analyzer._type_meta.get(k)
            if meta is not None:
                if "static" in (meta.get("modifiers") or []):
                    break
                if meta.get("kind") in ("interface", "annotation_interface", "enum", "record") and meta.get("is_nested"):
                    break
        return avail

    def _check_object_creation(self, node: ObjectCreationExpression, target_type: Optional[str] = None) -> "_FlowResult":
        """Valida criação de objetos, construtores, diamond <>, classe anônima e abstrata/interface."""
        line = getattr(node, "line", 1)
        tref = getattr(node, "type_ref", None)
        base_name = getattr(tref, "name", None) or getattr(node, "class_name", "")
        full_name = self._normalize_type_str(tref) or base_name
        has_qual_target = getattr(node, "target", None) is not None
        self._check_type_ref_annotations(tref, skip_type_access=has_qual_target, skip_arity=has_qual_target)
        resolved_unqual = self._inheritance_analyzer.resolve_type_key(base_name)
        qual_lookup_name = (
            resolved_unqual
            if (resolved_unqual and resolved_unqual in self._inheritance_analyzer._type_meta)
            else base_name
        )
        outer_subst: Optional[Dict[str, str]] = None
        if has_qual_target:
            self._check_expression_flow(node.target)
            outer_t = self.infer_type(node.target)
            if outer_t:
                outer_subst = self._type_var_mapping_for_type(outer_t) or None
                outer_base = self._strip_generics(outer_t) or outer_t
                outer_key = self._inheritance_analyzer.resolve_type_key(outer_base) or outer_base
                candidate_inner = f"{outer_key}.{base_name}"
                resolved_inner = self._inheritance_analyzer.resolve_type_key(candidate_inner)
                if resolved_inner is None:
                    resolved_inner = self._resolve_inherited_member_type(outer_key, base_name)
                qual_lookup_name = resolved_inner or candidate_inner
            self._inheritance_analyzer.check_type_access(qual_lookup_name, line)
            self._check_type_ref_arity(tref, resolved_name_override=qual_lookup_name)
            self._check_type_ref_bounds(tref, resolved_name_override=qual_lookup_name, outer_subst=outer_subst)

        req_enclosing = self._requires_enclosing_instance(qual_lookup_name)
        target_meta = self._inheritance_analyzer.get_type_meta(qual_lookup_name)
        if has_qual_target:
            if target_meta is not None and target_meta.get("is_local"):
                self.errors.append(
                    SemanticError(
                        f"Não é possível qualificar a instanciação da classe local '{base_name}' (JLS §15.9).",
                        line,
                    )
                )
            elif req_enclosing is None and (target_meta is not None or self._resolve_external_type(qual_lookup_name) is not None):
                self.errors.append(
                    SemanticError(
                        f"Instanciação qualificada '{base_name}' inválida: '{qual_lookup_name}' não é uma classe interna de instância (JLS §15.9).",
                        line,
                    )
                )
        elif req_enclosing is not None:
            avail_enclosing = self._available_enclosing_instance_types()
            has_enclosing_inst = any(
                avail == req_enclosing or self._is_subtype(avail, req_enclosing) is True
                for avail in avail_enclosing
            )
            if not has_enclosing_inst:
                self.errors.append(
                    SemanticError(
                        f"Não é possível instanciar a classe interna não-estática '{base_name}' sem uma instância externa válida de '{req_enclosing}' (JLS §15.9.2).",
                        line,
                    )
                )
        is_diamond = bool(getattr(node, "is_diamond", False))
        anon_body = getattr(node, "anonymous_body", None)

        effective_created_type = qual_lookup_name if (has_qual_target and qual_lookup_name != base_name) else full_name
        diamond_decls = self._type_param_decls_for_type(qual_lookup_name) if is_diamond else []
        diamond_expected_target = (
            target_type
            if (is_diamond and target_type and target_type not in ("var", "desconhecido"))
            else None
        )
        if is_diamond and diamond_expected_target and not diamond_decls:
            _, target_args, _ = self._extract_generic_args(diamond_expected_target)
            if target_args:
                concrete_dargs: List[str] = []
                for ta in target_args:
                    wkind, wbound = self._parse_wildcard_arg(ta)
                    if wkind == "unbounded":
                        concrete_dargs.append("Object")
                    elif wkind in ("extends", "super") and wbound:
                        concrete_dargs.append(wbound)
                    else:
                        concrete_dargs.append(ta)
                simple_base = self._simple_base_name(base_name) or base_name
                effective_created_type = f"{simple_base}<{', '.join(concrete_dargs)}>"

        ctors_lookup_type = qual_lookup_name if (is_diamond and diamond_decls) else effective_created_type
        ctors, is_known_c, tkind = self._collect_type_constructors(ctors_lookup_type)
        if is_diamond and diamond_decls and ctors:
            class_tparams = [pname for pname, _ in diamond_decls]
            class_bounds = {pname: list(bs) for pname, bs in diamond_decls}
            simple_base = self._simple_base_name(base_name) or base_name
            diamond_ret = f"{simple_base}<{', '.join(class_tparams)}>"
            diamond_ctors: List[Dict[str, Any]] = []
            for c in ctors:
                dc = dict(c)
                dc["tparams"] = class_tparams + list(c.get("tparams", []) or [])
                merged_bounds = dict(class_bounds)
                merged_bounds.update(c.get("tparam_bounds", {}) or {})
                dc["tparam_bounds"] = merged_bounds
                dc["ret"] = diamond_ret
                diamond_ctors.append(dc)
            ctors = diamond_ctors
        tdecl = self._lookup_type_decl(qual_lookup_name)
        if tdecl is not None:
            dkind, dnode = tdecl
            mods = getattr(dnode, "modifiers", [])
            if dkind == "enum":
                self.errors.append(
                    SemanticError(f"Tipo enum '{base_name}' não pode ser instanciado com 'new' (JLS §8.9).", line)
                )
            elif dkind in ("interface", "annotation_interface") and anon_body is None:
                self.errors.append(
                    SemanticError(f"Não é possível instanciar interface '{base_name}' diretamente sem corpo de classe anônima (JLS §15.9).", line)
                )
            elif dkind == "class" and "abstract" in mods and anon_body is None:
                self.errors.append(
                    SemanticError(f"Não é possível instanciar classe abstrata '{base_name}' sem corpo de classe anônima (JLS §15.9.1).", line)
                )
            elif anon_body is not None and ("final" in mods or dkind in ("record", "enum")):
                self.errors.append(
                    SemanticError(f"Não é possível criar classe anônima estendendo tipo fechado/final '{base_name}' (JLS §15.9.5).", line)
                )
        elif anon_body is None and tkind == "interface":
            self.errors.append(
                SemanticError(f"Não é possível instanciar interface '{base_name}' diretamente sem corpo de classe anônima (JLS §15.9).", line)
            )
        elif anon_body is None and tkind == "annotation_interface":
            self.errors.append(
                SemanticError(f"Não é possível instanciar interface de anotação '{base_name}' diretamente (JLS §15.9).", line)
            )
        else:
            ext_created = self._resolve_external_type(qual_lookup_name)
            if ext_created is not None:
                if ext_created.kind == "enum":
                    self.errors.append(
                        SemanticError(f"Tipo enum '{base_name}' não pode ser instanciado com 'new' (JLS §8.9).", line)
                    )
                elif ext_created.kind == "class" and ext_created.is_abstract and anon_body is None:
                    self.errors.append(
                        SemanticError(f"Não é possível instanciar classe abstrata '{base_name}' sem corpo de classe anônima (JLS §15.9.1).", line)
                    )
                elif anon_body is not None and (ext_created.is_final or ext_created.kind in ("record", "enum")):
                    self.errors.append(
                        SemanticError(f"Não é possível criar classe anônima estendendo tipo fechado/final '{base_name}' (JLS §15.9.5).", line)
                    )
            elif anon_body is not None and self._simple_base_name(base_name) in self.BUILTIN_FINAL_TYPES:
                self.errors.append(
                    SemanticError(f"Não é possível estender classe final '{base_name}' em classe anônima (JLS §15.9.5).", line)
                )

        # Se há lambdas nos argumentos, checa usando parâmetros do construtor quando houver candidato compatível
        win_ctor_sig = None
        if ctors:
            expected_ctor_ret = diamond_expected_target if (is_diamond and diamond_decls) else effective_created_type
            win_ctor_sig, inf_ctor_ret, bound_params = self._resolve_overload(
                ctors,
                list(node.arguments),
                line,
                f"new {base_name}(...)",
                expected_return=expected_ctor_ret,
            )
            if is_diamond and diamond_decls and inf_ctor_ret and "<" in inf_ctor_ret:
                effective_created_type = inf_ctor_ret
                _, inf_dargs, _ = self._extract_generic_args(inf_ctor_ret)
                if inf_dargs:
                    self._validate_type_args_against_bounds(qual_lookup_name, inf_dargs, line)
            for idx, arg in enumerate(node.arguments):
                pt = bound_params.get(idx) if bound_params else None
                self._check_expression_with_target(arg, pt)
        else:
            if not is_known_c:
                self._record_unresolved(f"Construtor do tipo externo '{effective_created_type}' não consta nas assinaturas embutidas/externas.")
                self._exception_analyzer.mark_unresolved_thrower()
            for arg in node.arguments:
                self._check_expression_flow(arg)

        if win_ctor_sig is not None:
            ctor_owner = win_ctor_sig.get("owner_key") or win_ctor_sig.get("owner") or base_name
            self._inheritance_analyzer.check_member_access(
                ctor_owner,
                win_ctor_sig.get("access", "public"),
                False,
                "construtor",
                self._simple_base_name(base_name) or base_name,
                line,
                is_anon_ctor=(anon_body is not None),
            )
            self._exception_analyzer.emit_thrown(
                win_ctor_sig.get("throws", []),
                line,
                f"construtor 'new {base_name}(...)'",
            )

        if anon_body is not None:
            anon_inst_throws: List[Tuple[str, int, str]] = []
            anon_super_key = self._inheritance_analyzer.resolve_type_key(base_name) or base_name
            self.symbols.enter_scope()
            next_anon_blocked = bool(self._in_static_context or self._in_early_construction_context or self._anon_enclosing_blocked)
            saved_ctx = self._enter_exec_context("type_body", return_type=None, share_locals=True)
            self._anon_enclosing_blocked = next_anon_blocked
            try:
                self._analyze_class_like_members(
                    anon_body,
                    container_label="classe anônima",
                    enclosing_name=f"<anonymous {base_name}>",
                    allow_constructor=False,
                    is_enum=False,
                    anon_inst_throws=anon_inst_throws,
                    anon_super_type=anon_super_key,
                    owner_kind="class",
                    owner_modifiers=[],
                    owner_line=line,
                )
            finally:
                self._restore_exec_context(saved_ctx)
                self.symbols.exit_scope()
            for a_exc_t, a_exc_ln, a_exc_desc in anon_inst_throws:
                self._exception_analyzer.emit_thrown([a_exc_t], a_exc_ln, a_exc_desc)

        self._inferred_types[id(node)] = effective_created_type
        return self._FlowResult()

    def _check_method_call(self, node: MethodCall, target_type: Optional[str] = None) -> "_FlowResult":
        """Valida invocação de método com resolução estática/instância, sobrecarga em 3 fases e target typing."""
        line = getattr(node, "line", 1)
        mname = node.method_name
        raw_targ_nodes = getattr(node, "type_arguments", []) or []
        for targ_node in raw_targ_nodes:
            self._check_type_ref_annotations(targ_node)
        explicit_targs = [self._normalize_type_str(t) or "Object" for t in raw_targ_nodes]

        recv_type: Optional[str] = None
        recv_is_type = False
        is_unqualified = node.target is None
        via_super = False
        via_iface_super = False

        if node.target is not None:
            qname = self._extract_qualified_name(node.target)
            if isinstance(node.target, MemberAccess) and node.target.member_name == "super":
                via_super = True
                self._check_early_target_ref(
                    "super",
                    line,
                    f"Invocação inválida de método via 'super' ('{mname}(...)')",
                )
                if self._in_static_context:
                    self.errors.append(
                        SemanticError(f"Não é possível usar 'super' em contexto estático ao invocar '{mname}(...)' (JLS §15.12.3).", line)
                    )
                qual_name = self._extract_qualified_name(node.target.target)
                if qual_name:
                    self._inheritance_analyzer.check_type_access(qual_name, line)
                    resolved_q = self._inheritance_analyzer.resolve_type_key(qual_name) or qual_name
                    qdecl = self._lookup_type_decl(resolved_q)
                    if qdecl is not None and qdecl[0] == "interface":
                        via_iface_super = True
                        self._inheritance_analyzer.validate_interface_super_call(resolved_q, mname, line)
                        recv_type = resolved_q
                    else:
                        supers, _ = self._direct_supertypes(resolved_q)
                        recv_type = supers[0] if supers else "Object"
            elif qname and (
                self._is_known_type(qname)
                or (qname.split(".")[-1][0].isupper() and self._lookup_var_symbol(qname.split(".")[0]) is None)
            ):
                recv_type = qname
                recv_is_type = True
                self._inheritance_analyzer.check_type_access(qname, line)
            elif isinstance(node.target, Identifier) and node.target.name in ("this", "super"):
                self._check_early_target_ref(
                    node.target.name,
                    line,
                    f"Invocação inválida de método via '{node.target.name}' ('{node.target.name}.{mname}(...)')",
                )
                cur = self._inheritance_analyzer.current_enclosing_key() or self._current_enclosing_type()
                if node.target.name == "this":
                    if self._in_static_context:
                        self.errors.append(
                            SemanticError(f"Não é possível usar 'this' em contexto estático ao invocar '{mname}(...)' (JLS §15.8.3).", line)
                        )
                    recv_type = cur
                else:
                    via_super = True
                    if self._in_static_context:
                        self.errors.append(
                            SemanticError(f"Não é possível usar 'super' em contexto estático ao invocar '{mname}(...)' (JLS §15.8.3).", line)
                        )
                    if cur:
                        supers, _ = self._direct_supertypes(cur)
                        recv_type = supers[0] if supers else "Object"
            elif isinstance(node.target, Identifier):
                sym = self._lookup_var_symbol(node.target.name)
                if sym is not None and sym.get("category") not in self.TYPE_SYMBOL_CATEGORIES and sym.get("category") is not None:
                    recv_type = sym.get("type")
                    self._check_expression_flow(node.target)
                elif self._is_known_type(node.target.name):
                    recv_type = node.target.name
                    recv_is_type = True
                    self._inheritance_analyzer.check_type_access(recv_type, line)
                elif node.target.name[0].isupper():
                    # Tipo externo importado / java.lang não pré-cadastrado
                    recv_type = node.target.name
                    recv_is_type = True
                else:
                    self._check_expression_flow(node.target)
                    recv_type = self.infer_type(node.target)
            else:
                self._check_expression_flow(node.target)
                recv_type = self.infer_type(node.target)
        else:
            if self._in_early_construction_context:
                sym = self.symbols.lookup(mname)
                if sym is not None and sym.get("category") == "metodo" and not sym.get("is_static", False):
                    self.errors.append(
                        SemanticError(
                            f"Invocação inválida de método de instância '{mname}(...)' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513).",
                            line,
                        )
                    )
            recv_type = self._inheritance_analyzer.current_enclosing_key() or self._current_enclosing_type()

        # Primeiro avalia argumentos não-poly para ter tipos durante a seleção de sobrecarga
        deferred_indices: Set[int] = set()
        for idx, arg in enumerate(node.arguments):
            if self._is_deferred_poly_call_arg(arg):
                deferred_indices.add(idx)
            else:
                self._check_expression_flow(arg)

        if not recv_type:
            for arg in node.arguments:
                if isinstance(arg, (LambdaExpression, MethodReference)):
                    self._check_expression_flow(arg)
            self._record_unresolved(f"Invocação '{mname}(...)' sobre tipo ou receptor externo não resolvido.")
            self._exception_analyzer.mark_unresolved_thrower()
            return self._FlowResult()

        recv_simple = self._simple_base_name(recv_type) or recv_type
        if recv_simple in self.PRIMITIVE_TYPES or recv_simple in ("void", "null"):
            for arg in node.arguments:
                if isinstance(arg, (LambdaExpression, MethodReference)):
                    self._check_expression_flow(arg)
            self.errors.append(
                SemanticError(
                    f"Não é possível invocar o método '{mname}(...)' sobre expressão do tipo '{recv_type}' (JLS §15.12).",
                    line,
                )
            )
            return self._FlowResult()

        if recv_type.endswith("[]") and mname == "length":
            for arg in node.arguments:
                if isinstance(arg, (LambdaExpression, MethodReference)):
                    self._check_expression_flow(arg)
            self.errors.append(
                SemanticError(
                    "'length' em arrays é um campo final, não um método invocável (use '.length' — JLS §10.7).",
                    line,
                )
            )
            return self._FlowResult()

        if not recv_is_type:
            recv_type = self._capture_convert(recv_type) or recv_type
        methods, is_known_m, is_declared = self._collect_type_methods(recv_type, mname)
        if not methods:
            for arg in node.arguments:
                if isinstance(arg, (LambdaExpression, MethodReference)):
                    self._check_expression_flow(arg)
            if is_unqualified and (mname in self._static_imports or self._has_wildcard_static_import):
                self._record_unresolved(f"Invocação '{mname}(...)' originada de import estático externo.")
                self._exception_analyzer.mark_unresolved_thrower()
                return self._FlowResult()
            if is_declared and is_known_m:
                self.errors.append(
                    SemanticError(
                        f"Método '{mname}' não encontrado no tipo '{recv_type}' ou supertipos (JLS §15.12.1).",
                        line,
                    )
                )
            else:
                self._record_unresolved(f"Método '{mname}' no tipo '{recv_type}' não consta nas assinaturas embutidas/externas.")
                self._exception_analyzer.mark_unresolved_thrower()
            return self._FlowResult()

        if recv_is_type:
            static_only = [m for m in methods if m["static"]]
            if not static_only:
                if not is_declared and not is_known_m:
                    self._record_unresolved(f"Método estático '{mname}' no tipo externo '{recv_type}' não resolvido.")
                    self._exception_analyzer.mark_unresolved_thrower()
                    return self._FlowResult()
                self.errors.append(
                    SemanticError(
                        f"Método de instância '{mname}' não pode ser referenciado a partir do contexto estático '{recv_type}.{mname}(...)' (JLS §15.12.3).",
                        line,
                    )
                )
                return self._FlowResult()
            methods = static_only
        elif is_unqualified and self._in_static_context:
            static_only = [m for m in methods if m["static"]]
            if not static_only and methods:
                self.errors.append(
                    SemanticError(
                        f"Não é possível referenciar o método não-estático '{mname}' a partir de um contexto estático (JLS §15.12.3).",
                        line,
                    )
                )
                return self._FlowResult()

        win_sig, eff_ret, bound_params = self._resolve_overload(
            methods,
            list(node.arguments),
            line,
            f"{recv_type}.{mname}(...)",
            expected_return=target_type,
            explicit_targs=explicit_targs,
        )
        for idx, arg in enumerate(node.arguments):
            if idx in deferred_indices:
                pt = bound_params.get(idx) if bound_params else None
                self._check_expression_with_target(arg, pt)
            elif isinstance(arg, (ConditionalExpression, SwitchExpression)):
                pt = bound_params.get(idx) if bound_params else None
                saved_flow = self._flow_snapshot()
                saved_sup = self._flow_suppress_errors
                saved_flags = self._snapshot_local_var_flags()
                self._flow_suppress_errors = True
                try:
                    self._check_expression_with_target(arg, pt)
                finally:
                    self._flow_suppress_errors = saved_sup
                    self._flow_restore(saved_flow)
                    self._restore_local_var_flags(saved_flags)
        if win_sig is not None:
            if via_super and win_sig.get("is_abstract", False) and not win_sig.get("is_default", False) and not via_iface_super:
                self.errors.append(
                    SemanticError(f"Não é possível invocar diretamente o método abstrato '{mname}(...)' via 'super' (JLS §15.12.3).", line)
                )
            eff_recv_for_access = None if (
                recv_is_type
                or via_super
                or is_unqualified
                or (isinstance(node.target, Identifier) and node.target.name == "this")
            ) else recv_type
            self._inheritance_analyzer.check_member_access(
                win_sig.get("owner_key") or win_sig.get("owner") or recv_type,
                win_sig.get("access", "public"),
                bool(win_sig.get("static", False)),
                "método",
                mname,
                line,
                receiver_type=eff_recv_for_access,
                via_super=via_super,
            )
            self._exception_analyzer.emit_thrown(
                win_sig.get("throws", []),
                line,
                f"chamada '{recv_type}.{mname}(...)'",
            )
        if eff_ret:
            self._inferred_types[id(node)] = eff_ret
        return self._FlowResult()


    def _check_early_target_ref(self, target_name: str, line: int, context_detail: str = "") -> bool:
        """Verifica se há uso inválido de 'this' ou 'super' durante o early construction context (JLS §8.8.7 / JEP 513)."""
        if not self._in_early_construction_context:
            return False
        for kw in ("this", "super"):
            if target_name == kw or target_name.startswith(f"{kw}."):
                msg = (
                    f"{context_detail} antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513)."
                    if context_detail
                    else f"Uso inválido de '{kw}' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513)."
                )
                self.errors.append(SemanticError(msg, line))
                return True
        return False

    def _check_assignment(self, node: Assignment) -> "_FlowResult":
        """Valida uma atribuição (instrução ou expressão), alvo modificável, operadores compostos e target typing."""
        line = getattr(node, "line", 1)
        op = getattr(node, "operator", "=")
        is_this_member_assign = (
            (node.name and node.name.startswith("this."))
            or (
                isinstance(node.target, MemberAccess)
                and isinstance(node.target.target, Identifier)
                and node.target.target.name == "this"
            )
        )
        if self._in_compact_constructor and is_this_member_assign:
            self.errors.append(
                SemanticError(
                    "Construtor compacto de record não pode atribuir campos de instância diretamente usando 'this.' (JLS §8.10.4.2).",
                    line,
                )
            )
            self.check_expression(node.expression)
            return self._FlowResult()

        if node.target is not None and not isinstance(node.target, Identifier):
            is_simple = (op == "=")
            if not is_simple and isinstance(node.target, MemberAccess) and isinstance(node.target.target, Identifier) and node.target.target.name == "this":
                self._flow_check_read(node.target.member_name, line, is_this_qualified=True)
            ok, target_type = self._is_modifiable_lvalue(
                node.target,
                node.name,
                line,
                f"atribuição '{op}'",
                defer_flow_write=True,
                defer_member_read=is_simple,
            )
            if is_simple and target_type:
                rhs_flow = self._check_expression_with_target(node.expression, target_type)
            else:
                rhs_flow = self._check_expression_flow(node.expression)
            if isinstance(node.target, MemberAccess) and isinstance(node.target.target, Identifier) and node.target.target.name == "this":
                self._flow_apply_local_write(
                    node.target.member_name,
                    line,
                    is_compound=not is_simple,
                    is_this_qualified=True,
                )
            if ok and target_type:
                label = node.name or (node.target.pretty() if hasattr(node.target, "pretty") else "alvo")
                self.check_assignment_type(target_type, node.expression, label, line, operator=op)
            return rhs_flow

        if node.name and (node.name.startswith(("this.", "super.")) or node.name in ("this", "super")):
            self._check_early_target_ref(node.name, line)
            if node.name.startswith("this.") and op != "=":
                self._flow_check_read(node.name[5:], line, is_this_qualified=True)
            rhs_flow = self._check_expression_flow(node.expression)
            if node.name.startswith("this."):
                self._flow_apply_local_write(node.name[5:], line, is_compound=(op != "="), is_this_qualified=True)
            return rhs_flow

        if node.name and "." in node.name:
            if node.target is not None:
                self.check_expression(node.target)
            return self._check_expression_flow(node.expression)

        target_ident = node.target.name if isinstance(node.target, Identifier) else node.name
        if op != "=" and target_ident:
            self._flow_check_read(target_ident, line, is_this_qualified=False)
        ok, target_type = self._is_modifiable_lvalue(
            node.target,
            node.name,
            line,
            f"atribuição '{op}'",
            defer_flow_write=True,
        )
        if op == "=" and target_type:
            rhs_flow = self._check_expression_with_target(node.expression, target_type)
        else:
            rhs_flow = self._check_expression_flow(node.expression)
        if target_ident:
            self._flow_apply_local_write(target_ident, line, is_compound=(op != "="), is_this_qualified=False)
        if target_type:
            self.check_assignment_type(
                target_type,
                node.expression,
                node.name or "alvo",
                line,
                operator=op,
            )
        if rhs_flow.true_state is not None or rhs_flow.false_state is not None:
            linfo = self._find_local_var_info(target_ident) if target_ident else None
            if linfo is not None:
                vid = ("local", id(linfo))
                def _with_assigned(st):
                    if st is None or not st[2]:
                        return st
                    return (st[0] | {vid}, st[1] - {vid}, True)
                return self._FlowResult(
                    rhs_flow.true_vars,
                    rhs_flow.false_vars,
                    _with_assigned(rhs_flow.true_state),
                    _with_assigned(rhs_flow.false_state),
                )
        return self._FlowResult()

    class _FlowResult:
        """Armazena conjuntos de variáveis de pattern e estados DA/DU para ramos booleano verdadeiro vs falso (JLS §6.3.1 / §16)."""
        __slots__ = ("true_vars", "false_vars", "true_state", "false_state")

        def __init__(
            self,
            true_vars: Optional[Dict[str, Dict[str, Any]]] = None,
            false_vars: Optional[Dict[str, Dict[str, Any]]] = None,
            true_state: Optional[Tuple[Set[Any], Set[Any], bool]] = None,
            false_state: Optional[Tuple[Set[Any], Set[Any], bool]] = None,
        ):
            self.true_vars: Dict[str, Dict[str, Any]] = true_vars if true_vars is not None else {}
            self.false_vars: Dict[str, Dict[str, Any]] = false_vars if false_vars is not None else {}
            self.true_state = true_state
            self.false_state = false_state

    def check_expression(self, node: Optional[ASTNode]):
        """Verifica expressões, prevenindo falsos positivos para símbolos externos e métodos."""
        if node is None:
            return
        self._check_expression_flow(node)

    def _check_expression_flow(self, node: Optional[ASTNode]) -> "_FlowResult":
        """Verifica uma expressão e computa variáveis de pattern em escopo nos ramos true/false (JLS §6.3.1)."""
        empty = self._FlowResult()
        if node is None:
            return empty

        if isinstance(node, Literal):
            self._validate_numeric_literal(node, negated=False)
            if getattr(node, "kind", "") == "BOOLEAN":
                cur = self._flow_snapshot()
                if str(node.value).lower() == "true":
                    return self._FlowResult(true_state=cur, false_state=self._flow_unreachable())
                return self._FlowResult(true_state=self._flow_unreachable(), false_state=cur)
            return empty

        if isinstance(node, Identifier):
            line = getattr(node, "line", 1)
            if self._check_early_target_ref(node.name, line):
                return empty
            if node.name == "this" and self._in_static_context:
                self.errors.append(
                    SemanticError("Não é possível usar 'this' em um contexto estático (JLS §15.8.3).", line)
                )
                return empty
            if node.name == "super" and self._in_static_context:
                self.errors.append(
                    SemanticError("Não é possível usar 'super' em um contexto estático (JLS §15.11).", line)
                )
                return empty

            # Identificadores com ponto (ex: System.out.println), 'this' ou 'super' não geram falso erro
            if node.name in ("this", "super") or node.name.startswith(("this.", "super.")) or "." in node.name:
                return empty

            # Registro de captura de variável local/parâmetro por expressão lambda (JLS §15.27.2)
            self._record_lambda_capture(node.name, line)

            symbol = self._lookup_var_symbol(node.name)
            if self._in_early_construction_context and symbol is not None and symbol.get("category") == "campo" and not symbol.get("is_static", False):
                self.errors.append(
                    SemanticError(f"Acesso inválido ao campo de instância '{node.name}' antes da invocação explícita do construtor (early construction context — JLS §8.8.7 / JEP 513).", line)
                )
            elif self._in_static_context and symbol is not None and symbol.get("category") == "campo" and not symbol.get("is_static", False):
                if self._find_local_var_info(node.name) is None:
                    self.errors.append(
                        SemanticError(f"Não é possível referenciar o campo não-estático '{node.name}' a partir de um contexto estático (JLS §8.3.1.1).", line)
                    )

            if symbol is not None and symbol.get("owner_key"):
                self._inheritance_analyzer.check_member_access(
                    symbol["owner_key"],
                    symbol.get("access", "public"),
                    bool(symbol.get("is_static", False)),
                    symbol.get("category", "campo"),
                    node.name,
                    line,
                )

            if symbol is None or symbol.get("category") not in (self.TYPE_SYMBOL_CATEGORIES | {"variavel", "parametro", "campo", "constante_enum", "constante_interface", "componente_record"}):
                self.errors.append(
                    SemanticError(f"Variável '{node.name}' não foi declarada.", line)
                )
            else:
                self._flow_check_read(node.name, line, is_this_qualified=False)
            return empty

        if isinstance(node, ObjectCreationExpression):
            return self._check_object_creation(node, target_type=None)

        if isinstance(node, MethodCall):
            return self._check_method_call(node, target_type=None)

        if isinstance(node, MemberAccess):
            line = getattr(node, "line", 1)
            qname = self._extract_qualified_name(node)
            if qname and self._is_known_type(qname):
                self._inheritance_analyzer.check_type_access(qname, line)
                return empty

            recv_is_type = False
            recv_type: Optional[str] = None
            via_super_access = isinstance(node.target, Identifier) and node.target.name == "super"
            qtarget = self._extract_qualified_name(node.target)
            if qtarget and (
                self._is_known_type(qtarget)
                or (qtarget.split(".")[-1][0].isupper() and self._lookup_var_symbol(qtarget.split(".")[0]) is None)
            ):
                recv_is_type = True
                recv_type = qtarget
                self._inheritance_analyzer.check_type_access(qtarget, line)
            elif isinstance(node.target, Identifier) and node.target.name in ("this", "super"):
                self._check_early_target_ref(
                    node.target.name,
                    line,
                    f"Acesso inválido a membro via '{node.target.name}' ('{node.target.name}.{node.member_name}')",
                )
                if self._in_static_context:
                    self.errors.append(
                        SemanticError(f"Não é possível usar '{node.target.name}' em contexto estático.", line)
                    )
                if node.target.name == "this":
                    self._flow_check_read(node.member_name, line, is_this_qualified=True)
                recv_type = self._infer_member_access_receiver_type(node)
            elif isinstance(node.target, Identifier):
                sym = self._lookup_var_symbol(node.target.name)
                if sym is not None and sym.get("category") not in self.TYPE_SYMBOL_CATEGORIES and sym.get("category") is not None:
                    self._check_expression_flow(node.target)
                    recv_type = sym.get("type")
                elif self._is_known_type(node.target.name):
                    recv_is_type = True
                    recv_type = node.target.name
                elif node.target.name and node.target.name[0].isupper():
                    recv_is_type = True
                    recv_type = node.target.name
                else:
                    self._check_expression_flow(node.target)
                    recv_type = self.infer_type(node.target)
            else:
                self._check_expression_flow(node.target)
                recv_type = self.infer_type(node.target)

            if recv_type:
                if recv_is_type and node.member_name in ("this", "super"):
                    if self._in_static_context:
                        self.errors.append(
                            SemanticError(
                                f"Não é possível usar '{recv_type}.{node.member_name}' em contexto estático (JLS §15.8.4).",
                                line,
                            )
                        )
                    return empty
                recv_simple = self._simple_base_name(recv_type) or recv_type
                if recv_simple in self.PRIMITIVE_TYPES or recv_simple in ("void", "null"):
                    self.errors.append(
                        SemanticError(
                            f"Não é possível acessar o membro '{node.member_name}' em expressão do tipo '{recv_type}' (JLS §15.11).",
                            line,
                        )
                    )
                    return empty
                if recv_type.endswith("[]"):
                    if node.member_name == "length":
                        return empty
                    self.errors.append(
                        SemanticError(
                            f"Campo '{node.member_name}' não existe no tipo array '{recv_type}' (apenas 'length' é membro de arrays — JLS §10.7).",
                            line,
                        )
                    )
                    return empty
                fields, is_known_f = self._collect_type_fields(recv_type)
                finfo = fields.get(node.member_name)
                if finfo is not None:
                    self._inheritance_analyzer.check_member_access(
                        finfo.get("owner_key") or recv_type,
                        finfo.get("access", "public"),
                        bool(finfo.get("is_static", False)),
                        finfo.get("category", "campo"),
                        node.member_name,
                        line,
                        receiver_type=None if (recv_is_type or via_super_access or (isinstance(node.target, Identifier) and node.target.name == "this")) else recv_type,
                        via_super=via_super_access,
                    )
                    if recv_is_type and not finfo.get("is_static", False):
                        self.errors.append(
                            SemanticError(
                                f"Campo de instância '{node.member_name}' não pode ser referenciado estaticamente via '{recv_type}.{node.member_name}' (JLS §15.11).",
                                line,
                            )
                        )
                elif self._lookup_type_decl(recv_type) is not None and is_known_f:
                    # Verifica também tipo aninhado qualificado (Outer.Inner)
                    if self._lookup_type_decl(f"{recv_type}.{node.member_name}") is None and self._lookup_type_decl(node.member_name) is None:
                        self.errors.append(
                            SemanticError(
                                f"Campo '{node.member_name}' não encontrado no tipo '{recv_type}' (JLS §15.11).",
                                line,
                            )
                        )
            return empty

        if isinstance(node, MethodReference):
            self._check_method_ref_with_target(node, target_type=None)
            return empty

        if isinstance(node, ArrayAccess):
            line = getattr(node, "line", 1)
            self._check_expression_flow(node.array)
            self._check_expression_flow(node.index)
            arr_t = self.infer_type(node.array)
            if arr_t and arr_t not in ("Object", "var", "desconhecido") and not self._is_type_variable(arr_t):
                if not arr_t.endswith("[]"):
                    self.errors.append(
                        SemanticError(
                            f"Expressão de tipo '{arr_t}' não é um array para acesso indexado '[...]' (JLS §10.4).",
                            line,
                        )
                    )
            idx_t = self.infer_type(node.index)
            if idx_t and idx_t not in ("Object", "var", "desconhecido") and not self._is_type_variable(idx_t):
                if self._unboxed_numeric(idx_t) not in ("byte", "short", "char", "int"):
                    self.errors.append(
                        SemanticError(
                            f"Índice de array deve ser compatível com 'int' (encontrado '{idx_t}' — JLS §10.4).",
                            line,
                        )
                    )
            return empty

        if isinstance(node, ConditionalExpression):
            return self._check_expression_with_target(node, target_type=None)

        if isinstance(node, ArrayCreationExpression):
            line = getattr(node, "line", 1)
            arr_tref = getattr(node, "type_ref", None)
            self._check_type_ref_annotations(arr_tref)
            self._check_array_component_reifiable(arr_tref, line, "expressão de criação de array 'new ...[]'")
            for dim in node.dimensions:
                if dim is not None:
                    self._check_expression_flow(dim)
                    dt = self.infer_type(dim)
                    if dt and dt not in ("Object", "var", "desconhecido") and not self._is_type_variable(dt):
                        if self._unboxed_numeric(dt) not in ("byte", "short", "char", "int"):
                            self.errors.append(
                                SemanticError(
                                    f"Expressão de tamanho de dimensão de array deve ser inteira compatível com 'int' (encontrado '{dt}' — JLS §15.10.1).",
                                    getattr(dim, "line", line),
                                )
                            )
            if node.initializer is not None:
                arr_t = self._normalize_type_str(getattr(node, "type_ref", None))
                self._check_expression_with_target(node.initializer, arr_t)
            return empty

        if isinstance(node, ArrayInitializer):
            for elem in node.elements:
                self._check_expression_flow(elem)
            return empty

        if isinstance(node, CastExpression):
            self._check_cast(node)
            return empty

        if isinstance(node, InstanceOfExpression):
            line = getattr(node, "line", 1)
            self._check_expression_flow(node.expression)
            src_type = self.infer_type(node.expression)
            pat = getattr(node, "pattern", None)
            if getattr(node, "is_pattern", False) or pat is not None:
                pvars = self._analyze_pattern(pat, selector_type=src_type, is_component=False)
                return self._FlowResult(true_vars=pvars, false_vars={})

            tref = getattr(node, "target_type", None)
            self._check_type_ref_annotations(tref)
            t_str = self._normalize_type_str(tref)
            if t_str:
                t_base, t_dims = self._split_type_dims(self._strip_generics(t_str) or "")
                src_base, src_dims = (
                    self._split_type_dims(self._strip_generics(src_type) or "")
                    if src_type
                    else ("", 0)
                )
                if t_dims == 0 and t_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                    self.errors.append(
                        SemanticError(
                            f"Tipo primitivo '{t_str}' em 'instanceof' pertence ao recurso preview (JEP 530) e está desabilitado no modo padrão Java SE 26 (JLS §15.20.2).",
                            line,
                        )
                    )
                elif src_type and src_dims == 0 and src_base in self.PRIMITIVE_TYPES and not self.enable_preview_primitive_patterns:
                    self.errors.append(
                        SemanticError(
                            f"Operador 'instanceof' exige expressão de tipo referência no modo padrão Java SE 26 (encontrado '{src_type}' — JLS §15.20.2).",
                            line,
                        )
                    )
                elif src_type and self._are_types_disjoint(src_type, t_str) is True:
                    self.errors.append(
                        SemanticError(
                            f"Tipos incompatíveis em 'instanceof': '{src_type}' não pode ser instância de '{t_str}' (JLS §15.20.2).",
                            line,
                        )
                    )
            return empty

        if isinstance(node, ClassLiteral):
            return empty

        if isinstance(node, LambdaExpression):
            self._check_lambda_with_target(node, target_type=None)
            return empty

        if isinstance(node, SwitchExpression):
            return self._check_expression_with_target(node, target_type=None)

        if isinstance(node, Assignment):
            return self._check_assignment(node)

        if isinstance(node, UnaryOp):
            if node.op == "!":
                sub = self._check_expression_flow(node.operand)
                op_t = self.infer_type(node.operand)
                if op_t and not self._is_boolean_type(op_t) and op_t not in ("Object", "var", "desconhecido") and not self._is_type_variable(op_t):
                    self.errors.append(
                        SemanticError(f"Operador lógico '!' requer operando 'boolean' (encontrado '{op_t}' — JLS §15.15.6).", getattr(node, "line", 1))
                    )
                cur = self._flow_snapshot()
                st_true = sub.false_state if sub.false_state is not None else cur
                st_false = sub.true_state if sub.true_state is not None else cur
                self._flow_restore(self._flow_join_states(st_true, st_false))
                return self._FlowResult(
                    true_vars=dict(sub.false_vars),
                    false_vars=dict(sub.true_vars),
                    true_state=st_true,
                    false_state=st_false,
                )
            self._validate_unary_op(node)
            return empty

        if isinstance(node, BinaryOp):
            if node.op == "&&":
                fl = self._check_expression_flow(node.left)
                cur_l = self._flow_snapshot()
                lt = fl.true_state if fl.true_state is not None else cur_l
                lf = fl.false_state if fl.false_state is not None else cur_l
                self._flow_restore(lt)
                self._push_pattern_scope(fl.true_vars)
                try:
                    fr = self._check_expression_flow(node.right)
                finally:
                    self._pop_pattern_scope()
                cur_r = self._flow_snapshot()
                rt = fr.true_state if fr.true_state is not None else cur_r
                rf = fr.false_state if fr.false_state is not None else cur_r
                out_true_st = rt
                out_false_st = self._flow_join_states(lf, rf)
                self._flow_restore(self._flow_join_states(out_true_st, out_false_st))
                self._validate_binary_op(node)
                merged_true = dict(fl.true_vars)
                merged_true.update(fr.true_vars)
                return self._FlowResult(
                    true_vars=merged_true,
                    false_vars={},
                    true_state=out_true_st,
                    false_state=out_false_st,
                )

            if node.op == "||":
                fl = self._check_expression_flow(node.left)
                cur_l = self._flow_snapshot()
                lt = fl.true_state if fl.true_state is not None else cur_l
                lf = fl.false_state if fl.false_state is not None else cur_l
                self._flow_restore(lf)
                self._push_pattern_scope(fl.false_vars)
                try:
                    fr = self._check_expression_flow(node.right)
                finally:
                    self._pop_pattern_scope()
                cur_r = self._flow_snapshot()
                rt = fr.true_state if fr.true_state is not None else cur_r
                rf = fr.false_state if fr.false_state is not None else cur_r
                out_true_st = self._flow_join_states(lt, rt)
                out_false_st = rf
                self._flow_restore(self._flow_join_states(out_true_st, out_false_st))
                self._validate_binary_op(node)
                merged_false = dict(fl.false_vars)
                merged_false.update(fr.false_vars)
                return self._FlowResult(
                    true_vars={},
                    false_vars=merged_false,
                    true_state=out_true_st,
                    false_state=out_false_st,
                )

            self._check_expression_flow(node.left)
            self._check_expression_flow(node.right)
            self._validate_binary_op(node)
            return empty

        return empty

    def is_assignable(self, target_type: str, source_type: str) -> bool:
        """
        Verifica compatibilidade de atribuição entre o tipo alvo e o da expressão,
        suportando widening, boxing, unboxing, subtipagem e argumentos genéricos (JLS §5.2).
        """
        if not target_type or not source_type:
            return True
        t_clean = self._strip_leading_type_annotations(target_type) or target_type
        s_clean = self._strip_leading_type_annotations(source_type) or source_type
        if t_clean == s_clean:
            return True
        t_simple = self._simple_base_name(t_clean) or t_clean
        s_simple = self._simple_base_name(s_clean) or s_clean

        if s_clean == "void":
            return False
        if t_clean == "void":
            return s_clean == "void"
        if t_clean in ("Object", "desconhecido", "var") or s_clean in ("desconhecido", "var"):
            return True
        t_active_tp = self._lookup_type_param_bounds(t_simple) is not None
        s_active_tp = self._lookup_type_param_bounds(s_simple) is not None
        if (self._is_type_variable(t_simple) and not t_active_tp) or (self._is_type_variable(s_simple) and not s_active_tp):
            return True
        if s_simple == "null":
            return t_simple not in self.PRIMITIVE_TYPES

        t_is_prim = t_simple in self.PRIMITIVE_TYPES
        s_is_prim = s_simple in self.PRIMITIVE_TYPES

        if t_is_prim and s_is_prim:
            if t_simple == s_simple:
                return True
            return t_simple in self.WIDENING_PRIMITIVE_TARGETS.get(s_simple, set())

        if t_is_prim and not s_is_prim:
            s_unboxed = self.WRAPPER_TO_PRIMITIVE.get(s_simple)
            if s_unboxed == t_simple:
                return True
            if s_unboxed and t_simple in self.WIDENING_PRIMITIVE_TARGETS.get(s_unboxed, set()):
                return True
            return False

        if not t_is_prim and s_is_prim:
            boxed = self.PRIMITIVE_TO_WRAPPER.get(s_simple)
            if not boxed:
                return False
            if boxed == t_simple or t_simple == "Object":
                return True
            return self._is_subtype(boxed, t_clean) is True

        sub = self._is_subtype(s_clean, t_clean)
        if sub is True:
            return True
        if sub is None and (not self._is_known_type(t_clean) or not self._is_known_type(s_clean)):
            return True
        return False

    def infer_type(self, node: Optional[ASTNode]) -> Optional[str]:
        """Infere o tipo estático da expressão considerando JLS §5.6, membros, arrays, poly expressions e switch."""
        if node is None:
            return None
        cached = self._inferred_types.get(id(node))
        if cached is not None:
            return cached
        if isinstance(node, Literal):
            if node.kind in ("STRING", "TEXT_BLOCK"):
                return "String"
            if node.kind == "NULL":
                return "null"
            if node.kind == "BOOLEAN":
                return "boolean"
            if node.kind == "CHAR":
                return "char"
            if node.kind == "DOUBLE":
                return "double"
            if node.kind == "FLOAT":
                return "float"
            if node.kind == "LONG":
                return "long"
            if node.kind in ("NUM", "INT"):
                val_str = str(node.value)
                if val_str.startswith(("0x", "0X")) and not any(c in val_str for c in ('p', 'P', '.')):
                    if val_str.endswith(("l", "L")):
                        return "long"
                    return "int"
                if "." in val_str or ("e" in val_str.lower() and not val_str.startswith(("0x", "0X"))) or val_str.endswith(("f", "F", "d", "D")):
                    if val_str.endswith(("f", "F")):
                        return "float"
                    return "double"
                if val_str.endswith(("l", "L")):
                    return "long"
                return "int"
            return "int"
        if isinstance(node, ClassLiteral):
            t_str = self._normalize_type_str(getattr(node, "type_ref", None))
            if not t_str:
                return "Class"
            if t_str == "void":
                return "Class<Void>"
            if t_str in self.PRIMITIVE_TO_WRAPPER:
                return f"Class<{self.PRIMITIVE_TO_WRAPPER[t_str]}>"
            return f"Class<{t_str}>"
        if isinstance(node, MemberAccess):
            recv_t = self._infer_member_access_receiver_type(node)
            if recv_t:
                if node.member_name == "this":
                    return recv_t
                if node.member_name == "super":
                    supers, _ = self._direct_supertypes(recv_t)
                    return supers[0] if supers else "Object"
                if recv_t.endswith("[]") and node.member_name == "length":
                    return "int"
                if self._simple_base_name(recv_t) in self._enums:
                    enum_decl = self._enums[self._simple_base_name(recv_t)]
                    if any(getattr(c, "name", None) == node.member_name for c in getattr(enum_decl, "constants", [])):
                        return recv_t
                fields, _ = self._collect_type_fields(recv_t)
                finfo = fields.get(node.member_name)
                if finfo is not None:
                    return finfo.get("type")
            return None
        if isinstance(node, Identifier):
            if node.name == "this":
                return self._current_enclosing_type()
            if node.name == "super":
                cur = self._current_enclosing_type()
                if cur:
                    supers, _ = self._direct_supertypes(cur)
                    return supers[0] if supers else "Object"
            symbol = self._lookup_var_symbol(node.name)
            return symbol["type"] if symbol and "type" in symbol else None
        if isinstance(node, ArrayAccess):
            arr_t = self.infer_type(node.array)
            if arr_t and arr_t.endswith("[]"):
                return arr_t[:-2]
            return None
        if isinstance(node, ArrayCreationExpression):
            return self._normalize_type_str(getattr(node, "type_ref", None))
        if isinstance(node, ObjectCreationExpression):
            return self._normalize_type_str(getattr(node, "type_ref", None)) or getattr(node, "class_name", None)
        if isinstance(node, InstanceOfExpression):
            return "boolean"
        if isinstance(node, CastExpression):
            return self._normalize_type_str(getattr(node, "target_type", None)) or str(node.target_type)
        if isinstance(node, ConditionalExpression):
            then_t = self.infer_type(node.then_expr)
            else_t = self.infer_type(node.else_expr)
            # JLS §15.25.2: constante int que cabe em byte/short/char combina com esse tipo
            if then_t in self.INTEGER_RANGES and self._is_constant_narrowing_compatible(then_t, node.else_expr):
                return then_t
            if else_t in self.INTEGER_RANGES and self._is_constant_narrowing_compatible(else_t, node.then_expr):
                return else_t
            return self._lub_type(then_t, else_t)
        if isinstance(node, UnaryOp):
            if node.op == "!":
                return "boolean"
            op_t = self.infer_type(node.operand)
            if node.op in ("++", "--", "post++", "post--"):
                return op_t
            if node.op in ("+", "-", "~"):
                return self._unary_numeric_promotion(op_t) or op_t
            return op_t
        if isinstance(node, Assignment):
            if isinstance(node.target, (MemberAccess, ArrayAccess)):
                t = self.infer_type(node.target)
                if t:
                    return t
            if node.name and "." not in node.name and not node.name.startswith("this."):
                symbol = self._lookup_var_symbol(node.name)
                if symbol and "type" in symbol:
                    return symbol["type"]
            return self.infer_type(node.expression)
        if isinstance(node, BinaryOp):
            if node.op in ("&&", "||", "==", "!=", "<", ">", "<=", ">="):
                return "boolean"
            left = self.infer_type(node.left)
            right = self.infer_type(node.right)
            if node.op == "+" and (left == "String" or right == "String"):
                return "String"
            if node.op in ("<<", ">>", ">>>"):
                return self._unary_numeric_promotion(left) or left
            if node.op in ("&", "|", "^"):
                if self._is_boolean_type(left) and self._is_boolean_type(right):
                    return "boolean"
                return self._binary_numeric_promotion(left, right) or left or right
            return self._binary_numeric_promotion(left, right) or left or right
        return None

    def check_assignment_type(
        self,
        target_type: str,
        expression: ASTNode,
        target_name: str,
        line: int,
        operator: str = "=",
    ):
        """
        Verifica compatibilidade entre o tipo alvo e a expressão em atribuições simples e compostas (JLS §5.2 / §15.26.2).
        """
        if operator == "+=" and target_type == "String":
            return

        if operator != "=" and target_type == "String":
            self.errors.append(
                SemanticError(
                    f"Operação aritmética '{operator}' inválida: tipo 'String' não é suportado em operações aritméticas.",
                    line,
                )
            )
            return

        if operator != "=":
            expr_type = self.infer_type(expression)
            if not expr_type or target_type in ("Object", "var", "desconhecido") or expr_type in ("Object", "var", "desconhecido"):
                return
            if operator in ("<<=", ">>=", ">>>="):
                if not self._is_integral_type(target_type) or not self._is_integral_type(expr_type):
                    self.errors.append(
                        SemanticError(
                            f"Atribuição composta '{operator}' exige operandos integrais (encontrado '{target_type}' e '{expr_type}' — JLS §15.26.2).",
                            line,
                        )
                    )
            elif operator in ("&=", "|=", "^="):
                both_int = self._is_integral_type(target_type) and self._is_integral_type(expr_type)
                both_bool = self._is_boolean_type(target_type) and self._is_boolean_type(expr_type)
                if not both_int and not both_bool:
                    self.errors.append(
                        SemanticError(
                            f"Atribuição composta '{operator}' exige operandos integrais ou booleanos compatíveis (encontrado '{target_type}' e '{expr_type}' — JLS §15.26.2).",
                            line,
                        )
                    )
            else:
                if self._unboxed_numeric(target_type) is None or self._unboxed_numeric(expr_type) is None:
                    self.errors.append(
                        SemanticError(
                            f"Atribuição aritmética composta '{operator}' inválida entre '{target_type}' e '{expr_type}' (JLS §15.26.2).",
                            line,
                        )
                    )
            return

        if not self._is_assignable_expr(target_type, expression):
            expr_type = self.infer_type(expression) or "poly-expression"
            self.errors.append(
                SemanticError(
                    f"Incompatibilidade de tipos: não é possível atribuir {expr_type} a '{target_name}' do tipo {target_type}.",
                    line,
                )
            )
