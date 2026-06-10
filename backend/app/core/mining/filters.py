import pandas as pd


def filtrar_redundantes(df_reglas, min_confianza):
    """
    Entre dos reglas donde el antecedente de una es subconjunto del otro
    (mismo consecuente), conserva la más corta siempre que su confianza
    supere min_confianza. El lift se usa solo para ordenar, no para filtrar.
    """
    registros = df_reglas.to_dict("records")
    mantener = []

    for i, fila in enumerate(registros):
        vars_fila = set(fila["antecedente"].split(" AND "))
        es_redundante = False

        for j, otra in enumerate(registros):
            if i == j:
                continue
            vars_otra = set(otra["antecedente"].split(" AND "))
            if (vars_otra < vars_fila                        # otra es subconjunto estricto
                    and otra["consecuente"] == fila["consecuente"]
                    and otra["confianza"] >= min_confianza): # la más corta supera el mínimo
                es_redundante = True
                break

        if not es_redundante:
            mantener.append(fila)

    return pd.DataFrame(mantener).reset_index(drop=True)


def filtrar_por_jerarquia(df_reglas, jerarquia, min_confianza):
    """
    Elimina la regla con variable "hijo" si existe la regla equivalente
    con la variable "padre" y su confianza supera min_confianza.
    """
    registros = df_reglas.to_dict("records")
    mantener = []

    for i, fila in enumerate(registros):
        vars_fila = set(fila["antecedente"].split(" AND "))
        es_redundante = False

        for padre, hijos in jerarquia.items():
            hijos_en_fila = vars_fila & set(hijos)
            if not hijos_en_fila:
                continue
            # Construir cómo sería la regla equivalente con el padre
            vars_con_padre = (vars_fila - hijos_en_fila) | {padre}

            for j, otra in enumerate(registros):
                if i == j:
                    continue
                vars_otra = set(otra["antecedente"].split(" AND "))
                if (vars_otra == vars_con_padre
                        and otra["consecuente"] == fila["consecuente"]
                        and otra["confianza"] >= min_confianza):
                    es_redundante = True
                    break
            if es_redundante:
                break

        if not es_redundante:
            mantener.append(fila)

    return pd.DataFrame(mantener).reset_index(drop=True)


def filtrar_top_por_consecuente(df_reglas, top_n):
    """
    Limita el número máximo de reglas por consecuente
    para evitar saturación en el módulo de NLG.
    """
    return (df_reglas
            .sort_values("lift", ascending=False)
            .groupby("consecuente", group_keys=False)
            .head(top_n)
            .sort_values("lift", ascending=False)
            .reset_index(drop=True))
