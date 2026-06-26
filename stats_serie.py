"""
stats_serie.py
==============
Analyse statistique d'une série de mesures.

Usage rapide
------------
    from stats_serie import analyse, print_report

    raw = open("mesures.txt").read()      # ou copier-coller direct
    res = analyse(raw, n_classes=15)
    print_report(res)
"""

import re
import math
from typing import Union


# ─────────────────────────────────────────────────────────────
#  PARSING
# ─────────────────────────────────────────────────────────────

def parse_data(raw: str) -> list[float]:
    """
    Extrait tous les nombres d'une chaîne (tableau Moodle copié-collé).
    Accepte : virgule décimale française, tabulations, points-virgules, espaces.

    >>> parse_data("47,3\\n48.1\\n46,9")
    [47.3, 48.1, 46.9]
    """
    # Virgule décimale française : 47,3 → 47.3
    cleaned = re.sub(r'(\d),(\d)', r'\1.\2', raw)
    # Autres séparateurs → espace
    cleaned = re.sub(r'[;,\t|]', ' ', cleaned)
    tokens  = re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?', cleaned)
    values  = [float(t) for t in tokens if math.isfinite(float(t))]
    if not values:
        raise ValueError("Aucune valeur numérique détectée dans les données.")
    return values


# ─────────────────────────────────────────────────────────────
#  QUANTILE  (méthode NumWorks / interpolation linéaire)
# ─────────────────────────────────────────────────────────────

def _quantile(sorted_data: list[float], p: float) -> float:
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    pos = p * (n - 1)
    lo, hi = int(pos), math.ceil(pos)
    if lo == hi:
        return sorted_data[lo]
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (pos - lo)


# ─────────────────────────────────────────────────────────────
#  FONCTION PRINCIPALE
# ─────────────────────────────────────────────────────────────

def analyse(
    data: list[float],
    n_classes: int = 10,
) -> dict:
    """
    Analyse statistique complète d'une série de mesures.

    Paramètres
    ----------
    data       : list[float] → liste de mesures Python
                 (si tu as un texte copié-collé, utilise d'abord parse_data())
    n_classes  : int         → nombre de classes de l'histogramme (défaut 10)

    Retourne
    --------
    dict avec deux clés :
        'stats'     → indicateurs statistiques
        'histogram' → classes, effectifs et fréquences

    Exemple
    -------
        mesures = [47.3, 48.1, 46.9, 47.8, ...]
        res = analyse(mesures, n_classes=15)
        print_report(res)

        # ou depuis un texte brut :
        res = analyse(parse_data(texte_brut), n_classes=15)
    """
    values = [float(v) for v in data if math.isfinite(float(v))]

    if len(values) < 2:
        raise ValueError("Il faut au moins 2 valeurs.")
    if n_classes < 2:
        raise ValueError("n_classes doit être ≥ 2.")

    n      = len(values)
    sorted_v = sorted(values)

    # ── Indicateurs classiques ──
    mean   = sum(sorted_v) / n
    ssq    = sum((x - mean) ** 2 for x in sorted_v)
    sig_n  = math.sqrt(ssq / n)
    sig_n1 = math.sqrt(ssq / (n - 1)) if n > 1 else 0.0
    v_min  = sorted_v[0]
    v_max  = sorted_v[-1]
    q1     = _quantile(sorted_v, 0.25)
    med    = _quantile(sorted_v, 0.50)
    q3     = _quantile(sorted_v, 0.75)
    iqr    = q3 - q1
    etendue = v_max - v_min

    # ── Asymétrie (skewness de Fisher) et aplatissement (kurtosis excess) ──
    if sig_n > 0:
        skewness = (sum((x - mean) ** 3 for x in sorted_v) / n) / (sig_n ** 3)
        kurtosis = (sum((x - mean) ** 4 for x in sorted_v) / n) / (sig_n ** 4) - 3
    else:
        skewness = 0.0
        kurtosis = 0.0

    # ── Valeurs aberrantes (méthode de Tukey : ±1.5 × IQR) ──
    fence_lo = q1 - 1.5 * iqr
    fence_hi = q3 + 1.5 * iqr
    outliers = [x for x in sorted_v if x < fence_lo or x > fence_hi]

    # ── Histogramme ──
    if etendue == 0:
        # Toutes les valeurs identiques → une seule classe
        class_width = 0.0
        classes     = {v_min: n}
        rel_freq    = {v_min: 100.0}
        modal_class = (v_min, v_min, n)
    else:
        class_width = etendue / n_classes

        # Bornes inférieures des classes
        classes: dict[float, int] = {}
        for i in range(n_classes):
            lower = v_min + i * class_width
            classes[lower] = 0

        for x in sorted_v:
            idx = int((x - v_min) / class_width)
            if idx >= n_classes:
                idx = n_classes - 1
            lower = v_min + idx * class_width
            classes[lower] += 1

        rel_freq = {k: round(v / n * 100, 2) for k, v in classes.items()}

        # Classe modale (effectif maximum)
        modal_lower = max(classes, key=classes.get)
        modal_count = classes[modal_lower]
        modal_class = (modal_lower, modal_lower + class_width, modal_count)

    stats = {
        "n"         : n,
        "mean"      : mean,
        "sum_x"     : sum(sorted_v),
        "sigma_n"   : sig_n,
        "sigma_n1"  : sig_n1,
        "variance_n": ssq / n,
        "min"       : v_min,
        "Q1"        : q1,
        "median"    : med,
        "Q3"        : q3,
        "max"       : v_max,
        "range"     : etendue,
        "IQR"       : iqr,
        "skewness"  : skewness,   # 0=symétrique, >0=queue à droite, <0=queue à gauche
        "kurtosis"  : kurtosis,   # 0=normale, >0=pointue (leptokurtique), <0=plate (platykurtique)
    }

    # Tableau combiné : une ligne par classe avec toutes les infos
    tableau = [
        {
            "lower"   : lower,
            "upper"   : lower + class_width,
            "count"   : count,
            "freq_pct": rel_freq[lower],          # fréquence en %
            "freq_rel": round(count / n, 6),      # fréquence relative [0;1]
        }
        for lower, count in classes.items()
    ]

    histogram = {
        "n_classes"  : n_classes,
        "class_width": class_width,
        "classes"    : classes,       # {borne_inf: effectif, ...}
        "rel_freq"   : rel_freq,      # {borne_inf: fréquence_%, ...}
        "tableau"    : tableau,       # liste de dicts {lower, upper, count, freq_pct, freq_rel}
        "modal_class": modal_class,   # (borne_inf, borne_sup, effectif)
        "outliers"   : outliers,      # valeurs hors ±1.5×IQR
    }

    return {"stats": stats, "histogram": histogram}


# ─────────────────────────────────────────────────────────────
#  AFFICHAGE
# ─────────────────────────────────────────────────────────────

def print_report(result: dict, precision: int = 4) -> None:
    """Affiche un rapport lisible dans le terminal."""

    def f(x):
        if not math.isfinite(x):
            return "—"
        if x == 0:
            return "0"
        abs_x = abs(x)
        if abs_x >= 1e6 or (abs_x < 1e-3 and abs_x != 0):
            return f"{x:.{precision-1}e}"
        mag = math.floor(math.log10(abs_x)) if abs_x > 0 else 0
        dec = max(0, precision - 1 - mag)
        return f"{x:.{dec}f}"

    s = result["stats"]
    h = result["histogram"]

    w = 46
    print("═" * w)
    print(f"  ANALYSE STATISTIQUE   (n = {s['n']} mesures)")
    print("═" * w)

    print("\n  ── Indicateurs de position ──")
    print(f"  {'Moyenne (x̄)':<22} {f(s['mean'])}")
    print(f"  {'Médiane':<22} {f(s['median'])}")
    print(f"  {'Somme Σx':<22} {f(s['sum_x'])}")

    print("\n  ── Dispersion ──")
    print(f"  {'Écart-type σn (pop.)':<22} {f(s['sigma_n'])}")
    print(f"  {'Écart-type σn-1 (éch.)':<22} {f(s['sigma_n1'])}")
    print(f"  {'Variance σn²':<22} {f(s['variance_n'])}")
    print(f"  {'Étendue':<22} {f(s['range'])}")
    print(f"  {'IQR (Q3 − Q1)':<22} {f(s['IQR'])}")

    print("\n  ── Quartiles ──")
    print(f"  {'Min':<22} {f(s['min'])}")
    print(f"  {'Q1':<22} {f(s['Q1'])}")
    print(f"  {'Médiane (Q2)':<22} {f(s['median'])}")
    print(f"  {'Q3':<22} {f(s['Q3'])}")
    print(f"  {'Max':<22} {f(s['max'])}")

    print("\n  ── Forme de la distribution ──")
    sk = s['skewness']
    sk_label = ("symétrique" if abs(sk) < 0.5
                else ("queue à droite" if sk > 0 else "queue à gauche"))
    print(f"  {'Asymétrie (skew.)':<22} {f(sk)}  ({sk_label})")
    ku = s['kurtosis']
    ku_label = ("≈ normale" if abs(ku) < 0.5
                else ("pointue" if ku > 0 else "aplatie"))
    print(f"  {'Aplatissement (kurt.)':<22} {f(ku)}  ({ku_label})")

    print("\n  ── Valeurs aberrantes (Tukey ±1.5×IQR) ──")
    if h['outliers']:
        print(f"  {len(h['outliers'])} valeur(s) : {h['outliers']}")
    else:
        print("  Aucune valeur aberrante détectée.")

    print(f"\n  ── Histogramme ({h['n_classes']} classes, amplitude {f(h['class_width'])}) ──")
    ml, mu, mc = h['modal_class']
    print(f"  Classe modale : [{f(ml)} ; {f(mu)}[  effectif = {mc}")
    print()
    print(f"  {'Borne inf.':<14} {'Borne sup.':<14} {'Effectif':>8}  {'Fréq. %':>8}")
    print(f"  {'-'*46}")
    cw = h['class_width']
    for lower, count in h['classes'].items():
        upper = lower + cw
        pct   = h['rel_freq'][lower]
        bar   = "█" * int(pct / 2)   # barre ASCII proportionnelle
        mark  = " ◀ modale" if lower == ml else ""
        print(f"  {f(lower):<14} {f(upper):<14} {count:>8}  {pct:>7.1f}%  {bar}{mark}")

    print("\n" + "═" * w)


# ─────────────────────────────────────────────────────────────
#  DEMO
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random, textwrap

    # Simulation : 250 mesures d'une résistance autour de 47 Ω
    random.seed(42)
    simulated = [round(random.gauss(47.0, 0.8), 2) for _ in range(250)]
    raw_text  = "\n".join(str(v) for v in simulated)

    result = analyse(raw_text, n_classes=15)
    print_report(result)

    # Accès programmatique
    print("\n[Accès direct]")
    print("  Moyenne   :", result["stats"]["mean"])
    print("  Outliers  :", result["histogram"]["outliers"])

    print("\n[Tableau des classes (5 premières)]")
    for row in result["histogram"]["tableau"][:5]:
        print(f"  [{row['lower']:.3f} ; {row['upper']:.3f}[  "
              f"effectif={row['count']:>3}  "
              f"fréq={row['freq_pct']:>5.1f}%  "
              f"fréq_rel={row['freq_rel']:.4f}")
