# Cadrage papier — CAS 3 Énergie

**Utilisateur :** acheteur d'énergie / responsable de flotte d'une collectivité du Centre-Val de Loire.

**Décision :** choisir un créneau de quatre heures pour déplacer la recharge de véhicules électriques, en minimisant la demande régionale observée et en privilégiant les périodes de forte contribution renouvelable.

**Trois questions, dans l'ordre :**
1. À quelles heures la consommation régionale est-elle la plus faible en semaine et le week-end ?
2. Comment les pics saisonniers évoluent-ils entre hiver et été ?
3. Quels créneaux de quatre heures combinent demande faible et production renouvelable importante ?

**Indicateurs :** consommation moyenne (MW), part renouvelable moyenne (%), meilleur créneau historique (4 h).

**Filtres :** période et type de jour ; ils pilotent les indicateurs et les graphiques de la vue filtrée.

**Drill-down :** année → mois → jour → demi-heure.

**ML :** Random Forest pour prévoir la consommation à partir des variables calendaires ; MAE, RMSE et comparaison à une baseline affichées.

**Framework :** Streamlit, choisi pour produire rapidement une application interactive Python, avec filtres, graphiques Plotly et déploiement simple.

**Limite métier :** les données décrivent le réseau régional, pas la consommation ni les contraintes opérationnelles propres à la collectivité. Le créneau proposé est un indicateur d'aide à la décision, à confronter au contrat d'énergie, aux bornes et aux besoins de mobilité.
