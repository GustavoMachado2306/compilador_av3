"""
Solucionador formal de restrições de inferência de tipos genéricos segundo a JLS §18.

Separa a modelagem explícita de:
- Variáveis de inferência (`InferenceVariable`: α = INF#k)
- Restrições tipadas (`Constraint`: igualdade =, subtipagem <:, contenção <=, compatibilidade →)
- Conjunto de limites (`BoundSet`: limites inferiores, superiores, igualdades e dependências α <: β)
- Redução (§18.2), Incorporação (§18.3), Resolução (§18.4) e Inferência de Invocação (§18.5.1 / §18.5.2)

O módulo mantém acoplamento mínimo com `SemanticAnalyzer` por meio da interface `host`,
permitindo evoluir as regras formais da JLS §18 sem misturar lógica do solucionador ao
visitante de AST e ao analisador de fluxo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.ast_nodes import (
    ASTNode,
    Block,
    ConditionalExpression,
    Identifier,
    LambdaExpression,
    Literal,
    MemberAccess,
    MethodCall,
    MethodReference,
    ObjectCreationExpression,
    ReturnStatement,
    TypeReference,
)


_INF_VAR_RE = re.compile(r"INF#\d+")
_INF_VAR_EXACT_RE = re.compile(r"^INF#\d+$")


class ConstraintKind(Enum):
    """Tipos formais de fórmulas de restrição da JLS §18.1.2."""

    COMPATIBLE = "->"
    SUBTYPE = "<:"
    EQUALITY = "="
    CONTAINS = "<="


@dataclass(frozen=True)
class InferenceVariable:
    """Representa uma variável de inferência α associada a um parâmetro de tipo T."""

    name: str
    alpha: str
    declared_bounds: Tuple[str, ...] = ("Object",)


@dataclass
class Constraint:
    """Fórmula de restrição entre expressões/tipos e tipos parametrizados."""

    kind: ConstraintKind
    left: str
    right: str
    expr_node: Optional[ASTNode] = None
    allow_boxing: bool = True


@dataclass
class BoundSet:
    """
    Conjunto explícito de limites das variáveis de inferência (JLS §18.1.3).

    Armazena limites inferiores (`L <: α`), superiores (`α <: U`), igualdades (`α = T`),
    dependências entre variáveis (`α <: β`, `α = β`) e contradições detectadas.
    """

    variables: Dict[str, InferenceVariable] = field(default_factory=dict)
    lower_bounds: Dict[str, List[str]] = field(default_factory=dict)
    upper_bounds: Dict[str, List[str]] = field(default_factory=dict)
    eq_bounds: Dict[str, List[str]] = field(default_factory=dict)
    dep_subtypes: Set[Tuple[str, str]] = field(default_factory=set)
    dep_equalities: Set[Tuple[str, str]] = field(default_factory=set)
    contradictions: List[str] = field(default_factory=list)

    def ensure_var(self, ivar: InferenceVariable) -> None:
        self.variables[ivar.alpha] = ivar
        self.lower_bounds.setdefault(ivar.alpha, [])
        self.upper_bounds.setdefault(ivar.alpha, [])
        self.eq_bounds.setdefault(ivar.alpha, [])

    def add_lower(self, alpha: str, bound: str) -> bool:
        if not bound or bound == alpha:
            return False
        lst = self.lower_bounds.setdefault(alpha, [])
        if bound not in lst:
            lst.append(bound)
            return True
        return False

    def add_upper(self, alpha: str, bound: str) -> bool:
        if not bound or bound == alpha or bound == "Object":
            return False
        lst = self.upper_bounds.setdefault(alpha, [])
        if bound not in lst:
            lst.append(bound)
            return True
        return False

    def add_eq(self, alpha: str, bound: str) -> bool:
        if not bound or bound == alpha:
            return False
        lst = self.eq_bounds.setdefault(alpha, [])
        if bound not in lst:
            lst.append(bound)
            return True
        return False

    def add_contradiction(self, msg: str) -> None:
        if msg and msg not in self.contradictions:
            self.contradictions.append(msg)

    def clone(self) -> "BoundSet":
        return BoundSet(
            variables=dict(self.variables),
            lower_bounds={k: list(v) for k, v in self.lower_bounds.items()},
            upper_bounds={k: list(v) for k, v in self.upper_bounds.items()},
            eq_bounds={k: list(v) for k, v in self.eq_bounds.items()},
            dep_subtypes=set(self.dep_subtypes),
            dep_equalities=set(self.dep_equalities),
            contradictions=list(self.contradictions),
        )


@dataclass
class InferenceResult:
    """Resultado completo da resolução de restrições para uma invocação genérica."""

    success: bool
    mapping: Dict[str, str]
    bound_set: BoundSet
    errors: List[str] = field(default_factory=list)


class JLS18ConstraintSolver:
    """
    Motor de inferência de tipos genéricos segundo JLS §18.

    Implementa:
    - Instanciação de variáveis de inferência `INF#k` com seus limites declarados;
    - Redução de restrições de compatibilidade (`->`), subtipagem (`<:`),
      igualdade (`=`) e contenção de argumentos de tipo (`<=`) (JLS §18.2);
    - Incorporação e fechamento transitivo de limites com detecção de conflitos e
      ciclos infinitos / occurs check (JLS §18.3);
    - Resolução topológica de variáveis dependentes com LUB parametrizado (JLS §18.4);
    - Integração iterativa com lambdas, method references, condicionais,
      chamadas genéricas aninhadas e operador diamond `<>` (JLS §18.5).
    """

    def __init__(self, host: Any):
        self.host = host
        self._alpha_counter = 0

    @staticmethod
    def free_inf_vars(type_str: Optional[str]) -> Set[str]:
        if not type_str:
            return set()
        return set(_INF_VAR_RE.findall(type_str))

    @staticmethod
    def is_inf_var(type_str: Optional[str]) -> bool:
        return bool(type_str and _INF_VAR_EXACT_RE.match(type_str.strip()))

    def _fresh_alpha(self) -> str:
        name = f"INF#{self._alpha_counter}"
        self._alpha_counter += 1
        return name

    def _substitute_map(self, type_str: Optional[str], mapping: Dict[str, str]) -> Optional[str]:
        if not type_str or not mapping:
            return type_str
        return self.host._substitute_type_vars(type_str, mapping)

    def _box_if_prim(self, type_str: str) -> str:
        s = self.host._strip_leading_type_annotations(type_str) or type_str
        return self.host._box_type(s) or s

    def _compute_ref_lub(self, types: List[str]) -> str:
        """
        Calcula Least Upper Bound de referência (JLS §4.10.4) para resolução §18.4.

        Diferente do operador ternário numérico (que promove para primitivo), limites de
        inferência trabalham com tipos de referência encaixotados e preservam supertipos
        parametrizados comuns quando possível.
        """
        non_null = [t for t in types if t and t != "null"]
        if not non_null:
            return "Object"
        boxed = [self._box_if_prim(t) for t in non_null]
        acc = boxed[0]
        for nxt in boxed[1:]:
            if acc == nxt:
                continue
            acc = self._lub_pair(acc, nxt)
        return acc

    def _lub_pair(self, t1: str, t2: str, visiting: Optional[Set[Tuple[str, str]]] = None) -> str:
        if t1 == t2:
            return t1
        if visiting is None:
            visiting = set()
        key = (t1, t2) if t1 <= t2 else (t2, t1)
        if key in visiting:
            return "Object"
        visiting.add(key)

        if self.host._is_subtype(t1, t2) is True:
            return t2
        if self.host._is_subtype(t2, t1) is True:
            return t1

        # Se ambos parametrizam a mesma base (ex: List<Integer> e List<Double> -> List<? extends Number>)
        b1, a1, d1 = self.host._extract_generic_args(t1)
        b2, a2, d2 = self.host._extract_generic_args(t2)
        if d1 == d2 == 0 and b1 and b2:
            s1 = self.host._simple_base_name(b1) or b1
            s2 = self.host._simple_base_name(b2) or b2
            if s1 == s2 and a1 and a2 and len(a1) == len(a2):
                merged_args: List[str] = []
                for x1, x2 in zip(a1, a2):
                    if x1 == x2:
                        merged_args.append(x1)
                    else:
                        u1 = x1[len("? extends "):].strip() if x1.startswith("? extends ") else x1
                        u2 = x2[len("? extends "):].strip() if x2.startswith("? extends ") else x2
                        if u1.startswith("?") or u2.startswith("?"):
                            merged_args.append("?")
                        else:
                            common = self._lub_pair(u1, u2, visiting)
                            if common == "Object":
                                merged_args.append("?")
                            else:
                                merged_args.append(f"? extends {common}")
                return f"{s1}<{', '.join(merged_args)}>"

        # Procura supertipo comum parametrizado via elevação de base
        common_base = self.host._lub_type(t1, t2) or "Object"
        if common_base != "Object":
            l1 = self.host._lift_to_base_type(t1, common_base)
            l2 = self.host._lift_to_base_type(t2, common_base)
            if l1 and l2 and ("<" in l1 or "<" in l2) and l1 != t1 and l2 != t2:
                return self._lub_pair(l1, l2, visiting)
        return common_base

    # ------------------------------------------------------------------
    # Instanciação de variáveis de inferência de uma assinatura
    # ------------------------------------------------------------------

    def _format_errors(self, bset: BoundSet) -> List[str]:
        if not bset.contradictions:
            return []
        alpha_to_name = {alpha: iv.name for alpha, iv in bset.variables.items()}
        formatted: List[str] = []
        for msg in bset.contradictions:
            text = _INF_VAR_RE.sub(lambda m: alpha_to_name.get(m.group(0), m.group(0)), msg)
            if text not in formatted:
                formatted.append(text)
        return formatted

    def _allocate_sig_vars(
        self,
        sig: Dict[str, Any],
        bset: BoundSet,
        name_to_alpha: Dict[str, str],
    ) -> Dict[str, str]:
        """Cria α frescos para os parâmetros de tipo declarados em `sig` com seus limites."""
        tparams = list(sig.get("tparams", []) or [])
        tparam_bounds = dict(sig.get("tparam_bounds", {}) or {})
        local_map: Dict[str, str] = {}
        for tp in tparams:
            alpha = self._fresh_alpha()
            local_map[tp] = alpha
            name_to_alpha[tp] = alpha

        for tp in tparams:
            alpha = local_map[tp]
            raw_bounds = list(tparam_bounds.get(tp, []) or []) or ["Object"]
            sub_bounds = [
                self._substitute_map(b, local_map) or b
                for b in raw_bounds
            ]
            ivar = InferenceVariable(name=tp, alpha=alpha, declared_bounds=tuple(sub_bounds))
            bset.ensure_var(ivar)
            for ub in sub_bounds:
                if self.is_inf_var(ub):
                    if ub != alpha:
                        bset.dep_subtypes.add((alpha, ub))
                elif ub and ub != "Object":
                    bset.add_upper(alpha, ub)
        return local_map

    # ------------------------------------------------------------------
    # Ponto de entrada público para chamadas / construtores
    # ------------------------------------------------------------------

    def solve_invocation(
        self,
        sig: Dict[str, Any],
        args: List[ASTNode],
        arg_types: List[Optional[str]],
        expected_return: Optional[str] = None,
        explicit_targs: Optional[List[str]] = None,
        phase: int = 2,
    ) -> InferenceResult:
        """
        Executa inferência JLS §18 completa para uma assinatura candidata.

        1. (§18.5.1) Reduz e incorpora restrições dos argumentos + limites declarados;
           se houver contradição, a sobrecarga não é aplicável (`success=False`).
        2. (§18.5.2) Reduz restrições de contexto de retorno esperado e expressões
           poly adiadas (lambdas, method references, condicionais, chamadas aninhadas,
           diamond `<>`) até convergência.
        3. (§18.4) Resolve as variáveis de inferência em ordem topológica.
        """
        tparams = list(sig.get("tparams", []) or [])
        bset = BoundSet()
        if not tparams:
            return InferenceResult(success=True, mapping={}, bound_set=bset)

        if explicit_targs:
            if len(explicit_targs) != len(tparams):
                bset.add_contradiction(
                    f"Quantidade incorreta de argumentos de tipo explícitos: esperado {len(tparams)}, encontrado {len(explicit_targs)} (JLS §15.12.2)."
                )
                return InferenceResult(
                    success=False,
                    mapping={},
                    bound_set=bset,
                    errors=list(bset.contradictions),
                )
            explicit_map: Dict[str, str] = {}
            for tp, ta in zip(tparams, explicit_targs):
                explicit_map[tp] = ta
            # Ainda valida que explicit_targs satisfazem tparam_bounds declarados
            tparam_bounds = dict(sig.get("tparam_bounds", {}) or {})
            for tp in tparams:
                ta = explicit_map.get(tp)
                if not ta:
                    continue
                for raw_b in (tparam_bounds.get(tp, []) or []):
                    b = self._substitute_map(raw_b, explicit_map) or raw_b
                    if b not in ("Object", "java.lang.Object") and self.host._is_subtype(ta, b) is False:
                        bset.add_contradiction(
                            f"Argumento de tipo explícito '{ta}' não satisfaz limite '{b}' de '{tp}' (JLS §15.12.2.1)."
                        )
            return InferenceResult(
                success=len(bset.contradictions) == 0,
                mapping=explicit_map,
                bound_set=bset,
                errors=list(bset.contradictions),
            )

        name_to_alpha: Dict[str, str] = {}
        local_map = self._allocate_sig_vars(sig, bset, name_to_alpha)
        eff_params = [self._substitute_map(p, local_map) or p for p in sig["params"]]
        eff_ret = self._substitute_map(sig.get("ret", "void"), local_map) or sig.get("ret", "void")

        is_varargs = bool(sig.get("varargs", False))
        allow_boxing = phase >= 2
        deferred_poly: List[Tuple[int, ASTNode, str]] = []
        worklist: List[Constraint] = []

        # Passo 1: Restrições dos argumentos formais (§18.5.1)
        if not is_varargs or phase < 3:
            if len(eff_params) != len(args):
                bset.add_contradiction("Aridade incompatível durante inferência.")
                return InferenceResult(False, {}, bset, list(bset.contradictions))
            pairs = list(zip(range(len(args)), args, arg_types, eff_params))
        else:
            if len(args) < len(eff_params) - 1:
                bset.add_contradiction("Aridade insuficiente para varargs durante inferência.")
                return InferenceResult(False, {}, bset, list(bset.contradictions))
            fixed = eff_params[:-1]
            va_elem = eff_params[-1]
            pairs = []
            for idx in range(len(args)):
                pt = fixed[idx] if idx < len(fixed) else va_elem
                pairs.append((idx, args[idx], arg_types[idx], pt))

        for idx, arg_node, arg_t, param_t in pairs:
            if is_varargs and phase < 3 and idx == len(eff_params) - 1:
                # Param varargs em fase 1/2 pode receber array T[] diretamente ou elemento único T
                if arg_t and self.host._strip_type_dims_full(arg_t)[1] > self.host._strip_type_dims_full(param_t)[1]:
                    param_t = f"{param_t}[]"
            elif is_varargs and phase >= 3 and idx == len(eff_params) - 1 and len(args) == len(eff_params):
                if arg_t and self.host._strip_type_dims_full(arg_t)[1] > self.host._strip_type_dims_full(param_t)[1]:
                    param_t = f"{param_t}[]"

            if self._is_deferred_poly_arg(arg_node, arg_t):
                # Checagem estrutural inicial + adiamento para fase de poly-expression
                self._initial_poly_applicability(arg_node, param_t, bset, worklist)
                deferred_poly.append((idx, arg_node, param_t))
            elif arg_t and arg_t not in ("var", "desconhecido"):
                worklist.append(
                    Constraint(
                        ConstraintKind.COMPATIBLE,
                        arg_t,
                        param_t,
                        expr_node=arg_node,
                        allow_boxing=allow_boxing,
                    )
                )
            elif isinstance(arg_node, Literal) and getattr(arg_node, "kind", "") == "NULL":
                worklist.append(
                    Constraint(
                        ConstraintKind.COMPATIBLE,
                        "null",
                        param_t,
                        expr_node=arg_node,
                        allow_boxing=allow_boxing,
                    )
                )

        self._reduce_and_incorporate(bset, worklist)
        if bset.contradictions:
            return InferenceResult(False, {}, bset, self._format_errors(bset))

        # Passo 2 (§18.5.2): Reduz expressões poly adiadas que dependem dos parâmetros de entrada
        # e incorpora o tipo de retorno esperado quando houver contexto de atribuição/retorno.
        app_snapshot = bset.clone()
        has_valid_target = bool(
            expected_return and expected_return not in ("var", "desconhecido", "void")
        )
        # Primeiro incorpora expected_return quando há contexto e verifica compatibilidade;
        # caso arguments já determinem um retorno conflitante com target (ex: String s = pick(10, 20)),
        # preservamos o resultado §18.5.1 quando não há variáveis livres a inferir do target para que
        # check_assignment_type reporte a incompatibilidade exata entre tipo inferido e alvo.
        if has_valid_target and eff_ret != "void":
            bset_with_target = bset.clone()
            self._reduce_and_incorporate(
                bset_with_target,
                [
                    Constraint(
                        ConstraintKind.COMPATIBLE,
                        eff_ret,
                        expected_return,
                        allow_boxing=True,
                    )
                ],
            )
            if not bset_with_target.contradictions:
                bset = bset_with_target
            else:
                # Verifica se o conflito veio de poly/unconstrained ou de argumento já fechado contra target.
                # Se alguma variável que ocorre no retorno não tem igualdade nem limite inferior, propagar
                # a contradição é obrigatório; se todas já estão concretizadas pelos argumentos e não há
                # poly pendente, preservamos app_snapshot para erro claro de atribuição.
                ret_vars = self.free_inf_vars(eff_ret)
                unconstrained_ret_var = any(
                    not bset.eq_bounds.get(v) and not bset.lower_bounds.get(v)
                    for v in ret_vars
                )
                if unconstrained_ret_var or deferred_poly:
                    return InferenceResult(False, {}, bset_with_target, self._format_errors(bset_with_target))
                # Mesmo sem usar target no bset final, se explicit_ret já está fechado pelos args,
                # seguimos para resolver os args e deixar check_assignment_type apontar o erro.
                bset = app_snapshot

        # Passo 3: Loop iterativo de redução para lambdas, method refs, condicionais e chamadas aninhadas
        self._resolve_deferred_poly_loop(bset, deferred_poly, allow_boxing)
        if bset.contradictions:
            return InferenceResult(False, {}, bset, self._format_errors(bset))

        # Se expected_return foi adiado por causa de um lambda/methodref que acabou de fixar o retorno:
        if has_valid_target and eff_ret != "void" and deferred_poly:
            self._reduce_and_incorporate(
                bset,
                [Constraint(ConstraintKind.COMPATIBLE, eff_ret, expected_return, allow_boxing=True)],
            )
            if bset.contradictions:
                return InferenceResult(False, {}, bset, self._format_errors(bset))

        # Passo 4 (§18.4): Resolução topológica final de todas as variáveis da assinatura
        resolved_alphas = self._resolve_variables(bset)
        if bset.contradictions:
            return InferenceResult(False, {}, bset, self._format_errors(bset))

        final_map: Dict[str, str] = {}
        for tp in tparams:
            alpha = local_map[tp]
            final_map[tp] = resolved_alphas.get(alpha, "Object")

        return InferenceResult(success=True, mapping=final_map, bound_set=bset)

    # ------------------------------------------------------------------
    # Redução de restrições (JLS §18.2) e Incorporação (JLS §18.3)
    # ------------------------------------------------------------------

    def _is_deferred_poly_arg(self, node: Optional[ASTNode], arg_t: Optional[str]) -> bool:
        if isinstance(node, (LambdaExpression, MethodReference)):
            return True
        if isinstance(node, ObjectCreationExpression) and getattr(node, "is_diamond", False):
            return True
        if isinstance(node, ConditionalExpression):
            return self.host._is_poly_expression(node) or arg_t is None
        if isinstance(node, MethodCall) and arg_t is None:
            return True
        return False

    def _initial_poly_applicability(
        self,
        node: ASTNode,
        param_t: str,
        bset: BoundSet,
        worklist: List[Constraint],
    ) -> None:
        """Verifica aplicabilidade estrutural inicial para poly expression (§18.5.1)."""
        if isinstance(node, LambdaExpression):
            sam, is_known = self.host._resolve_functional_interface(param_t)
            if sam is None:
                ps = self.host._simple_base_name(param_t) or param_t
                if not self.is_inf_var(ps) and is_known:
                    bset.add_contradiction(f"Tipo de parâmetro '{param_t}' não é interface funcional para lambda.")
                return
            sam_params, _ = sam
            if len(node.parameters) != len(sam_params):
                bset.add_contradiction(
                    f"Lambda com {len(node.parameters)} parâmetro(s) incompatível com interface funcional '{param_t}'."
                )
                return
            if getattr(node, "parameter_mode", "inferred") == "explicit":
                typed_params = list(getattr(node, "typed_parameters", []) or [])
                for lp, sp in zip(typed_params, sam_params):
                    tref = getattr(lp, "type_ref", None)
                    if tref is not None:
                        lt = self.host._normalize_type_str(tref)
                        if lt:
                            worklist.append(Constraint(ConstraintKind.EQUALITY, lt, sp))
        elif isinstance(node, MethodReference):
            sam, is_known = self.host._resolve_functional_interface(param_t)
            if sam is None:
                ps = self.host._simple_base_name(param_t) or param_t
                if not self.is_inf_var(ps) and is_known:
                    bset.add_contradiction(f"Tipo de parâmetro '{param_t}' não é interface funcional para method reference.")
        elif isinstance(node, ConditionalExpression):
            worklist.append(Constraint(ConstraintKind.COMPATIBLE, "", param_t, expr_node=node.then_expr))
            worklist.append(Constraint(ConstraintKind.COMPATIBLE, "", param_t, expr_node=node.else_expr))
        elif isinstance(node, MethodCall):
            worklist.append(Constraint(ConstraintKind.COMPATIBLE, "", param_t, expr_node=node))
        elif isinstance(node, ObjectCreationExpression) and getattr(node, "is_diamond", False):
            worklist.append(Constraint(ConstraintKind.COMPATIBLE, "", param_t, expr_node=node))

    def _reduce_and_incorporate(
        self,
        bset: BoundSet,
        initial_worklist: List[Constraint],
        max_rounds: int = 40,
    ) -> None:
        queue = list(initial_worklist)
        seen: Set[Tuple[str, str, str, int, bool]] = set()
        rounds = 0
        while (queue or rounds == 0) and not bset.contradictions and rounds < max_rounds:
            rounds += 1
            while queue and not bset.contradictions:
                c = queue.pop(0)
                key = (
                    c.kind.value,
                    c.left or "",
                    c.right or "",
                    id(c.expr_node) if c.expr_node is not None else 0,
                    c.allow_boxing,
                )
                if key in seen:
                    continue
                seen.add(key)
                self._reduce_single(c, bset, queue)

            if bset.contradictions:
                break
            new_constraints = self._incorporate_step(bset)
            if not new_constraints:
                break
            for nc in new_constraints:
                nkey = (
                    nc.kind.value,
                    nc.left or "",
                    nc.right or "",
                    id(nc.expr_node) if nc.expr_node is not None else 0,
                    nc.allow_boxing,
                )
                if nkey not in seen:
                    queue.append(nc)

    def _reduce_single(self, c: Constraint, bset: BoundSet, queue: List[Constraint]) -> None:
        if c.expr_node is not None and not c.left:
            self._reduce_expr_node(c.expr_node, c.right, c.allow_boxing, bset, queue)
            return

        left = (self.host._strip_leading_type_annotations(c.left) or c.left).strip() if c.left else ""
        right = (self.host._strip_leading_type_annotations(c.right) or c.right).strip() if c.right else ""
        if not left or not right or left in ("var", "desconhecido") or right in ("var", "desconhecido"):
            return

        if c.kind == ConstraintKind.EQUALITY:
            self._reduce_equality(left, right, bset, queue)
        elif c.kind == ConstraintKind.SUBTYPE:
            self._reduce_subtype(left, right, bset, queue)
        elif c.kind == ConstraintKind.CONTAINS:
            self._reduce_contains(left, right, bset, queue)
        elif c.kind == ConstraintKind.COMPATIBLE:
            self._reduce_compatible_types(left, right, c.allow_boxing, bset, queue)

    def _reduce_expr_node(
        self,
        expr_node: ASTNode,
        target_t: str,
        allow_boxing: bool,
        bset: BoundSet,
        queue: List[Constraint],
    ) -> None:
        """Reduz fórmula de compatibilidade envolvendo subexpressão poly aninhada."""
        if isinstance(expr_node, ConditionalExpression):
            if self.host._is_poly_expression(expr_node):
                queue.append(Constraint(ConstraintKind.COMPATIBLE, "", target_t, expr_node=expr_node.then_expr, allow_boxing=allow_boxing))
                queue.append(Constraint(ConstraintKind.COMPATIBLE, "", target_t, expr_node=expr_node.else_expr, allow_boxing=allow_boxing))
            else:
                st = self._speculative_infer_expr(expr_node)
                if st:
                    queue.append(Constraint(ConstraintKind.COMPATIBLE, st, target_t, allow_boxing=allow_boxing))
            return

        if isinstance(expr_node, ObjectCreationExpression) and getattr(expr_node, "is_diamond", False):
            base_name = getattr(expr_node.type_ref, "name", None) or getattr(expr_node, "class_name", "")
            simple_base = self.host._simple_base_name(base_name) or base_name
            decls = self.host._type_param_decls_for_type(simple_base)
            if not decls:
                queue.append(Constraint(ConstraintKind.COMPATIBLE, simple_base, target_t, allow_boxing=allow_boxing))
                return
            betas: List[str] = []
            for p_name, p_bounds in decls:
                beta = self._fresh_alpha()
                ivar = InferenceVariable(name=p_name, alpha=beta, declared_bounds=tuple(p_bounds or ["Object"]))
                bset.ensure_var(ivar)
                for ub in (p_bounds or ["Object"]):
                    if ub != "Object":
                        bset.add_upper(beta, ub)
                betas.append(beta)
            poly_inst = f"{simple_base}<{', '.join(betas)}>"
            queue.append(Constraint(ConstraintKind.SUBTYPE, poly_inst, target_t))
            return

        if isinstance(expr_node, MethodCall):
            if self._try_lift_inner_method_call(expr_node, target_t, bset, queue):
                return
            st = self._speculative_infer_expr(expr_node)
            if st:
                queue.append(Constraint(ConstraintKind.COMPATIBLE, st, target_t, allow_boxing=allow_boxing))
            return

        st = self._speculative_infer_expr(expr_node)
        if st:
            queue.append(Constraint(ConstraintKind.COMPATIBLE, st, target_t, allow_boxing=allow_boxing))

    def _try_lift_inner_method_call(
        self,
        call_node: MethodCall,
        target_t: str,
        bset: BoundSet,
        queue: List[Constraint],
    ) -> bool:
        """
        Eleva chamada genérica aninhada (`head(emptyList())`, `take(criar())`) para o
        mesmo `BoundSet` quando há uma assinatura única compatível com a aridade.
        """
        if getattr(call_node, "type_arguments", None):
            return False
        mname = call_node.method_name
        recv_type, _ = self._peek_call_receiver(call_node)
        if not recv_type:
            return False
        methods, _, _ = self.host._collect_type_methods(recv_type, mname)
        nargs = len(call_node.arguments)
        ar_matches = [
            m for m in methods
            if (len(m["params"]) == nargs and not m.get("varargs"))
            or (m.get("varargs") and nargs >= len(m["params"]) - 1)
        ]
        if len(ar_matches) != 1 or not ar_matches[0].get("tparams"):
            return False
        inner_sig = ar_matches[0]
        local_map: Dict[str, str] = {}
        inner_map = self._allocate_sig_vars(inner_sig, bset, local_map)
        inner_ret = self._substitute_map(inner_sig.get("ret", "void"), inner_map) or inner_sig.get("ret", "void")
        for idx, (inner_arg, inner_pt_raw) in enumerate(zip(call_node.arguments, inner_sig["params"])):
            inner_pt = self._substitute_map(inner_pt_raw, inner_map) or inner_pt_raw
            if isinstance(inner_arg, (LambdaExpression, MethodReference, ConditionalExpression, MethodCall, ObjectCreationExpression)):
                queue.append(Constraint(ConstraintKind.COMPATIBLE, "", inner_pt, expr_node=inner_arg, allow_boxing=True))
            else:
                iat = self._speculative_infer_expr(inner_arg)
                if iat:
                    queue.append(Constraint(ConstraintKind.COMPATIBLE, iat, inner_pt, expr_node=inner_arg, allow_boxing=True))
        if inner_ret != "void":
            queue.append(Constraint(ConstraintKind.COMPATIBLE, inner_ret, target_t, allow_boxing=True))
        return True

    def _peek_call_receiver(self, call_node: MethodCall) -> Tuple[Optional[str], bool]:
        if call_node.target is None:
            return self.host._current_enclosing_type(), False
        if isinstance(call_node.target, Identifier):
            sym = self.host._lookup_var_symbol(call_node.target.name)
            if sym is not None and sym.get("category") not in self.host.TYPE_SYMBOL_CATEGORIES and sym.get("category") is not None:
                return sym.get("type"), False
            if self.host._is_known_type(call_node.target.name) or (call_node.target.name and call_node.target.name[0].isupper()):
                return call_node.target.name, True
        return self.host._infer_member_access_receiver_type(call_node) if isinstance(call_node.target, MemberAccess) else self._speculative_infer_expr(call_node.target), False

    def _speculative_infer_expr(self, expr: ASTNode) -> Optional[str]:
        """Infere tipo de expressão sem poluir erros ou fluxo do analisador."""
        cached = self.host._inferred_types.get(id(expr))
        if cached is not None:
            return cached
        snap_flow = self.host._flow_snapshot()
        snap_sup = self.host._flow_suppress_errors
        snap_flags = self.host._snapshot_local_var_flags()
        snap_errs = len(self.host.errors)
        snap_caps = len(self.host._pending_lambda_captures)
        snap_unres = len(self.host.unresolved_checks)
        self.host._flow_suppress_errors = True
        try:
            return self.host.infer_type(expr)
        finally:
            del self.host.errors[snap_errs:]
            del self.host._pending_lambda_captures[snap_caps:]
            del self.host.unresolved_checks[snap_unres:]
            self.host._flow_suppress_errors = snap_sup
            self.host._flow_restore(snap_flow)
            self.host._restore_local_var_flags(snap_flags)

    # ------------------------------------------------------------------
    # Regras de redução por forma de restrição (§18.2.1 - §18.2.4)
    # ------------------------------------------------------------------

    def _reduce_compatible_types(
        self,
        src: str,
        dst: str,
        allow_boxing: bool,
        bset: BoundSet,
        queue: List[Constraint],
    ) -> None:
        if src == dst or dst == "Object":
            return
        if src == "void":
            if dst != "void":
                bset.add_contradiction(f"Tipo 'void' incompatível com '{dst}'.")
            return
        if dst == "void":
            bset.add_contradiction(f"Tipo '{src}' incompatível com retorno 'void'.")
            return
        if src == "null":
            dst_base, dst_dims = self.host._strip_type_dims_full(dst)
            if dst_dims == 0 and dst_base in self.host.PRIMITIVE_TYPES:
                bset.add_contradiction(f"'null' não é compatível com tipo primitivo '{dst}'.")
            return

        s_base, s_dims = self.host._strip_type_dims_full(src)
        d_base, d_dims = self.host._strip_type_dims_full(dst)
        s_is_prim = (s_dims == 0) and (s_base in self.host.PRIMITIVE_TYPES)
        d_is_prim = (d_dims == 0) and (d_base in self.host.PRIMITIVE_TYPES)

        if s_is_prim and d_is_prim:
            if s_base != d_base and d_base not in self.host.WIDENING_PRIMITIVE_TARGETS.get(s_base, set()):
                bset.add_contradiction(f"Tipo primitivo '{s_base}' incompatível com '{d_base}'.")
            return

        if s_is_prim and not d_is_prim:
            if not allow_boxing:
                # Em Fase 1 (estrita), primitivo não sofre boxing para tipo de referência/variável de tipo
                bset.add_contradiction(f"Boxing não permitido na Fase 1 de sobrecarga ('{src}' -> '{dst}').")
                return
            boxed = self._box_if_prim(s_base)
            queue.append(Constraint(ConstraintKind.SUBTYPE, boxed, dst))
            return

        if not s_is_prim and d_is_prim:
            if not allow_boxing:
                bset.add_contradiction(f"Unboxing não permitido na Fase 1 ('{src}' -> '{dst}').")
                return
            if self.is_inf_var(src):
                wrapper = self.host.PRIMITIVE_TO_WRAPPER.get(d_base)
                if wrapper:
                    queue.append(Constraint(ConstraintKind.SUBTYPE, src, wrapper))
                return
            unboxed = self.host.WRAPPER_TO_PRIMITIVE.get(self.host._simple_base_name(src) or src)
            if unboxed == d_base or (unboxed and d_base in self.host.WIDENING_PRIMITIVE_TARGETS.get(unboxed, set())):
                return
            bset.add_contradiction(f"Tipo '{src}' não pode ser convertido por unboxing para '{dst}'.")
            return

        queue.append(Constraint(ConstraintKind.SUBTYPE, src, dst))

    def _reduce_equality(
        self,
        left: str,
        right: str,
        bset: BoundSet,
        queue: List[Constraint],
    ) -> None:
        if left == right:
            return

        if self.is_inf_var(left) and self.is_inf_var(right):
            if left != right:
                bset.dep_equalities.add((left, right))
                bset.dep_equalities.add((right, left))
            return

        if self.is_inf_var(left):
            if left in self.free_inf_vars(right):
                bset.add_contradiction(f"Tipo cíclico infinito em '{left} = {right}' (JLS §18.3).")
                return
            bset.add_eq(left, right)
            return

        if self.is_inf_var(right):
            if right in self.free_inf_vars(left):
                bset.add_contradiction(f"Tipo cíclico infinito em '{right} = {left}' (JLS §18.3).")
                return
            bset.add_eq(right, left)
            return

        l_kind, l_bound = self.host._parse_wildcard_arg(left)
        r_kind, r_bound = self.host._parse_wildcard_arg(right)
        if l_kind is not None or r_kind is not None:
            if l_kind != r_kind:
                bset.add_contradiction(f"Restrição de igualdade inválida entre '{left}' e '{right}' (JLS §18.2.4).")
                return
            if l_kind == "unbounded":
                return
            if l_bound and r_bound:
                queue.append(Constraint(ConstraintKind.EQUALITY, l_bound, r_bound))
            return

        l_base, l_args, l_dims = self.host._extract_generic_args(left)
        r_base, r_args, r_dims = self.host._extract_generic_args(right)
        if l_dims != r_dims:
            bset.add_contradiction(f"Dimensões de array incompatíveis em '{left} = {right}'.")
            return
        if l_dims > 0:
            l_elem = f"{l_base}<{', '.join(l_args)}>" if l_args else (l_base or left[:-2 * l_dims])
            r_elem = f"{r_base}<{', '.join(r_args)}>" if r_args else (r_base or right[:-2 * r_dims])
            queue.append(Constraint(ConstraintKind.EQUALITY, l_elem, r_elem))
            return

        l_simple = self.host._simple_base_name(left) or left
        r_simple = self.host._simple_base_name(right) or right
        if l_simple != r_simple:
            if self.host._is_known_type(left) and self.host._is_known_type(right):
                bset.add_contradiction(f"Restrição de igualdade incompatível: '{left}' != '{right}' (JLS §18.2.4).")
            return

        if not l_args and not r_args:
            return
        if len(l_args) != len(r_args):
            if l_args and r_args:
                bset.add_contradiction(f"Aridade genérica incompatível em '{left} = {right}'.")
            return
        for la, ra in zip(l_args, r_args):
            queue.append(Constraint(ConstraintKind.EQUALITY, la, ra))

    def _reduce_subtype(
        self,
        sub: str,
        sup: str,
        bset: BoundSet,
        queue: List[Constraint],
    ) -> None:
        if sub == sup or sup == "Object" or sub == "null":
            return

        if self.is_inf_var(sub) and self.is_inf_var(sup):
            bset.dep_subtypes.add((sub, sup))
            return

        if self.is_inf_var(sub):
            bset.add_upper(sub, sup)
            return

        if self.is_inf_var(sup):
            boxed = self._box_if_prim(sub)
            bset.add_lower(sup, boxed)
            return

        has_free = bool(self.free_inf_vars(sub) or self.free_inf_vars(sup))
        if not has_free:
            res = self.host._is_subtype(sub, sup)
            if res is False:
                bset.add_contradiction(f"Tipo '{sub}' não é subtipo de '{sup}' (JLS §18.2.3).")
            return

        # Redução estrutural quando há variáveis de inferência em sub ou sup
        s_base, s_args, s_dims = self.host._extract_generic_args(sub)
        t_base, t_args, t_dims = self.host._extract_generic_args(sup)
        if s_dims > 0 or t_dims > 0:
            if s_dims > 0 and t_dims == 0:
                t_simple = self.host._simple_base_name(sup) or sup
                if t_simple not in ("Object", "Cloneable", "Serializable") and not self.is_inf_var(t_simple):
                    bset.add_contradiction(f"Array '{sub}' não é subtipo de '{sup}'.")
                return
            if s_dims == 0 and t_dims > 0:
                bset.add_contradiction(f"Tipo escalar '{sub}' não é subtipo de array '{sup}'.")
                return
            if s_dims != t_dims:
                if not (s_dims > t_dims and (self.host._simple_base_name(sup) or "") in ("Object", "Cloneable", "Serializable")):
                    bset.add_contradiction(f"Dimensões de array incompatíveis entre '{sub}' e '{sup}'.")
                return
            s_elem = f"{s_base}<{', '.join(s_args)}>" if s_args else (s_base or sub[:-2 * s_dims])
            t_elem = f"{t_base}<{', '.join(t_args)}>" if t_args else (t_base or sup[:-2 * t_dims])
            se_s = self.host._simple_base_name(s_elem) or s_elem
            te_s = self.host._simple_base_name(t_elem) or t_elem
            if se_s in self.host.PRIMITIVE_TYPES or te_s in self.host.PRIMITIVE_TYPES:
                if se_s != te_s:
                    bset.add_contradiction(f"Arrays primitivos incompatíveis: '{sub}' e '{sup}'.")
                return
            queue.append(Constraint(ConstraintKind.SUBTYPE, s_elem, t_elem))
            return

        t_simple = self.host._simple_base_name(t_base or sup) or sup
        s_simple = self.host._simple_base_name(s_base or sub) or sub

        if not t_args:
            # Alvo sem argumentos genéricos (ex: Comparable sem params ou classe concreta)
            raw_res = self.host._is_subtype(self.host._strip_generics(sub), self.host._strip_generics(sup))
            if raw_res is False:
                bset.add_contradiction(f"Tipo '{sub}' não é subtipo de '{sup}' (JLS §18.2.3).")
            return

        # Eleva `sub` até o supertipo parametrizado que compartilha a base `t_simple`
        lifted = self.host._lift_to_base_type(sub, t_simple)
        if lifted is None:
            # Se `sub` for uma variável de captura CAP#k ou tipo variável ativo, tenta limites superiores
            if self.host._is_capture_var(s_simple):
                cap = self.host._capture_vars.get(s_simple, {})
                ups = cap.get("upper_bounds") or ["Object"]
                for u in ups:
                    ul = self.host._lift_to_base_type(u, t_simple)
                    if ul is not None:
                        queue.append(Constraint(ConstraintKind.SUBTYPE, u, sup))
                        return
                bset.add_contradiction(f"Tipo capturado '{sub}' não é subtipo de '{sup}'.")
                return
            raw_res = self.host._is_subtype(s_simple, t_simple)
            if raw_res is False:
                bset.add_contradiction(f"Tipo '{sub}' não é subtipo de '{sup}' (JLS §18.2.3).")
            return

        # Se há wildcard em `lifted` e posição correspondente em `t_args` NÃO é wildcard
        # (ex: unir(List<?>, List<?>) passando a List<T>), captura argumentos wildcard antes!
        _, l_args, _ = self.host._extract_generic_args(lifted)
        if not l_args:
            # Tipo raw `List` -> compatível por unchecked conversion
            return
        if len(l_args) != len(t_args):
            bset.add_contradiction(f"Aridade genérica incompatível entre '{lifted}' e '{sup}'.")
            return

        needs_capture = any(
            self.host._is_wildcard_arg(la) and not self.host._is_wildcard_arg(ta)
            for la, ta in zip(l_args, t_args)
        )
        if needs_capture:
            captured = self.host._capture_convert(lifted) or lifted
            _, l_args, _ = self.host._extract_generic_args(captured)

        for la, ta in zip(l_args, t_args):
            queue.append(Constraint(ConstraintKind.CONTAINS, la, ta))

    def _reduce_contains(
        self,
        sub_arg: str,
        sup_arg: str,
        bset: BoundSet,
        queue: List[Constraint],
    ) -> None:
        skind, sbound = self.host._parse_wildcard_arg(sub_arg)
        tkind, tbound = self.host._parse_wildcard_arg(sup_arg)

        if tkind == "unbounded":
            return

        if tkind is None:
            if skind is not None:
                bset.add_contradiction(f"Argumento wildcard '{sub_arg}' não contido em '{sup_arg}' (JLS §18.2.3).")
                return
            queue.append(Constraint(ConstraintKind.EQUALITY, sub_arg, sup_arg))
            return

        if tkind == "extends" and tbound:
            if skind is None:
                queue.append(Constraint(ConstraintKind.SUBTYPE, sub_arg, tbound))
            elif skind == "extends" and sbound:
                queue.append(Constraint(ConstraintKind.SUBTYPE, sbound, tbound))
            elif skind == "unbounded":
                queue.append(Constraint(ConstraintKind.SUBTYPE, "Object", tbound))
            else:
                queue.append(Constraint(ConstraintKind.SUBTYPE, "Object", tbound))
            return

        if tkind == "super" and tbound:
            if skind is None:
                queue.append(Constraint(ConstraintKind.SUBTYPE, tbound, sub_arg))
            elif skind == "super" and sbound:
                queue.append(Constraint(ConstraintKind.SUBTYPE, tbound, sbound))
            else:
                bset.add_contradiction(f"Argumento '{sub_arg}' incompatível com '{sup_arg}' (JLS §18.2.3).")

    # ------------------------------------------------------------------
    # Incorporação (JLS §18.3)
    # ------------------------------------------------------------------

    def _incorporate_step(self, bset: BoundSet) -> List[Constraint]:
        out: List[Constraint] = []

        # 1. Igualdade entre variáveis de inferência: α = β
        for a, b in list(bset.dep_equalities):
            for t in bset.eq_bounds.get(a, []):
                if bset.add_eq(b, t):
                    out.append(Constraint(ConstraintKind.EQUALITY, b, t))
            for l in bset.lower_bounds.get(a, []):
                if bset.add_lower(b, l):
                    out.append(Constraint(ConstraintKind.SUBTYPE, l, b))
            for u in bset.upper_bounds.get(a, []):
                if bset.add_upper(b, u):
                    out.append(Constraint(ConstraintKind.SUBTYPE, b, u))

        # 2. Subtipagem entre variáveis de inferência: α <: β
        for a, b in list(bset.dep_subtypes):
            for l in bset.lower_bounds.get(a, []):
                out.append(Constraint(ConstraintKind.SUBTYPE, l, b))
            for u in bset.upper_bounds.get(b, []):
                out.append(Constraint(ConstraintKind.SUBTYPE, a, u))
            for t in bset.eq_bounds.get(b, []):
                out.append(Constraint(ConstraintKind.SUBTYPE, a, t))
            for t in bset.eq_bounds.get(a, []):
                out.append(Constraint(ConstraintKind.SUBTYPE, t, b))

        # 3. Cruzamento de igualdades, inferiores e superiores em cada variável α
        for alpha in bset.variables:
            eqs = bset.eq_bounds.get(alpha, [])
            lows = bset.lower_bounds.get(alpha, [])
            ups = bset.upper_bounds.get(alpha, [])

            if len(eqs) > 1:
                base_eq = eqs[0]
                for other_eq in eqs[1:]:
                    out.append(Constraint(ConstraintKind.EQUALITY, base_eq, other_eq))

            for eq_t in eqs:
                for l in lows:
                    out.append(Constraint(ConstraintKind.SUBTYPE, l, eq_t))
                for u in ups:
                    out.append(Constraint(ConstraintKind.SUBTYPE, eq_t, u))

            for l in lows:
                for u in ups:
                    out.append(Constraint(ConstraintKind.SUBTYPE, l, u))

            # Consistência entre múltiplos limites superiores na mesma variável
            if len(ups) > 1:
                self._check_upper_bounds_consistency(alpha, ups, bset, out)

        return out

    def _check_upper_bounds_consistency(
        self,
        alpha: str,
        ups: List[str],
        bset: BoundSet,
        out: List[Constraint],
    ) -> None:
        """Verifica se múltiplos limites superiores `α <: U1` e `α <: U2` são compatíveis (§18.3)."""
        proper_ups = [u for u in ups if not self.free_inf_vars(u)]
        # Mesmo que algum contenha variável livre, duas parametrizações da mesma base exigem igualdade de args
        for i in range(len(ups)):
            u1 = ups[i]
            b1, a1, d1 = self.host._extract_generic_args(u1)
            s1 = self.host._simple_base_name(b1 or u1) or u1
            for j in range(i + 1, len(ups)):
                u2 = ups[j]
                if u1 == u2:
                    continue
                b2, a2, d2 = self.host._extract_generic_args(u2)
                s2 = self.host._simple_base_name(b2 or u2) or u2
                if s1 == s2 and d1 == d2 == 0 and a1 and a2 and len(a1) == len(a2):
                    for x1, x2 in zip(a1, a2):
                        if not self.host._is_wildcard_arg(x1) and not self.host._is_wildcard_arg(x2):
                            out.append(Constraint(ConstraintKind.EQUALITY, x1, x2))

        for i in range(len(proper_ups)):
            u1 = proper_ups[i]
            s1 = self.host._simple_base_name(u1) or u1
            k1 = self.host._is_class_kind(s1)
            for j in range(i + 1, len(proper_ups)):
                u2 = proper_ups[j]
                s2 = self.host._simple_base_name(u2) or u2
                k2 = self.host._is_class_kind(s2)
                if k1 is True and k2 is True:
                    # Duas classes concretas nos limites de α só são compatíveis se uma é subtipo da outra
                    if self.host._is_subtype(u1, u2) is False and self.host._is_subtype(u2, u1) is False:
                        bset.add_contradiction(
                            f"Limites superiores de classe incompatíveis para '{bset.variables[alpha].name}': '{u1}' e '{u2}' (JLS §18.3)."
                        )
                elif s1 in self.host.BUILTIN_FINAL_TYPES or self._is_user_final_class(s1):
                    if self.host._is_subtype(u1, u2) is False:
                        bset.add_contradiction(
                            f"Classe final '{u1}' incompatível com limite '{u2}' em '{bset.variables[alpha].name}' (JLS §18.3)."
                        )
                elif s2 in self.host.BUILTIN_FINAL_TYPES or self._is_user_final_class(s2):
                    if self.host._is_subtype(u2, u1) is False:
                        bset.add_contradiction(
                            f"Classe final '{u2}' incompatível com limite '{u1}' em '{bset.variables[alpha].name}' (JLS §18.3)."
                        )

    def _is_user_final_class(self, simple_name: str) -> bool:
        tdecl = self.host._lookup_type_decl(simple_name)
        if tdecl is not None and tdecl[0] == "class":
            return "final" in (getattr(tdecl[1], "modifiers", []) or [])
        return False

    # ------------------------------------------------------------------
    # Resolução de expressões poly adiadas (Lambdas, MethodRefs, etc.)
    # ------------------------------------------------------------------

    def _resolve_deferred_poly_loop(
        self,
        bset: BoundSet,
        deferred_poly: List[Tuple[int, ASTNode, str]],
        allow_boxing: bool,
    ) -> None:
        if not deferred_poly:
            return
        max_iters = max(4, len(deferred_poly) + 2)
        for _ in range(max_iters):
            partial = self._snapshot_partial_instantiation(bset, deferred_poly)
            new_constraints: List[Constraint] = []
            for _, arg_node, param_pat in deferred_poly:
                eff_param = self._substitute_map(param_pat, partial) or param_pat
                if isinstance(arg_node, LambdaExpression):
                    self._collect_lambda_constraints(arg_node, eff_param, bset, new_constraints)
                elif isinstance(arg_node, MethodReference):
                    self._collect_method_ref_constraints(arg_node, eff_param, bset, new_constraints)
                elif isinstance(arg_node, ConditionalExpression):
                    new_constraints.append(Constraint(ConstraintKind.COMPATIBLE, "", eff_param, expr_node=arg_node.then_expr, allow_boxing=allow_boxing))
                    new_constraints.append(Constraint(ConstraintKind.COMPATIBLE, "", eff_param, expr_node=arg_node.else_expr, allow_boxing=allow_boxing))
                elif isinstance(arg_node, (MethodCall, ObjectCreationExpression)):
                    new_constraints.append(Constraint(ConstraintKind.COMPATIBLE, "", eff_param, expr_node=arg_node, allow_boxing=allow_boxing))
            if bset.contradictions:
                break
            before = (
                sum(len(v) for v in bset.eq_bounds.values()),
                sum(len(v) for v in bset.lower_bounds.values()),
                sum(len(v) for v in bset.upper_bounds.values()),
            )
            if new_constraints:
                self._reduce_and_incorporate(bset, new_constraints)
            after = (
                sum(len(v) for v in bset.eq_bounds.values()),
                sum(len(v) for v in bset.lower_bounds.values()),
                sum(len(v) for v in bset.upper_bounds.values()),
            )
            if bset.contradictions or after == before:
                break

    def _snapshot_partial_instantiation(
        self,
        bset: BoundSet,
        deferred_poly: List[Tuple[int, ASTNode, str]],
    ) -> Dict[str, str]:
        """
        Resolve antecipadamente variáveis que já possuem igualdades ou limites inferiores/superiores
        de entrada (JLS §18.5.2.2), mantendo livres variáveis puramente de saída aguardando poly return.
        """
        resolved: Dict[str, str] = {}
        # Identifica variáveis que possuem evidência direta (eq ou lower)
        for _ in range(len(bset.variables) + 1):
            progressed = False
            for alpha in bset.variables:
                if alpha in resolved:
                    continue
                eqs = [self._substitute_map(t, resolved) or t for t in bset.eq_bounds.get(alpha, [])]
                proper_eqs = [t for t in eqs if not self.free_inf_vars(t)]
                if proper_eqs:
                    resolved[alpha] = proper_eqs[0]
                    progressed = True
                    continue
                lows = [self._substitute_map(t, resolved) or t for t in bset.lower_bounds.get(alpha, [])]
                proper_lows = [t for t in lows if not self.free_inf_vars(t) and t != "null"]
                if proper_lows:
                    # Só antecipa se não estiver dependente de outro lower pendente ainda não reduzido
                    resolved[alpha] = self._compute_ref_lub(proper_lows)
                    progressed = True
            if not progressed:
                break
        return resolved

    def _collect_lambda_constraints(
        self,
        lam: LambdaExpression,
        target_type: str,
        bset: BoundSet,
        out: List[Constraint],
    ) -> None:
        if self.free_inf_vars(target_type):
            sam, _ = self.host._resolve_functional_interface(target_type)
            if sam is None:
                return
            sam_params, sam_ret = sam
            # Só avalia corpo quando os tipos dos parâmetros do lambda estão livres de INF#k
            if any(self.free_inf_vars(p) for p in sam_params):
                return
        else:
            sam, is_known = self.host._resolve_functional_interface(target_type)
            if sam is None:
                if is_known:
                    bset.add_contradiction(f"Tipo alvo '{target_type}' em lambda não é interface funcional (JLS §15.27).")
                return
            sam_params, sam_ret = sam

        if len(lam.parameters) != len(sam_params):
            bset.add_contradiction(
                f"Aridade incompatível em lambda: esperado {len(sam_params)}, encontrado {len(lam.parameters)}."
            )
            return

        param_types = self._resolve_lambda_param_types(lam, sam_params)
        ret_types = self._speculative_infer_lambda_returns(lam, param_types, sam_ret)

        if sam_ret == "void":
            if ret_types is None:
                bset.add_contradiction("Corpo de lambda 'void' inválido para método abstrato void.")
            return

        for rt in (ret_types or []):
            if rt == "void":
                bset.add_contradiction(f"Lambda com corpo 'void' incompatível com retorno '{sam_ret}'.")
            elif rt and rt not in ("var", "desconhecido"):
                out.append(Constraint(ConstraintKind.COMPATIBLE, rt, sam_ret, allow_boxing=True))

    def _resolve_lambda_param_types(self, lam: LambdaExpression, sam_params: List[str]) -> List[str]:
        typed_params = list(getattr(lam, "typed_parameters", []) or [])
        mode = getattr(lam, "parameter_mode", "inferred")
        result: List[str] = []
        for idx, _ in enumerate(lam.parameters):
            lp = typed_params[idx] if idx < len(typed_params) else None
            if mode == "explicit" and lp is not None and getattr(lp, "type_ref", None) is not None:
                pt = self.host._normalize_type_str(lp.type_ref) or sam_params[idx]
                if getattr(lp, "is_varargs", False) and not pt.endswith("[]"):
                    pt += "[]"
                result.append(pt)
            else:
                result.append(sam_params[idx] if idx < len(sam_params) else "Object")
        return result

    def _speculative_infer_lambda_returns(
        self,
        lam: LambdaExpression,
        param_types: List[str],
        sam_ret: str,
    ) -> Optional[List[str]]:
        """Infere tipos retornados pelo corpo de um lambda sem produzir efeitos colaterais."""
        host = self.host
        snap_flow = host._flow_snapshot()
        snap_sup = host._flow_suppress_errors
        snap_flags = host._snapshot_local_var_flags()
        snap_errs = len(host.errors)
        snap_caps = len(host._pending_lambda_captures)
        snap_unres = len(host.unresolved_checks)

        host._flow_suppress_errors = True
        host.symbols.enter_scope()
        floor_idx = len(host._local_var_scopes)
        host._lambda_scope_floor_stack.append(floor_idx)
        host._local_var_scopes.append({})
        host._active_pattern_scopes.append({})
        host._local_type_scopes.append({})
        host._local_declared_type_scopes.append({})
        host._lambda_return_exprs_stack.append([])
        ctx_ret = None if self.free_inf_vars(sam_ret) else sam_ret
        saved_ctx = host._enter_exec_context("lambda", return_type=ctx_ret, share_locals=True)
        inferred_returns: List[str] = []
        try:
            for idx, pname in enumerate(lam.parameters):
                if pname != "_":
                    host._register_local_var(
                        pname,
                        param_types[idx] if idx < len(param_types) else "Object",
                        getattr(lam, "line", 1),
                        has_initializer=True,
                        category="parametro",
                    )
            if lam.is_block_body and isinstance(lam.body, Block):
                host.analyze_block(lam.body)
                ret_exprs = list(host._lambda_return_exprs_stack[-1]) if host._lambda_return_exprs_stack else []
                if sam_ret == "void":
                    if any(r is not None for r in ret_exprs):
                        return None
                    return []
                for rexpr in ret_exprs:
                    if rexpr is not None:
                        rt = host.infer_type(rexpr)
                        if rt:
                            inferred_returns.append(rt)
            elif lam.body is not None:
                if sam_ret == "void":
                    if not host._is_statement_expression(lam.body):
                        return None
                    return []
                if ctx_ret and ctx_ret not in ("var", "desconhecido"):
                    host._check_expression_with_target(lam.body, ctx_ret)
                else:
                    host._check_expression_flow(lam.body)
                rt = host.infer_type(lam.body)
                if rt:
                    inferred_returns.append(rt)
        finally:
            host._restore_exec_context(saved_ctx)
            host._lambda_return_exprs_stack.pop()
            host._lambda_scope_floor_stack.pop()
            host._local_declared_type_scopes.pop()
            host._local_type_scopes.pop()
            host._pop_pattern_scope()
            host._local_var_scopes.pop()
            host.symbols.exit_scope()
            del host.errors[snap_errs:]
            del host._pending_lambda_captures[snap_caps:]
            del host.unresolved_checks[snap_unres:]
            host._flow_suppress_errors = snap_sup
            host._flow_restore(snap_flow)
            host._restore_local_var_flags(snap_flags)
        return inferred_returns

    def _collect_method_ref_constraints(
        self,
        mref: MethodReference,
        target_type: str,
        bset: BoundSet,
        out: List[Constraint],
    ) -> None:
        host = self.host
        sam, is_known_sam = host._resolve_functional_interface(target_type)
        if sam is None:
            if is_known_sam and not self.free_inf_vars(target_type):
                bset.add_contradiction(f"Tipo alvo '{target_type}' em method reference não é interface funcional.")
            return
        sam_params, sam_ret = sam
        if any(self.free_inf_vars(p) for p in sam_params):
            return

        if getattr(mref, "is_array_creation", False):
            if len(sam_params) != 1 or not host._is_integral_type(sam_params[0]):
                bset.add_contradiction(f"Referência de criação de array incompatível com '{target_type}'.")
                return
            arr_t = host._normalize_type_str(getattr(mref, "array_type", None)) or host._normalize_type_str(mref.target)
            if arr_t and sam_ret != "void":
                out.append(Constraint(ConstraintKind.COMPATIBLE, arr_t, sam_ret, allow_boxing=True))
            return

        if mref.method_name == "new":
            if isinstance(mref.target, TypeReference):
                tname = host._normalize_type_str(mref.target) or ""
            elif isinstance(mref.target, Identifier):
                tname = mref.target.name
            elif isinstance(mref.target, MemberAccess):
                tname = host._dotted_name(mref.target) or ""
            else:
                tname = host._normalize_type_str(mref.target) or ""
            ctors, is_known_c, _ = host._collect_type_constructors(tname)
            matched = [
                csig for csig in ctors
                if len(csig["params"]) == len(sam_params)
                and all(host._score_param_match(cp, None, sp, 2) is not None for cp, sp in zip(csig["params"], sam_params))
            ]
            if ctors and not matched:
                bset.add_contradiction(f"Nenhum construtor compatível em '{tname}::new' para '{target_type}'.")
                return
            if sam_ret != "void" and tname:
                # Se tname for genérico sem argumentos explícitos e sam_ret for parametrizado ou variável de inferência
                if "<" not in tname and ("<" in sam_ret or self.is_inf_var(sam_ret)):
                    decls = host._type_param_decls_for_type(tname)
                    if decls:
                        betas = [self._fresh_alpha() for _ in decls]
                        for (pn, pb), bt in zip(decls, betas):
                            bset.ensure_var(InferenceVariable(pn, bt, tuple(pb or ["Object"])))
                        out.append(Constraint(ConstraintKind.SUBTYPE, f"{tname}<{', '.join(betas)}>", sam_ret))
                        return
                out.append(Constraint(ConstraintKind.COMPATIBLE, tname, sam_ret, allow_boxing=True))
            elif not is_known_c:
                return
            return

        recv_is_type, recv_type = self._resolve_mref_receiver(mref)
        if not recv_type:
            return
        methods, is_known_m, _ = host._collect_type_methods(recv_type, mref.method_name)
        if not methods:
            if is_known_m:
                bset.add_contradiction(f"Método '{mref.method_name}' não encontrado em '{recv_type}'.")
            return

        compatible_sigs: List[Dict[str, Any]] = []
        for msig in methods:
            mparams = msig["params"]
            if msig["static"]:
                if not recv_is_type or len(mparams) != len(sam_params):
                    continue
                if all(host._score_param_match(mp, None, sp, 2) is not None for mp, sp in zip(mparams, sam_params)):
                    compatible_sigs.append(msig)
            else:
                if not recv_is_type and len(mparams) == len(sam_params):
                    if all(host._score_param_match(mp, None, sp, 2) is not None for mp, sp in zip(mparams, sam_params)):
                        compatible_sigs.append(msig)
                elif recv_is_type and len(sam_params) == len(mparams) + 1:
                    recv_arg = sam_params[0]
                    if host.is_assignable(recv_type, recv_arg) or host._is_subtype(recv_arg, recv_type) is True:
                        if all(host._score_param_match(mp, None, sp, 2) is not None for mp, sp in zip(mparams, sam_params[1:])):
                            compatible_sigs.append(msig)

        if not compatible_sigs:
            bset.add_contradiction(f"Referência a método '{recv_type}::{mref.method_name}' incompatível com '{target_type}'.")
            return

        if sam_ret != "void":
            # Se todos os candidatos retornam o mesmo tipo ou há 1 candidato, restringe sam_ret
            rets = [ms["ret"] for ms in compatible_sigs if ms.get("ret") and ms["ret"] != "void"]
            if len(compatible_sigs) == 1 and not rets and sam_ret != "void":
                bset.add_contradiction(f"Referência a método void '{recv_type}::{mref.method_name}' incompatível com retorno '{sam_ret}'.")
            elif len(rets) == 1 or (rets and all(r == rets[0] for r in rets)):
                out.append(Constraint(ConstraintKind.COMPATIBLE, rets[0], sam_ret, allow_boxing=True))

    def _resolve_mref_receiver(self, mref: MethodReference) -> Tuple[bool, Optional[str]]:
        host = self.host
        tgt = mref.target
        if isinstance(tgt, TypeReference):
            return True, host._normalize_type_str(tgt)
        if isinstance(tgt, Identifier):
            sym = host._lookup_var_symbol(tgt.name)
            if sym is not None and "type" in sym and sym.get("category") not in host.TYPE_SYMBOL_CATEGORIES:
                return False, sym["type"]
            if host._is_known_type(tgt.name) or (tgt.name and tgt.name[0].isupper()):
                return True, tgt.name
            if tgt.name == "this":
                return False, host._current_enclosing_type()
            if tgt.name == "super":
                cur = host._current_enclosing_type()
                if cur:
                    supers, _ = host._direct_supertypes(cur)
                    return False, supers[0] if supers else "Object"
        if tgt is not None:
            return False, self._speculative_infer_expr(tgt)
        return False, None

    # ------------------------------------------------------------------
    # Resolução final de variáveis de inferência (JLS §18.4)
    # ------------------------------------------------------------------

    def _resolve_variables(self, bset: BoundSet) -> Dict[str, str]:
        resolved: Dict[str, str] = {}
        remaining = list(bset.variables.keys())

        while remaining and not bset.contradictions:
            # Seleciona lote de variáveis cujos limites não dependem de outras variáveis não resolvidas
            ready: List[str] = []
            for alpha in remaining:
                deps = self._other_vars_in_bounds(alpha, bset, remaining)
                if not deps:
                    ready.append(alpha)

            # Se há ciclo de dependências entre variáveis restantes (ex: F-bounded), quebra escolhendo quem tem lower bound concreto primeiro
            if not ready:
                with_concrete_lower = [
                    a for a in remaining
                    if any(not (self.free_inf_vars(self._substitute_map(l, resolved) or l) - {a}) for l in bset.lower_bounds.get(a, []))
                ]
                ready = [with_concrete_lower[0]] if with_concrete_lower else [remaining[0]]

            for alpha in ready:
                val = self._instantiate_single_var(alpha, bset, resolved)
                if bset.contradictions:
                    break
                resolved[alpha] = val
                remaining.remove(alpha)

        return resolved

    def _other_vars_in_bounds(self, alpha: str, bset: BoundSet, remaining: List[str]) -> Set[str]:
        rem_set = set(remaining) - {alpha}
        deps: Set[str] = set()
        for src in (
            bset.eq_bounds.get(alpha, [])
            + bset.lower_bounds.get(alpha, [])
            + bset.upper_bounds.get(alpha, [])
        ):
            deps |= (self.free_inf_vars(src) & rem_set)
        for a, b in bset.dep_subtypes:
            if a == alpha and b in rem_set:
                deps.add(b)
            # Se `b <: alpha`, resolver `b` primeiro propaga os lower bounds concretos ou podemos resolver `alpha` antes se `alpha` já tiver lowers.
        for a, b in bset.dep_equalities:
            if a == alpha and b in rem_set:
                deps.add(b)
        return deps

    def _instantiate_single_var(
        self,
        alpha: str,
        bset: BoundSet,
        resolved: Dict[str, str],
    ) -> str:
        ivar = bset.variables[alpha]
        eqs = [self._substitute_map(t, resolved) or t for t in bset.eq_bounds.get(alpha, [])]
        lows = [self._substitute_map(t, resolved) or t for t in bset.lower_bounds.get(alpha, [])]
        ups = [self._substitute_map(t, resolved) or t for t in bset.upper_bounds.get(alpha, [])]

        proper_eqs = [t for t in eqs if not self.free_inf_vars(t)]
        proper_lows = [t for t in lows if not self.free_inf_vars(t)]
        proper_ups = [t for t in ups if not self.free_inf_vars(t) and t != "Object"]

        candidate: Optional[str] = None
        if proper_eqs:
            candidate = proper_eqs[0]
            for other in proper_eqs[1:]:
                if other != candidate:
                    # Verifica igualdade estrutural
                    if self.host._is_known_type(candidate) and self.host._is_known_type(other):
                        bset.add_contradiction(
                            f"Igualdades conflitantes para '{ivar.name}': '{candidate}' e '{other}' (JLS §18.4)."
                        )
                        return "Object"
        elif proper_lows:
            non_null = [t for t in proper_lows if t != "null"]
            if non_null:
                candidate = self._compute_ref_lub(non_null)
            else:
                candidate = proper_ups[0] if proper_ups else "Object"
        elif proper_ups:
            # Escolhe limite superior mais específico quando todos são compatíveis
            candidate = self._pick_most_specific_upper(proper_ups)
        else:
            # Limite apenas recursivo/F-bounded (ex: <T extends Comparable<T>> T make())
            raw_ups = [u for u in ups if u != "Object"]
            if raw_ups:
                first_u = raw_ups[0]
                u_base = self.host._strip_generics(first_u)
                candidate = u_base or "Object"
            else:
                candidate = "Object"

        # Valida candidato contra todos os limites inferiores e superiores próprios
        for l in proper_lows:
            if l != "null" and self.host._is_subtype(l, candidate) is False:
                bset.add_contradiction(
                    f"Instanciação '{candidate}' para '{ivar.name}' viola limite inferior '{l}' (JLS §18.4)."
                )
                return "Object"
        for u in proper_ups:
            # Substitui caso u contenha apenas auto-referência
            u_check = self._substitute_map(u, {alpha: candidate}) or u
            if self.host._is_subtype(candidate, u_check) is False:
                bset.add_contradiction(
                    f"Instanciação '{candidate}' para '{ivar.name}' viola limite superior '{u_check}' (JLS §18.4)."
                )
                return "Object"
        # Valida limites F-bounded onde `alpha` aparecia nos argumentos do próprio limite superior
        for u in ups:
            if alpha in self.free_inf_vars(u):
                u_closed = self._substitute_map(u, {**resolved, alpha: candidate}) or u
                if not self.free_inf_vars(u_closed) and self.host._is_subtype(candidate, u_closed) is False:
                    bset.add_contradiction(
                        f"Instanciação '{candidate}' para '{ivar.name}' viola limite recursivo '{u_closed}' (JLS §18.4)."
                    )
                    return "Object"

        return candidate

    def _pick_most_specific_upper(self, ups: List[str]) -> str:
        if len(ups) == 1:
            return ups[0]
        # Se um dos limites é subtipo de todos os demais, ele é o GLB imediato
        for cand in ups:
            if all(cand == other or self.host._is_subtype(cand, other) is True for other in ups):
                return cand
        # Preferência para classe concreta (não-interface) antes de interfaces
        for cand in ups:
            s = self.host._simple_base_name(cand) or cand
            if self.host._is_class_kind(s) is True:
                return cand
        return ups[0]
