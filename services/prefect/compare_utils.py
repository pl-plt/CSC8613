import math

def should_promote(new_auc: float, prod_auc: float, delta: float = 0.01) -> bool:
    """
    Retourne True si le modèle candidat doit être promu.
    Règle : promotion si prod_auc est NaN (cas rare) OU si new_auc > prod_auc + delta.
    """
    if prod_auc is None:
        return True

    if isinstance(prod_auc, float) and math.isnan(prod_auc):
        return True

    # return False  # TODO: implémentez la règle de décision
    return new_auc > prod_auc + delta