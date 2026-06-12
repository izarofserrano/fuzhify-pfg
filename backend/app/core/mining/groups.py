from .constants import MESES_POR_ESTACION


def _construir_grupos(cols_disponibles):
    """
    Genera los grupos excluyentes filtrando solo las columnas
    que realmente existen en el CSV fuzzificado.
    """
    cols = set(cols_disponibles)
    grupos = []

    candidatos = [
        # Meses
        {"t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
         "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"},
        # Estaciones
        {"t_Primavera","t_Verano","t_Otonio","t_Invierno"},
        # Horas
        {f"t_H{h:02d}" for h in range(24)},
        # Franjas horarias
        {"t_Madrugada","t_Mañana","t_Tarde","t_Noche"},
        # Días de la semana
        {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie","t_Sab","t_Dom"},
        # Tipo de día
        {"t_Laborable","t_FinSemana"},
        # Años (dinámico: cualquier t_20XX)
        {c for c in cols if c.startswith("t_20")},
        # Quincenas
        {"t_Q1mes","t_Q2mes"},
        # Minutos (cuartos de hora) — nuevo bloque src01
        {"t_M00","t_M15","t_M30","t_M45"},
        # Exclusiones cruzadas laborable/fin de semana
        {"t_Laborable", "t_Sab", "t_Dom"},
        {"t_FinSemana", "t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie"},
        # Exclusiones cruzadas festivo/laborable
        {"t_Laborable", "t_Festivo"},
        {"t_FinSemana", "t_Festivo"},
    ]

    for grupo in candidatos:
        presente = grupo & cols
        if len(presente) >= 2:   # solo añadir si hay al menos 2 vars del grupo
            grupos.append(presente)

    return grupos


def _combinacion_valida(tokens, grupos_excluyentes):
    # Regla 1: dentro de cada grupo, máximo 1 valor
    for grupo in grupos_excluyentes:
        if len(tokens & grupo) > 1:
            return False

    # Regla 2: mes y estación deben ser compatibles
    NOMBRES_MESES = {
        "t_Ene","t_Feb","t_Marz","t_Abr","t_May","t_Jun",
        "t_Jul","t_Ago","t_Sep","t_Oct","t_Nov","t_Dic"
    }
    grupo_meses = next(
        (g for g in grupos_excluyentes if g & NOMBRES_MESES),
        set()
    )
    for estacion, meses_validos in MESES_POR_ESTACION.items():
        if estacion in tokens:
            meses_en_regla = tokens & grupos_excluyentes[0]
            meses_en_regla = tokens & grupo_meses
            if meses_en_regla - meses_validos:
                return False
            
    # Regla 3: hora y franja deben ser compatibles
    HORAS_POR_FRANJA = {
        "t_Madrugada": {f"t_H{h:02d}" for h in range(0, 7)},
        "t_Mañana":    {f"t_H{h:02d}" for h in range(7, 14)},
        "t_Tarde":     {f"t_H{h:02d}" for h in range(14, 21)},
        "t_Noche":     {f"t_H{h:02d}" for h in range(21, 24)},
    }

    for franja, horas_validas in HORAS_POR_FRANJA.items():
        if franja in tokens:
            horas_en_regla = tokens & {f"t_H{h:02d}" for h in range(24)}
            if horas_en_regla and not (horas_en_regla <= horas_validas):
                return False

    # Regla 4: día concreto y tipo_dia deben ser coherentes
    DIAS_LABORABLES = {"t_Lun","t_Mar","t_Mie","t_Jue","t_Vie"}
    DIAS_FINSEM     = {"t_Sab","t_Dom"}
    if "t_Laborable" in tokens and (tokens & DIAS_FINSEM):
        return False
    if "t_FinSemana" in tokens and (tokens & DIAS_LABORABLES):
        return False

    return True


def construir_jerarquia(cols_csv):
    """
    Construye la jerarquía semántica padre→hijos filtrada
    a las columnas presentes en el CSV fuzzificado.
    """
    _cols_csv = set(cols_csv)

    def _filtrar_hijos(hijos):
        return [h for h in hijos if h in _cols_csv]

    _JERARQUIA_COMPLETA = {
        # Franjas → horas individuales
        "t_Madrugada": [f"t_H{h:02d}" for h in range(0,  7)],
        "t_Mañana":    [f"t_H{h:02d}" for h in range(7,  14)],
        "t_Tarde":     [f"t_H{h:02d}" for h in range(14, 21)],
        "t_Noche":     [f"t_H{h:02d}" for h in range(21, 24)],
        # Tipo día → días individuales
        "t_Laborable": ["t_Lun", "t_Mar", "t_Mie", "t_Jue", "t_Vie"],
        "t_FinSemana": ["t_Sab", "t_Dom"],
        # Estaciones → meses
        "t_Invierno":  ["t_Dic", "t_Ene", "t_Feb"],
        "t_Primavera": ["t_Marz", "t_Abr", "t_May"],
        "t_Verano":    ["t_Jun", "t_Jul", "t_Ago"],
        "t_Otonio":    ["t_Sep", "t_Oct", "t_Nov"],
        # Festivo → laborable/fin de semana (festivo es más específico)
        "t_Festivo":   ["t_Laborable", "t_FinSemana"],
    }

    return {
        padre: hijos_filtrados
        for padre, hijos in _JERARQUIA_COMPLETA.items()
        if padre in _cols_csv
        for hijos_filtrados in [_filtrar_hijos(hijos)]
        if hijos_filtrados  # solo incluir si hay al menos 1 hijo presente
    }
